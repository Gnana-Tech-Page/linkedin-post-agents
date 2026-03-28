# 🚀 LinkedIn Terraform Tips Bot — Complete Setup Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     OrchestratorAgent                        │
│  Coordinates the full pipeline & manages state              │
└────────┬──────────┬─────────────┬──────────────┬────────────┘
         │          │             │              │
         ▼          ▼             ▼              ▼
  ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
  │  Content   │ │Scheduler │ │LinkedIn  │ │   Monitor    │
  │  Agent     │ │  Agent   │ │  Agent   │ │   Agent      │
  │            │ │          │ │          │ │              │
  │ OpenAI GPT │ │ Timing & │ │ OAuth &  │ │ Analytics &  │
  │ generates  │ │ schedule │ │ UGC API  │ │ reporting    │
  │ 50 tips    │ │ CSV/JSON │ │ posting  │ │              │
  └────────────┘ └──────────┘ └──────────┘ └──────────────┘
         │                                         │
         └─────────────── StateManager ────────────┘
                    (JSON persistence layer)
```

---

## Step 1: Project Setup

```bash
git clone <your-repo> linkedin-terraform-bot
cd linkedin-post-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p state output
```

---

## Step 2: Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Click **"Create new secret key"**
3. Copy the key → paste in `.env` as `OPENAI_API_KEY`

**Cost estimate:** ~50 GPT-4o calls × ~$0.01 each = **~$0.50 total** for all 50 tips

---

## Step 3: Get LinkedIn Access Token

LinkedIn uses OAuth 2.0. Follow these steps:

### 3a. Create a LinkedIn App
1. Go to https://www.linkedin.com/developers/apps/new
2. Fill in app name: `Terraform Tips Bot`
3. Associate with a LinkedIn Page (create one if needed)
4. Under **Products**, request access to:
   - ✅ **Share on LinkedIn** (for posting)
   - ✅ **Sign In with LinkedIn using OpenID Connect**

### 3b. Configure OAuth Redirect
1. In your app → **Auth** tab
2. Add Redirect URL: `https://localhost:8000/callback`
3. Note your **Client ID** and **Client Secret**

### 3c. Get Authorization Code
Open this URL in your browser (replace `YOUR_CLIENT_ID`):
```
https://www.linkedin.com/oauth/v2/authorization
  ?response_type=code
  &client_id=YOUR_CLIENT_ID
  &redirect_uri=https://localhost:8000/callback
  &scope=openid%20profile%20w_member_social
```

After authorizing, copy the `code` parameter from the redirect URL.

### 3d. Exchange Code for Access Token
```bash
curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
  -d "grant_type=authorization_code" \
  -d "code=YOUR_AUTH_CODE" \
  -d "redirect_uri=https://localhost:8000/callback" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

Copy the `access_token` from the response → paste in `.env` as `LINKEDIN_ACCESS_TOKEN`.

> **Note:** LinkedIn tokens expire after 60 days. You'll need to refresh mid-campaign if running past Day 60.

---

## Step 4: Configure .env

```env
OPENAI_API_KEY=sk-proj-...
LINKEDIN_ACCESS_TOKEN=AQX...
START_DATE=2024-01-15T08:30:00
POST_INTERVAL_DAYS=1
DRY_RUN=true    ← Keep true until you've verified output
```

---

## Step 5: Test the Pipeline

```bash
# Test 1: Generate all 50 tips (takes ~2 min)
python3 main.py generate

# Check output
cat output/all_tips.json | python3 -m json.tool | head -60

# Test 2: Create schedule
python3 main.py schedule
cat output/posting_schedule.csv

# Test 3: Full dry run (no actual posting)
python3 main.py run

# Test 4: Verify LinkedIn token works
# Change DRY_RUN=false in .env, then:
python3 main.py post --day 1
```

---

## Step 6: Go Live

1. Set `DRY_RUN=false` in `.env`
2. Set `START_DATE` to your desired launch date
3. Run once to generate + schedule:
   ```bash
   python main.py run
   ```

---

## Step 7: Automate with GitHub Actions (Recommended)

```bash
# Push project to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/Gnana-Tech-Page/linkedin-post-agents
git push -u origin main
```

Then add GitHub Secrets:
1. Repo → **Settings** → **Secrets and variables** → **Actions**
2. Add:
   - `OPENAI_API_KEY` = your OpenAI key
   - `LINKEDIN_ACCESS_TOKEN` = your LinkedIn token

The workflow (`.github/workflows/daily_post.yml`) runs automatically at **8:30 AM UTC daily**.

---

## Alternative: Run Locally with Cron

```bash
# Add to crontab (runs daily at 9:00 AM)
crontab -e

# Add this line:
0 9 * * * cd /path/to/linkedin-terraform-bot && /path/to/venv/bin/python main.py run >> /tmp/linkedin-bot.log 2>&1
```

---

## Available Commands

| Command | Description |
|---------|-------------|
| `python main.py run` | Full pipeline (generate → schedule → post → report) |
| `python main.py generate` | Generate all 50 tips, save to JSON |
| `python main.py schedule` | Create posting schedule, export CSV |
| `python main.py post --day N` | Manually post a specific day |
| `python main.py report` | Print analytics report |
| `python main.py reset` | Clear all state (start fresh) |

---

## Project Structure

```
linkedin-terraform-bot/
├── main.py                          # CLI entry point
├── requirements.txt
├── .env.example
├── .github/
│   └── workflows/
│       └── daily_post.yml           # GitHub Actions automation
├── agents/
│   ├── orchestrator.py              # Pipeline coordinator
│   ├── content_agent.py             # OpenAI tip generator
│   ├── scheduler_agent.py           # Timing & schedule builder
│   ├── linkedin_agent.py            # LinkedIn API (OAuth + UGC)
│   └── monitor_agent.py             # Analytics tracker
├── utils/
│   └── state_manager.py             # JSON state persistence
├── state/
│   ├── pipeline_state.json          # Generated tips + schedule
│   └── analytics.json               # Post performance data
└── output/
    ├── all_tips.json                 # All 50 generated tips
    ├── posting_schedule.csv          # Human-readable schedule
    ├── analytics_report.md           # Performance report
    └── pipeline.log                  # Execution logs
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `OPENAI_API_KEY not set` | Add key to `.env` |
| `LinkedIn 401 Unauthorized` | Token expired — re-generate via OAuth flow |
| `LinkedIn 422 Unprocessable` | Post content too long (>3000 chars) — check content_agent.py prompt |
| `Tips already generated` | Run `python main.py reset` to regenerate |
| `No posts due right now` | Check START_DATE in `.env` — it may be in the future |
