# Simple script to push to GitHub
Write-Host "=== Push to GitHub ===" -ForegroundColor Green
Write-Host ""

# Check if repo exists locally
if (-not (Test-Path .git)) {
    Write-Host "Error: Not a git repository!" -ForegroundColor Red
    exit 1
}

# Get token from user
$token = Read-Host "Enter your GitHub Personal Access Token (from https://github.com/settings/tokens)"

if ([string]::IsNullOrWhiteSpace($token)) {
    Write-Host "Error: Token is required!" -ForegroundColor Red
    exit 1
}

# Set remote URL with token
Write-Host "Setting remote URL..." -ForegroundColor Yellow
git remote set-url origin "https://$token@github.com/optimizeforall/polymarket-bot.git"

# Push
Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nSuccess! Your code is on GitHub!" -ForegroundColor Green
    Write-Host "Repository: https://github.com/optimizeforall/polymarket-bot" -ForegroundColor Cyan
} else {
    Write-Host "`nPush failed. Make sure:" -ForegroundColor Red
    Write-Host "1. Repository exists at: https://github.com/optimizeforall/polymarket-bot" -ForegroundColor Yellow
    Write-Host "2. Token has 'repo' permissions" -ForegroundColor Yellow
    Write-Host "3. Token is valid and not expired" -ForegroundColor Yellow
}
