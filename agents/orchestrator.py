"""
Orchestrator Agent - Coordinates all agents in the pipeline
"""
import asyncio
import logging
from datetime import datetime
from agents.content_agent import ContentAgent
from agents.scheduler_agent import SchedulerAgent
from agents.linkedin_agent import LinkedInAgent
from agents.monitor_agent import MonitorAgent
from utils.state_manager import StateManager

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    def __init__(self, config: dict):
        self.config = config
        self.state = StateManager("state/pipeline_state.json")
        self.content_agent = ContentAgent(config)
        self.scheduler_agent = SchedulerAgent(config)
        self.linkedin_agent = LinkedInAgent(config)
        self.monitor_agent = MonitorAgent(config)

    async def run_pipeline(self):
        """Full pipeline: Generate → Schedule → Post → Monitor"""
        logger.info("🚀 Starting LinkedIn Terraform Tips Automation Pipeline")

        # Step 1: Generate 50 tips
        tips = await self._ensure_tips_generated()

        # Step 2: Create posting schedule
        schedule = await self.scheduler_agent.create_schedule(tips)
        stats = self.scheduler_agent.get_stats(schedule)
        logger.info(f"📊 Progress: {stats['posted']}/50 posted, {stats['pending']} pending, {stats['failed']} failed")

        # Step 3: Post anything due now
        await self._process_due_posts(schedule)

        # Step 4: Refresh analytics for posted items
        await self.monitor_agent.refresh_analytics()
        report = self.monitor_agent.generate_report()
        logger.info("\n" + report[:500])

        logger.info("✅ Pipeline run complete")

    async def generate_only(self):
        """Only generate tips and save to output."""
        tips = await self._ensure_tips_generated()
        import json
        with open("output/all_tips.json", "w") as f:
            json.dump(tips, f, indent=2)
        logger.info(f"💾 Saved {len(tips)} tips to output/all_tips.json")
        return tips

    async def schedule_only(self):
        """Generate + schedule without posting."""
        tips = await self._ensure_tips_generated()
        schedule = await self.scheduler_agent.create_schedule(tips)
        logger.info(f"📅 Schedule ready. Next post: Day {schedule[0]['day']} at {schedule[0]['scheduled_time']}")
        return schedule

    async def _ensure_tips_generated(self):
        state = self.state.load()
        if state.get("tips_generated") and len(state.get("tips", [])) == 50:
            logger.info("📚 Tips already generated, loading from state")
            return state["tips"]

        logger.info("✍️  Generating 50 Terraform tips via OpenAI (this takes ~2 minutes)...")
        tips = await self.content_agent.generate_all_tips()
        self.state.update({"tips_generated": True, "tips": tips})
        logger.info(f"✅ Generated {len(tips)} tips")
        return tips

    async def _process_due_posts(self, schedule):
        now = datetime.now()
        due_posts = [
            item for item in schedule
            if not item.get("posted")
            and not item.get("failed")
            and datetime.fromisoformat(item["scheduled_time"]) <= now
        ]

        if not due_posts:
            next_post = self.scheduler_agent.get_next_post(schedule)
            if next_post:
                logger.info(f"⏳ Next post: Day {next_post['day']} at {next_post['scheduled_time']}")
            return

        logger.info(f"📤 {len(due_posts)} post(s) due — processing...")
        for post in due_posts:
            logger.info(f"  → Day {post['day']}: {post['tip']['topic']}")
            try:
                result = await self.linkedin_agent.post(post["tip"])
                post["posted"] = True
                post["post_id"] = result.get("id")
                post["posted_at"] = datetime.now().isoformat()
                await self.monitor_agent.track(post)
                logger.info(f"  ✅ Posted (ID: {result.get('id')})")
            except Exception as e:
                logger.error(f"  ❌ Failed: {e}")
                post["failed"] = True
                post["error"] = str(e)

        self.state.update({"schedule": schedule})
