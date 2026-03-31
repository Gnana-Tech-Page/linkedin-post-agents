"""
Monitor Agent - Tracks post performance and generates reports
"""
import json
import logging
import httpx
from datetime import datetime, timedelta
from utils.state_manager import StateManager

logger = logging.getLogger(__name__)

LINKEDIN_STATS_URL = "https://api.linkedin.com/v2/socialActions/{post_id}"


class MonitorAgent:
    def __init__(self, config: dict):
        self.config = config
        self.access_token = config["linkedin_access_token"]
        self.state = StateManager("state/analytics.json")

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def track(self, post_item: dict):
        """Record a newly published post."""
        analytics = self.state.load()
        posts = analytics.get("posts", [])

        entry = {
            "day": post_item["day"],
            "topic": post_item["tip"]["topic"],
            "post_id": post_item.get("post_id"),
            "posted_at": post_item.get("posted_at", datetime.now().isoformat()),
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "impressions": 0,
            "last_checked": None,
        }
        posts.append(entry)
        self.state.update({"posts": posts})
        logger.info(f"📊 Tracking post Day {entry['day']}")

    async def refresh_analytics(self):
        """Fetch updated stats for all tracked posts."""
        analytics = self.state.load()
        posts = analytics.get("posts", [])

        for post in posts:
            if not post.get("post_id") or post["post_id"].startswith("dry-run"):
                continue
            try:
                stats = await self._fetch_post_stats(post["post_id"])
                post.update(stats)
                post["last_checked"] = datetime.now().isoformat()
            except Exception as e:
                logger.warning(f"Could not fetch stats for post {post['post_id']}: {e}")

        self.state.update({"posts": posts})
        return posts

    async def _fetch_post_stats(self, post_id: str) -> dict:
        """Fetch engagement metrics from LinkedIn API."""

        # Skip fake/manual post IDs
        if not post_id or post_id.startswith(('dry-run', 'confirmed', 'manually')):
            return {}

        # post_id may already be a full URN like urn:li:share:123
        # or just a numeric ID — handle both
        if post_id.startswith('urn:li:'):
            urn = post_id
        else:
            urn = f"urn:li:ugcPost:{post_id}"

        url = f"https://api.linkedin.com/v2/socialActions/{urn}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "likes":    data.get("likesSummary", {}).get("totalLikes", 0),
                    "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
                }
            else:
                logger.warning(f"Stats fetch failed {resp.status_code} for {urn}")
                return {}

    def generate_report(self) -> str:
        """Generate a markdown summary report."""
        analytics = self.state.load()
        posts = analytics.get("posts", [])

        if not posts:
            return "No posts tracked yet."

        total_posts = len(posts)
        total_likes = sum(p.get("likes", 0) for p in posts)
        total_comments = sum(p.get("comments", 0) for p in posts)
        best_post = max(posts, key=lambda p: p.get("likes", 0), default=None)

        report = f"""# LinkedIn Terraform Tips — Analytics Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Summary
- **Posts Published**: {total_posts}/50
- **Total Likes**: {total_likes}
- **Total Comments**: {total_comments}
- **Avg Likes/Post**: {total_likes / total_posts:.1f}

## Top Performer
"""
        if best_post:
            report += f"- Day {best_post['day']}: **{best_post['topic']}** — {best_post.get('likes', 0)} likes\n"

        report += "\n## Post-by-Post Breakdown\n| Day | Topic | Likes | Comments |\n|-----|-------|-------|----------|\n"
        for p in sorted(posts, key=lambda x: x["day"]):
            report += f"| {p['day']} | {p['topic'][:40]} | {p.get('likes', 0)} | {p.get('comments', 0)} |\n"

        with open("output/analytics_report.md", "w") as f:
            f.write(report)
        logger.info("📊 Report saved to output/analytics_report.md")
        return report
