"""
Scheduler Agent - Plans optimal posting times across 50 days
"""
import json
import logging
from datetime import datetime, timedelta
from utils.state_manager import StateManager
from typing import Optional

logger = logging.getLogger(__name__)

# Optimal LinkedIn posting times (UTC) — adjust to your timezone
POSTING_SLOTS = [
    {"hour": 8, "minute": 30},   # Morning: high engagement
    {"hour": 12, "minute": 0},   # Lunch: peak scroll time
    {"hour": 17, "minute": 30},  # Evening: after work
]

# Skip weekends for professional content (optional)
SKIP_WEEKENDS = False


class SchedulerAgent:
    def __init__(self, config: dict):
        self.config = config
        self.state = StateManager("state/pipeline_state.json")
        self.post_interval_days = config.get("post_interval_days", 1)
        self.start_date = datetime.fromisoformat(
            config.get("start_date", datetime.now().isoformat())
        )

    async def create_schedule(self, tips: list) -> list:
        """Create or load an existing posting schedule."""
        state = self.state.load()
        if state.get("schedule") and len(state["schedule"]) == len(tips):
            logger.info("📅 Loaded existing schedule from state")
            return state["schedule"]

        schedule = self._build_schedule(tips)
        self.state.update({"schedule": schedule})
        self._export_schedule(schedule)
        return schedule

    def _build_schedule(self, tips: list) -> list:
        schedule = []
        current_date = self.start_date
        slot_index = 0

        for tip in tips:
            if SKIP_WEEKENDS:
                while current_date.weekday() >= 5:  # Sat=5, Sun=6
                    current_date += timedelta(days=1)

            slot = POSTING_SLOTS[slot_index % len(POSTING_SLOTS)]
            post_time = current_date.replace(
                hour=slot["hour"],
                minute=slot["minute"],
                second=0,
                microsecond=0
            )

            schedule.append({
                "day": tip["day"],
                "tip": tip,
                "scheduled_time": post_time.isoformat(),
                "slot": f"{slot['hour']:02d}:{slot['minute']:02d}",
                "posted": False,
                "post_id": None,
                "failed": False,
            })

            current_date += timedelta(days=self.post_interval_days)
            slot_index += 1

        logger.info(f"📅 Schedule built: Day 1 on {schedule[0]['scheduled_time'][:10]}, "
                    f"Day 50 on {schedule[-1]['scheduled_time'][:10]}")
        return schedule

    def _export_schedule(self, schedule: list):
        """Export human-readable schedule to CSV."""
        import csv
        with open("output/posting_schedule.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["day", "topic", "scheduled_time", "slot", "posted"])
            writer.writeheader()
            for item in schedule:
                writer.writerow({
                    "day": item["day"],
                    "topic": item["tip"]["topic"],
                    "scheduled_time": item["scheduled_time"],
                    "slot": item["slot"],
                    "posted": item["posted"],
                })
        logger.info("📊 Schedule exported to output/posting_schedule.csv")

    def get_next_post(self, schedule: list) -> Optional[dict]:
        pending = [s for s in schedule if not s["posted"] and not s["failed"]]
        return pending[0] if pending else None

    def get_stats(self, schedule: list) -> dict:
        return {
            "total": len(schedule),
            "posted": sum(1 for s in schedule if s["posted"]),
            "pending": sum(1 for s in schedule if not s["posted"] and not s["failed"]),
            "failed": sum(1 for s in schedule if s["failed"]),
        }
