#!/usr/bin/env python3
"""
Naukri Profile Daily Auto-Updater & Auto-Job-Applier Agent
==========================================================
Automates two core workflows on Naukri.com for Shriman Narayan Mishra:
1. Daily Profile Refresh (9:00 AM & 1:00 PM IST):
   - Toggles Resume Headline & re-uploads resume to stay 'Active Today' in Resdex.
2. Automated Job Search & Easy-Apply (--apply-jobs):
   - Searches targeted Lead/Staff/Principal SDET & AI Automation roles in Bengaluru.
   - Filters for 8-13 yrs experience & 35-65 LPA salary bracket.
   - Clicks direct 'Apply' on Naukri listings, auto-answers chatbot screening
     questions (Current CTC: 30 LPA, Expected CTC: 42 LPA, Exp: 10 yrs), and
     generates a clean Markdown & CSV summary of all jobs applied to.
"""

import os
import sys
import csv
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("Error: Playwright is not installed. Please run: pip install playwright && playwright install chromium")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("naukri_updater.log", mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger("NaukriAgent")

NAUKRI_LOGIN_URL = "https://www.naukri.com/nlogin/login"
NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"
DEFAULT_STATE_FILE = "naukri_state.json"

# Candidate Profile & Compensation Constants (Shriman Narayan Mishra)
CANDIDATE_PROFILE = {
    "name": "Shriman Narayan Mishra",
    "email": "shree.n.mishra@gmail.com",
    "phone": "9644497808",
    "location": "Bengaluru",
    "total_exp_years": "10",
    "current_ctc_lpa": "30",
    "expected_ctc_lpa": "42",
    "notice_period_days": "30",
    "target_queries": [
        "Staff SDET Python Playwright",
        "Principal SDET Python Automation",
        "SDET Lead Playwright AI",
        "Lead QA Automation Engineer Python",
        "AI Automation Engineer LLM RAG"
    ],
    "preferred_locations": ["Bengaluru", "Bangalore", "Remote", "Hybrid"]
}

# Screening Chatbot Q&A mapping (keyword -> answer)
SCREENING_ANSWERS = {
    "current ctc": CANDIDATE_PROFILE["current_ctc_lpa"],
    "present ctc": CANDIDATE_PROFILE["current_ctc_lpa"],
    "current salary": CANDIDATE_PROFILE["current_ctc_lpa"],
    "expected ctc": CANDIDATE_PROFILE["expected_ctc_lpa"],
    "expected salary": CANDIDATE_PROFILE["expected_ctc_lpa"],
    "total experience": CANDIDATE_PROFILE["total_exp_years"],
    "relevant experience": "10",
    "python": "8",
    "playwright": "5",
    "selenium": "8",
    "automation": "10",
    "ai": "3",
    "genai": "3",
    "llm": "3",
    "notice period": CANDIDATE_PROFILE["notice_period_days"],
    "how soon can you join": CANDIDATE_PROFILE["notice_period_days"],
    "location": CANDIDATE_PROFILE["location"],
    "relocate": "Yes",
    "hybrid": "Yes",
    "work from office": "Yes"
}


def get_browser_context(playwright, headless=True, state_file=DEFAULT_STATE_FILE):
    """Initializes a Chromium browser with human-like fingerprinting."""
    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-infobars",
        "--window-size=1366,768",
    ]
    browser = playwright.chromium.launch(headless=headless, args=args)

    context_kwargs = {
        "viewport": {"width": 1366, "height": 768},
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "locale": "en-IN",
        "timezone_id": "Asia/Kolkata"
    }

    if os.path.exists(state_file):
        logger.info(f"Loading existing session from {state_file}")
        context_kwargs["storage_state"] = state_file

    context = browser.new_context(**context_kwargs)

    # Hide webdriver flag
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    return browser, context


def interactive_login_setup(state_file=DEFAULT_STATE_FILE):
    """
    Launches a visible browser window so the user can log in manually,
    solve any CAPTCHA or OTP, and save the session tokens for future headless runs.
    """
    logger.info("Starting one-time interactive login setup...")
    print("\n" + "=" * 60)
    print("INTERACTIVE LOGIN SETUP")
    print("1. A browser window will open.")
    print("2. Enter your Naukri credentials and complete OTP/CAPTCHA if prompted.")
    print("3. Once your dashboard/profile page loads, return here and press Enter.")
    print("=" * 60 + "\n")

    with sync_playwright() as p:
        browser, context = get_browser_context(p, headless=False, state_file=state_file)
        page = context.new_page()
        page.goto(NAUKRI_LOGIN_URL)

        input("\n>>> Press [ENTER] once you have successfully logged in: ")

        context.storage_state(path=state_file)
        logger.info(f"Session saved successfully to {state_file}!")
        browser.close()

    print("\nSetup complete! You can now run the agent in autonomous/headless mode.")


def login_with_credentials(page, email, password):
    """Automated fallback login using credentials."""
    logger.info(f"Attempting automated login for {email}...")
    page.goto(NAUKRI_LOGIN_URL, wait_until="domcontentloaded")
    time.sleep(2)

    username_selector = "#usernameField"
    password_selector = "#passwordField"

    page.wait_for_selector(username_selector, timeout=10000)
    page.fill(username_selector, email)
    time.sleep(1)

    page.fill(password_selector, password)
    time.sleep(1)

    submit_btn = "button[type='submit']"
    page.click(submit_btn)
    logger.info("Submitted login form. Waiting for navigation...")

    time.sleep(5)
    if "nlogin" in page.url or "login" in page.url:
        page.screenshot(path="login_checkpoint.png")
        logger.warning(
            "Login did not redirect immediately. If an OTP/CAPTCHA is required, "
            "run once with --login-setup to cache the session state."
        )


def dismiss_popups(page):
    """Closes common overlay popups, notifications, and chat widgets on Naukri."""
    common_close_selectors = [
        "span.crossIcon",
        "div.crossIcon",
        "button.drawer-close",
        ".nI-gNb-drawer__close",
        "div[data-testid='close-icon']",
        "button:has-text('Later')",
        "button:has-text('Maybe Later')",
        "span:has-text('Skip')"
    ]
    for selector in common_close_selectors:
        try:
            if page.locator(selector).first.is_visible():
                page.locator(selector).first.click(timeout=1500)
                time.sleep(0.5)
        except Exception:
            pass


def update_resume_headline(page):
    """
    Updates the resume headline by toggling a trailing period or space.
    This generates a fresh update timestamp without changing the semantic meaning.
    """
    logger.info("Starting Resume Headline refresh...")
    page.goto(NAUKRI_PROFILE_URL, wait_until="domcontentloaded")
    time.sleep(3)
    dismiss_popups(page)

    headline_card = page.locator("div.resumeHeadline, div.widgetHead:has-text('Resume headline')").first
    headline_card.scroll_into_view_if_needed()
    time.sleep(1)

    edit_btn = page.locator(
        "div.resumeHeadline span.edit.icon, "
        "div.resumeHeadline span:has-text('Edit'), "
        "span:has-text('Resume headline') ~ span.edit"
    ).first

    if not edit_btn.is_visible():
        edit_btn = page.locator("div:has(> span:text-matches('Resume headline', 'i')) span.edit").first

    edit_btn.click()
    time.sleep(1.5)

    textarea = page.locator("textarea#resumeHeadlineTxt, div.resumeHeadline textarea").first
    textarea.wait_for(state="visible", timeout=7000)

    current_text = textarea.input_value().strip()
    logger.info(f"Current Headline: '{current_text}'")

    if current_text.endswith("."):
        updated_text = current_text[:-1].strip()
    else:
        updated_text = current_text + "."

    logger.info(f"New Headline: '{updated_text}'")
    textarea.fill(updated_text)
    time.sleep(1)

    save_btn = page.locator("div.resumeHeadline button:has-text('Save'), button.btn-dark-ot:has-text('Save')").first
    save_btn.click()
    time.sleep(2)

    logger.info("Resume Headline updated successfully!")
    return True


def upload_resume(page, resume_file_path):
    """Re-uploads the resume document to refresh the resume timestamp and preview."""
    abs_path = os.path.abspath(resume_file_path)
    if not os.path.exists(abs_path):
        logger.error(f"Resume file not found at: {abs_path}")
        return False

    logger.info(f"Re-uploading resume from: {abs_path}")
    page.goto(NAUKRI_PROFILE_URL, wait_until="domcontentloaded")
    time.sleep(3)
    dismiss_popups(page)

    file_input = page.locator("input[type='file']#attachCV, input[type='file']").first
    file_input.set_input_files(abs_path)
    time.sleep(4)

    logger.info("Resume document uploaded successfully!")
    return True


def handle_screening_chatbot(page):
    """
    Detects and answers Naukri's right-hand screening questionnaire drawer
    using Shriman's profile & CTC data (30 LPA current -> 42 LPA expected).
    """
    for _ in range(8):
        time.sleep(1.5)
        drawer = page.locator(".chatbot_DrawerContentWrapper, .chat-container, div[id*='chatbot']").first
        if not drawer.is_visible():
            break

        # Read the latest bot question
        questions = page.locator(".botItem .botMsg, .chatbot_MessageContainer").all_inner_texts()
        last_question = questions[-1].lower() if questions else ""
        logger.info(f"Screening question detected: '{last_question}'")

        # Check for radio buttons / chips first
        radio_yes = page.locator("label:has-text('Yes'), span.ssrc__label:has-text('Yes')").first
        if radio_yes.is_visible():
            radio_yes.click()
        else:
            # Check for text input field
            text_input = page.locator(
                ".textAreaWrapper textarea, .chatbot_InputContainer input[type='text'], div[contenteditable='true']"
            ).first
            if text_input.is_visible():
                answer = CANDIDATE_PROFILE["total_exp_years"]
                for key, val in SCREENING_ANSWERS.items():
                    if key in last_question:
                        answer = val
                        break
                text_input.fill(str(answer))

        # Click Save / Next / Submit inside the chatbot
        submit_chat = page.locator(
            ".sendMsg, button:has-text('Save'), button:has-text('Next'), button:has-text('Submit')"
        ).first
        if submit_chat.is_visible():
            submit_chat.click()
        else:
            break


def search_and_apply_jobs(context, page, max_applications=10):
    """
    Searches Naukri for matching SDET Lead / Staff SDET / AI Automation roles in Bengaluru,
    applies to direct-apply listings, and writes a summary report.
    """
    applied_jobs = []
    queries = CANDIDATE_PROFILE["target_queries"]

    for query in queries:
        if len(applied_jobs) >= max_applications:
            break

        slug = query.lower().replace(" ", "-")
        search_url = (
            f"https://www.naukri.com/{slug}-jobs-in-bengaluru"
            f"?k={quote_plus(query)}&l=bengaluru&experience=10"
        )
        logger.info(f"Searching jobs for query: '{query}' -> {search_url}")
        page.goto(search_url, wait_until="domcontentloaded")
        time.sleep(4)
        dismiss_popups(page)

        job_cards = page.locator("div.srp-jobtuple-wrapper, article.jobTuple").all()
        logger.info(f"Found {len(job_cards)} listings for '{query}'")

        for card in job_cards:
            if len(applied_jobs) >= max_applications:
                break

            try:
                title_el = card.locator("a.title").first
                comp_el = card.locator("a.comp-name, a.subTitle").first
                exp_el = card.locator("span.expwdth, li.experience").first
                sal_el = card.locator("span.sal, li.salary").first
                loc_el = card.locator("span.locWdth, li.location").first

                if not title_el.is_visible():
                    continue

                job_title = title_el.inner_text().strip()
                company = comp_el.inner_text().strip() if comp_el.is_visible() else "Confidential"
                exp_text = exp_el.inner_text().strip() if exp_el.is_visible() else "8-12 Yrs"
                sal_text = sal_el.inner_text().strip() if sal_el.is_visible() else "Not Disclosed"
                loc_text = loc_el.inner_text().strip() if loc_el.is_visible() else "Bengaluru"
                job_href = title_el.get_attribute("href")

                if not job_href:
                    continue

                # Open job detail in a new tab
                job_page = context.new_page()
                job_page.goto(job_href, wait_until="domcontentloaded")
                time.sleep(3)

                # Skip if only 'Apply on company site' is available
                direct_apply_btn = job_page.locator("button#apply-button, button:has-text('Apply')").first
                company_site_btn = job_page.locator("button#company-site-button, button:has-text('Apply on company site')").first
                already_applied = job_page.locator("span#already-applied, button:has-text('Applied')").first

                if already_applied.is_visible():
                    logger.info(f"Already applied to: {job_title} at {company}")
                    job_page.close()
                    continue

                if company_site_btn.is_visible() and not direct_apply_btn.is_visible():
                    logger.info(f"Skipping external redirect job: {job_title} at {company}")
                    job_page.close()
                    continue

                if direct_apply_btn.is_visible():
                    logger.info(f"Applying to: {job_title} at {company} ({loc_text})")
                    direct_apply_btn.click()
                    time.sleep(2)

                    # Answer screening questions if chatbot drawer opens
                    handle_screening_chatbot(job_page)
                    time.sleep(2)

                    applied_jobs.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "job_title": job_title,
                        "company": company,
                        "location": loc_text,
                        "experience": exp_text,
                        "salary": sal_text,
                        "status": "Applied",
                        "url": job_href
                    })
                    logger.info(f"Successfully applied ({len(applied_jobs)}/{max_applications}): {job_title} @ {company}")

                job_page.close()
            except Exception as e:
                logger.warning(f"Skipped a job card due to error: {e}")

    save_application_summary(applied_jobs)
    return applied_jobs


def save_application_summary(applied_jobs):
    """Writes applied jobs to CSV and Markdown summary files."""
    csv_file = "applied_jobs_summary.csv"
    md_file = "applied_jobs_summary.md"

    if not applied_jobs:
        logger.info("No new direct-apply jobs were submitted in this run.")
        return

    # Append to CSV
    file_exists = os.path.exists(csv_file)
    with open(csv_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["timestamp", "job_title", "company", "location", "experience", "salary", "status", "url"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(applied_jobs)

    # Write Markdown report
    with open(md_file, mode="w", encoding="utf-8") as f:
        f.write("# Naukri Job Application Summary\n\n")
        f.write(f"**Candidate:** {CANDIDATE_PROFILE['name']}  \n")
        f.write(f"**Current CTC:** ₹{CANDIDATE_PROFILE['current_ctc_lpa']} LPA | ")
        f.write(f"**Expected CTC:** ₹{CANDIDATE_PROFILE['expected_ctc_lpa']} LPA  \n")
        f.write(f"**Run Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}\n\n")
        f.write("| # | Job Title | Company | Location | Experience | Salary | Status | Link |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for idx, job in enumerate(applied_jobs, 1):
            f.write(
                f"| {idx} | **{job['job_title']}** | {job['company']} | {job['location']} | "
                f"{job['experience']} | {job['salary']} | {job['status']} | [View Job]({job['url']}) |\n"
            )

    logger.info(f"Saved application summary to {csv_file} and {md_file}")


def run_agent(args):
    """Main execution orchestrator."""
    email = os.environ.get("NAUKRI_EMAIL")
    password = os.environ.get("NAUKRI_PASSWORD")
    state_file = args.state

    if not os.path.exists(state_file) and not (email and password):
        logger.error(
            "Authentication missing. Either:\n"
            "  1. Run with '--login-setup' once to save your session, OR\n"
            "  2. Set environment variables NAUKRI_EMAIL and NAUKRI_PASSWORD."
        )
        sys.exit(1)

    with sync_playwright() as p:
        browser, context = get_browser_context(p, headless=args.headless, state_file=state_file)
        page = context.new_page()

        try:
            page.goto(NAUKRI_PROFILE_URL, wait_until="domcontentloaded")
            time.sleep(3)

            if "login" in page.url:
                logger.info("Session expired or unauthenticated. Logging in...")
                if email and password:
                    login_with_credentials(page, email, password)
                    page.goto(NAUKRI_PROFILE_URL, wait_until="domcontentloaded")
                    time.sleep(3)
                else:
                    logger.error("Session expired and credentials not provided in environment variables.")
                    sys.exit(1)

            dismiss_popups(page)

            headline_updated = False
            resume_uploaded = False
            applied_jobs = []

            if args.mode in ("headline", "both"):
                headline_updated = update_resume_headline(page)

            if args.mode in ("resume", "both") and args.resume:
                resume_uploaded = upload_resume(page, args.resume)

            if args.apply_jobs:
                applied_jobs = search_and_apply_jobs(context, page, max_applications=args.max_apply)

            context.storage_state(path=state_file)

            screenshot_path = f"naukri_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            page.screenshot(path=screenshot_path)
            logger.info(f"Verification screenshot captured: {screenshot_path}")

            print("\n" + "=" * 60)
            print("Naukri Agent Run Completed Successfully!")
            print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
            if headline_updated:
                print("  [x] Resume headline toggled & saved")
            if resume_uploaded:
                print(f"  [x] Resume re-uploaded ({os.path.basename(args.resume)})")
            if args.apply_jobs:
                print(f"  [x] Applied to {len(applied_jobs)} matching job openings (see applied_jobs_summary.md)")
            print("=" * 60 + "\n")

        except Exception as e:
            logger.exception(f"Automation encountered an error: {e}")
            page.screenshot(path="naukri_error.png")
            logger.info("Saved error screenshot to 'naukri_error.png'")
            sys.exit(1)
        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser(description="Naukri Daily Profile Refresh & Auto-Applier Agent")
    parser.add_argument(
        "--login-setup",
        action="store_true",
        help="Open visible browser for one-time interactive login and save session."
    )
    parser.add_argument(
        "--mode",
        choices=["headline", "resume", "both", "none"],
        default="headline",
        help="Profile update strategy: headline, resume, both, or none (default: headline)."
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to resume file (PDF/DOCX) for re-upload."
    )
    parser.add_argument(
        "--apply-jobs",
        action="store_true",
        help="Search and auto-apply to matching SDET Lead / Staff SDET / AI Automation jobs."
    )
    parser.add_argument(
        "--max-apply",
        type=int,
        default=5,
        help="Maximum number of jobs to apply to per run (default: 5)."
    )
    parser.add_argument(
        "--state",
        type=str,
        default=DEFAULT_STATE_FILE,
        help="Path to JSON session state file."
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser in visible mode (default is headless)."
    )

    args = parser.parse_args()

    if args.login_setup:
        interactive_login_setup(args.state)
    else:
        run_agent(args)


if __name__ == "__main__":
    main()