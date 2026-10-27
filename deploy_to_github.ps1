# ==============================================================================
# One-Command GitHub Repository & Naukri Scheduler Setup Script (Windows PowerShell)
# ==============================================================================
$ErrorActionPreference = "Stop"

$RepoName = "naukri-daily-agent"

Write-Host "1. Initializing local Git repository..." -ForegroundColor Cyan
git init
git branch -M main

# Ensure .github/workflows directory exists and copy workflow
if (-not (Test-Path ".github\workflows")) {
    New-Item -ItemType Directory -Force -Path ".github\workflows" | Out-Null
}

if (Test-Path "naukri_scheduler.yml") {
    Copy-Item -Force "naukri_scheduler.yml" ".github\workflows\naukri_scheduler.yml"
}

# Create .gitignore if missing
if (-not (Test-Path ".gitignore")) {
    @"
naukri_state.json
*.png
*.log
__pycache__/
.env
"@ | Out-File -Encoding utf8 ".gitignore"
}

git add .
git commit -m "Initialize Naukri Daily Refresh & Auto-Applier Agent (9 AM & 1 PM IST)" 2>$null

Write-Host "`nChecking for GitHub CLI (gh)..." -ForegroundColor Cyan
if (Get-Command gh -ErrorAction SilentlyContinue) {
    Write-Host "GitHub CLI detected! Creating private repository '$RepoName' and pushing code..." -ForegroundColor Green
    gh repo create "$RepoName" --private --source=. --remote=origin --push

    Write-Host "`nSetting up encrypted GitHub Actions Secrets..." -ForegroundColor Cyan
    $email = Read-Host "Enter your Naukri Email [default: shree.n.mishra@gmail.com]"
    if ([string]::IsNullOrWhiteSpace($email)) { $email = "shree.n.mishra@gmail.com" }
    gh secret set NAUKRI_EMAIL --body "$email"

    $pass = Read-Host "Enter your Naukri Password" -AsSecureString
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($pass)
    $plainPass = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    gh secret set NAUKRI_PASSWORD --body "$plainPass"

    if (Test-Path "naukri_state.json") {
        Write-Host "Encoding naukri_state.json and uploading as NAUKRI_AUTH_STATE_B64..." -ForegroundColor Green
        $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("naukri_state.json"))
        gh secret set NAUKRI_AUTH_STATE_B64 --body "$b64"
    }

    Write-Host "`nTriggering immediate test run on GitHub Actions..." -ForegroundColor Green
    gh workflow run naukri_scheduler.yml
    Write-Host "`nSUCCESS! Your Naukri scheduler is live and scheduled for 9:00 AM and 1:00 PM IST daily." -ForegroundColor Green
} else {
    Write-Host "`nGit repository prepared locally!" -ForegroundColor Green
    Write-Host "To link and push to your GitHub account:" -ForegroundColor Yellow
    Write-Host "1. Create an empty private repository at https://github.com/new named '$RepoName'"
    Write-Host "2. Run these two commands in this terminal:" -ForegroundColor Yellow
    Write-Host "   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/$RepoName.git"
    Write-Host "   git push -u origin main"
}
