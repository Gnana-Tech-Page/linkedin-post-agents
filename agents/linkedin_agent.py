"""
LinkedIn Agent - Handles OAuth and posting via LinkedIn API v2
"""
import json
import logging
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
LINKEDIN_UGC_POST_URL = f"{LINKEDIN_API_BASE}/ugcPosts"
LINKEDIN_ME_URL = "https://api.linkedin.com/v2/userinfo"


class LinkedInAgent:
    def __init__(self, config: dict):
        self.access_token = config["linkedin_access_token"]
        self.dry_run = config.get("dry_run", False)
        self._person_id = None

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def get_person_id(self) -> str:
        """Fetch LinkedIn person URN."""
        if self._person_id:
            return self._person_id

        async with httpx.AsyncClient() as client:
            resp = await client.get(LINKEDIN_ME_URL, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            self._person_id = data["sub"]
            logger.info(f"👤 LinkedIn Person ID: {self._person_id}")
            return self._person_id

    def _build_post_body(self, person_id: str, tip: dict) -> dict:
        """Build UGC post payload."""
        content = tip["content"]

        # Append hashtags if not already in content
        if tip.get("hashtags"):
            hashtag_str = " ".join(f"#{tag.replace('#', '')}" for tag in tip["hashtags"])
            if hashtag_str not in content:
                content = f"{content}\n\n{hashtag_str}"

        return {
            "author": f"urn:li:person:{person_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

    async def post(self, tip: dict) -> dict:
        """Post a tip to LinkedIn. Returns post result."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would post Day {tip['day']}: {tip['topic']}")
            logger.info(f"[DRY RUN] Content preview:\n{tip['content'][:200]}...")
            return {"id": f"dry-run-{tip['day']}", "dry_run": True}

        person_id = await self.get_person_id()
        body = self._build_post_body(person_id, tip)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                LINKEDIN_UGC_POST_URL,
                headers=self.headers,
                json=body
            )

            if resp.status_code == 201:
                post_id = resp.headers.get("x-restli-id", "unknown")
                logger.info(f"✅ Posted to LinkedIn: {post_id}")
                return {"id": post_id, "status": "published", "posted_at": datetime.now().isoformat()}
            else:
                error_msg = f"LinkedIn API error {resp.status_code}: {resp.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

    async def delete_post(self, post_id: str) -> bool:
        """Delete a post (useful for testing)."""
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{LINKEDIN_UGC_POST_URL}/{post_id}",
                headers=self.headers
            )
            return resp.status_code == 204

    async def verify_token(self) -> bool:
        """Verify the access token is valid."""
        try:
            await self.get_person_id()
            return True
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return False
