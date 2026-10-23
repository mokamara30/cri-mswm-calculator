@echo off
REM Push the CRI-MSWM calculator to GitHub.
REM Before running: create an EMPTY public repository named "cri-mswm-calculator"
REM at https://github.com/new (no README, no licence, no .gitignore).
cd /d "%~dp0"
set /p GHUSER=Enter your GitHub username:
git remote remove origin 2>nul
git remote add origin https://github.com/%GHUSER%/cri-mswm-calculator.git
git push -u origin main
echo.
echo If a browser window asked you to sign in to GitHub, approve it and the push completes.
echo Repository: https://github.com/%GHUSER%/cri-mswm-calculator
pause
