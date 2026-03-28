"""
Content Agent - Generates 50 unique Terraform tips using OpenAI
"""
import json
import asyncio
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

TERRAFORM_TOPICS = [
    "terraform init deep dive", "terraform plan best practices", "terraform apply safely",
    "state file management", "remote state with S3", "state locking with DynamoDB",
    "terraform workspaces", "modules structure", "module versioning",
    "variables and locals", "output values", "data sources",
    "resource dependencies", "count vs for_each", "dynamic blocks",
    "terraform fmt and validate", "terragrunt overview", "provider configuration",
    "multiple providers", "provider aliases", "terraform import",
    "moved blocks", "refactoring resources", "lifecycle rules",
    "create_before_destroy", "prevent_destroy", "ignore_changes",
    "terraform cloud basics", "remote execution", "policy as code with Sentinel",
    "OPA with Terraform", "tflint usage", "checkov security scanning",
    "terraform testing with Terratest", "null_resource and triggers",
    "provisioners (when/why avoid)", "backends overview", "S3 backend config",
    "GCS backend", "Azure backend", "secrets management with Vault",
    "AWS Secrets Manager integration", "conditional expressions",
    "templatefile function", "file() and filebase64()", "terraform console",
    "debugging with TF_LOG", "CI/CD with Terraform", "GitHub Actions pipeline",
    "GitLab CI pipeline", "atlantis workflow"
]


class ContentAgent:
    def __init__(self, config: dict):
        self.client = AsyncOpenAI(api_key=config["openai_api_key"])
        self.model = config.get("openai_model", "gpt-4o")

    async def generate_tip(self, day: int, topic: str) -> dict:
        """Generate a single LinkedIn post for a Terraform topic."""
        prompt = f"""You are a senior DevOps engineer and Terraform expert writing LinkedIn posts.

Create a LinkedIn post for Day {day} of a "50 Days of Terraform Tips" series.

Topic: {topic}

Requirements:
- Start with an engaging hook (first line should stop the scroll)
- Include 3-5 practical, actionable tips or insights
- Add a real-world example or use case
- Use relevant emojis sparingly (max 5)
- Include a code snippet if applicable (use triple backticks)
- End with a thought-provoking question to drive engagement
- Add 5-7 relevant hashtags at the end
- Keep total length between 1200-1800 characters
- Tone: Professional but approachable, like a mentor sharing knowledge

Format your response as JSON:
{{
  "day": {day},
  "topic": "{topic}",
  "hook": "the first attention-grabbing line",
  "content": "full post content",
  "hashtags": ["terraform", "devops", ...],
  "has_code": true/false,
  "estimated_read_time": "X min read"
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.8,
        )

        tip = json.loads(response.choices[0].message.content)
        tip["generated_at"] = __import__("datetime").datetime.now().isoformat()
        logger.info(f"  ✓ Generated Day {day}: {topic}")
        return tip

    async def generate_all_tips(self) -> list:
        """Generate all 50 tips with concurrency control."""
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent API calls

        async def bounded_generate(day, topic):
            async with semaphore:
                await asyncio.sleep(0.5)  # Rate limit buffer
                return await self.generate_tip(day, topic)

        tasks = [
            bounded_generate(i + 1, topic)
            for i, topic in enumerate(TERRAFORM_TOPICS)
        ]

        tips = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out any failures and retry
        valid_tips = []
        for i, tip in enumerate(tips):
            if isinstance(tip, Exception):
                logger.warning(f"Failed to generate Day {i+1}, retrying...")
                try:
                    tip = await self.generate_tip(i + 1, TERRAFORM_TOPICS[i])
                    valid_tips.append(tip)
                except Exception as e:
                    logger.error(f"Retry failed for Day {i+1}: {e}")
            else:
                valid_tips.append(tip)

        return valid_tips
