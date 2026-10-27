# Naukri Profile Daily Refresh & Auto-Applier Agent

Autonomous Playwright agent designed to log into **Naukri.com**, refresh your candidate profile daily at **9:00 AM IST** and **1:00 PM IST**, and automatically apply to matching **Staff/Principal/Lead SDET & AI Automation** roles in Bengaluru.

## Candidate Configuration (Pre-Configured for Shriman Narayan Mishra)
- **Target Roles**: Staff SDET, Principal SDET, SDET Lead, Lead QA Automation Engineer, AI Automation Engineer
- **Tech Stack**: Python, Playwright, Selenium, Agentic AI, RAG, LLMs
- **Location**: Bengaluru / Hybrid / Remote (10+ Years Experience)
- **Compensation**: Current CTC **₹30 LPA** → Expected CTC **₹42 LPA** (pre-filled for Naukri's screening chatbot)

## Features
- **Headless Browser Automation**: Powered by Playwright with realistic user-agent and navigator overrides.
- **Session State Persistence**: Supports one-time interactive login (`--login-setup`) to bypass OTP/CAPTCHA challenges, caching authentication in `naukri_state.json`.
- **Intelligent Headline Toggle**: Subtly toggles a trailing period in your Resume Headline to trigger Naukri’s `Last Updated` timestamp without altering your text.
- **Automated Easy-Apply & Chatbot Screening (`--apply-jobs`)**:
  - Searches top matching roles in Bengaluru (`10+ years` experience).
  - Applies directly to one-click Naukri listings (skipping external company redirects).
  - Automatically answers Naukri's screening chatbot questions (Current CTC: `30`, Expected CTC: `42`, Total Exp: `10`, Python/Playwright Exp, Notice Period: `30 days`).
  - Exports a full audit report to `applied_jobs_summary.md` and `applied_jobs_summary.csv`.

## Project Structure
```text
├── naukri_agent.py             # Main Playwright updater & auto-applier agent
├── naukri_scheduler.yml        # GitHub Actions workflow (9 AM & 1 PM IST cron)
├── requirements.txt            # Python dependencies
├── Shriman_Mishra_SDET_Lead.pdf# Your latest resume (optional re-upload)
└── README.md                   # Setup and execution guide
```

## Deployment Option 1: GitHub Actions (Recommended — 100% Free & Cloud-Hosted)

1. **Create a Private GitHub Repository** (keep it **Private** for credential safety).
2. Push `naukri_agent.py`, `naukri_scheduler.yml` (placed inside `.github/workflows/`), and your resume PDF into the repo.
3. In GitHub, go to **Settings > Secrets and variables > Actions > New repository secret** and add:
   - `NAUKRI_EMAIL`: Your Naukri account email (`shree.n.mishra@gmail.com`).
   - `NAUKRI_PASSWORD`: Your Naukri account password.
   - `NAUKRI_AUTH_STATE_B64` *(Optional, recommended if your account prompts OTP)*:
     - Run `python naukri_agent.py --login-setup` locally to generate `naukri_state.json`.
     - Base64 encode it (`base64 -w 0 naukri_state.json` on Linux, `base64 naukri_state.json` on macOS, or `[Convert]::ToBase64String([IO.File]::ReadAllBytes('naukri_state.json'))` on Windows PowerShell).
4. After each run at **9:00 AM IST** and **1:00 PM IST**, open the **Actions** tab in GitHub to view the rendered **Job Application Summary table** directly in the workflow summary page.

## Deployment Option 2: Local Execution & Cron (macOS / Linux / Windows)

### 1. Install Dependencies
```bash
pip install playwright
playwright install chromium
```

### 2. One-Time Login Setup (Bypass OTP/CAPTCHA)
```bash
python naukri_agent.py --login-setup
```

### 3. Run Profile Update + Auto-Apply Immediately
```bash
python naukri_agent.py --mode headline --apply-jobs --max-apply 5 --no-headless
```

## Command Reference
| Command | Description |
| :--- | :--- |
| `python naukri_agent.py --login-setup` | One-time visible login to capture session cookies. |
| `python naukri_agent.py --mode headline` | Toggles headline trailing dot only. |
| `python naukri_agent.py --mode headline --apply-jobs --max-apply 5` | Refreshes profile and applies to up to 5 matching jobs. |
| `python naukri_agent.py --mode both --resume Shriman_Mishra_SDET_Lead.pdf --apply-jobs` | Updates headline, re-uploads resume PDF, and applies to jobs. |
| `python naukri_agent.py --apply-jobs --no-headless` | Runs job applications in a visible browser window so you can watch live. |
