#!/usr/bin/env bash
# ==============================================================================
# One-Command GitHub Repository & Naukri Scheduler Setup Script
# ==============================================================================
set -e

REPO_NAME="naukri-daily-agent"

echo "1. Initializing local Git repository..."
git init
git branch -M main

mkdir -p .github/workflows
if [ -f "naukri_scheduler.yml" ]; then
  cp -f naukri_scheduler.yml .github/workflows/naukri_scheduler.yml
fi

cat << 'GITIGNORE' > .gitignore
naukri_state.json
*.png
*.log
__pycache__/
.env
GITIGNORE

git add .
git commit -m "Initialize Naukri Daily Refresh & Auto-Applier Agent (9 AM & 1 PM IST)" || true

if command -v gh &> /dev/null; then
  echo "2. GitHub CLI (gh) detected! Creating private repository '$REPO_NAME' and pushing code..."
  gh repo create "$REPO_NAME" --private --source=. --remote=origin --push

  echo ""
  echo "3. Configuring GitHub Actions Repository Secrets..."
  read -p "Enter your Naukri Email [default: shree.n.mishra@gmail.com]: " NAUKRI_EMAIL_INPUT
  NAUKRI_EMAIL_INPUT=${NAUKRI_EMAIL_INPUT:-shree.n.mishra@gmail.com}
  gh secret set NAUKRI_EMAIL --body "$NAUKRI_EMAIL_INPUT"

  read -s -p "Enter your Naukri Password: " NAUKRI_PASS_INPUT
  echo ""
  gh secret set NAUKRI_PASSWORD --body "$NAUKRI_PASS_INPUT"

  if [ -f "naukri_state.json" ]; then
    echo "Encoding naukri_state.json and uploading as NAUKRI_AUTH_STATE_B64 secret..."
    B64_STATE=$(python3 -c "import base64; print(base64.b64encode(open('naukri_state.json','rb').read()).decode())")
    gh secret set NAUKRI_AUTH_STATE_B64 --body "$B64_STATE"
  fi

  echo ""
  echo "4. Triggering an immediate workflow run on GitHub Actions..."
  gh workflow run naukri_scheduler.yml
  echo "Success! Your Naukri scheduler is live and scheduled for 9:00 AM and 1:00 PM IST daily."
else
  echo "GitHub CLI (gh) is not installed. To push manually:"
  echo "  1. Create an empty private repo at https://github.com/new named '$REPO_NAME'"
  echo "  2. Run: git remote add origin https://github.com/<your-github-username>/$REPO_NAME.git"
  echo "  3. Run: git push -u origin main"
fi
