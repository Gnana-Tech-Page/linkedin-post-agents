"""
main.py — Entry point for LinkedIn Terraform Tips Bot
Usage:
    python main.py run          # Full pipeline (generate → schedule → post → monitor)
    python main.py generate     # Generate tips only
    python main.py schedule     # Generate + schedule only
    python main.py post --day 5 # Manually post a specific day
    python main.py report       # Print analytics report
    python main.py reset        # Clear all state (start fresh)
"""
import asyncio
import argparse
import logging
import json
import os
from dotenv import load_dotenv
from agents.orchestrator import OrchestratorAgent
from agents.monitor_agent import MonitorAgent
from utils.state_manager import StateManager

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("output/pipeline.log"),
    ]
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    config = {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o"),
        "linkedin_access_token": os.getenv("LINKEDIN_ACCESS_TOKEN"),
        "start_date": os.getenv("START_DATE", __import__("datetime").datetime.now().isoformat()),
        "post_interval_days": int(os.getenv("POST_INTERVAL_DAYS", "1")),
        "dry_run": os.getenv("DRY_RUN", "false").lower() == "true",
    }

    if not config["openai_api_key"]:
        raise ValueError("❌ OPENAI_API_KEY is required in .env")
    if not config["linkedin_access_token"] and not config["dry_run"]:
        raise ValueError("❌ LINKEDIN_ACCESS_TOKEN is required (or set DRY_RUN=true)")

    return config


async def main():
    parser = argparse.ArgumentParser(description="LinkedIn Terraform Tips Bot")
    parser.add_argument("command", choices=["run", "generate", "schedule", "post", "report", "reset"],
                        help="Command to execute")
    parser.add_argument("--day", type=int, help="Day number for manual post command")
    args = parser.parse_args()

    config = load_config()
    orchestrator = OrchestratorAgent(config)

    if args.command == "run":
        await orchestrator.run_pipeline()

    elif args.command == "generate":
        tips = await orchestrator.generate_only()
        print(f"\n✅ Generated {len(tips)} tips → output/all_tips.json")
        print(f"\nSample — Day 1: {tips[0]['hook'][:100]}...")

    elif args.command == "schedule":
        schedule = await orchestrator.schedule_only()
        print(f"\n📅 Schedule saved → output/posting_schedule.csv")
        print(f"First post: {schedule[0]['scheduled_time']}")
        print(f"Last post:  {schedule[-1]['scheduled_time']}")

    elif args.command == "post":
        if not args.day:
            print("❌ Specify a day: python main.py post --day 5")
            return
        state = StateManager("state/pipeline_state.json").load()
        schedule = state.get("schedule", [])
        item = next((s for s in schedule if s["day"] == args.day), None)
        if not item:
            print(f"❌ Day {args.day} not found. Run 'generate' first.")
            return
        from agents.linkedin_agent import LinkedInAgent
        agent = LinkedInAgent(config)
        result = await agent.post(item["tip"])
        print(f"✅ Posted Day {args.day}: {result}")

    elif args.command == "report":
        monitor = MonitorAgent(config)
        report = monitor.generate_report()
        print(report)

    elif args.command == "reset":
        confirm = input("⚠️  This will reset all state. Type 'yes' to confirm: ")
        if confirm.lower() == "yes":
            StateManager("state/pipeline_state.json").reset()
            StateManager("state/analytics.json").reset()
            print("✅ State reset. Run 'generate' to start fresh.")


if __name__ == "__main__":
    asyncio.run(main())
