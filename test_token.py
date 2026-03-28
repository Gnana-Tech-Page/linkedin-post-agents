import httpx, os
from dotenv import load_dotenv
load_dotenv()

token = os.getenv("LINKEDIN_ACCESS_TOKEN")
resp = httpx.get(
    "https://api.linkedin.com/v2/userinfo",
    headers={"Authorization": f"Bearer {token}"}
)
print(resp.status_code, resp.json())