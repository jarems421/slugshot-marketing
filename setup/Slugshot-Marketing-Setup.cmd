@echo off
setlocal
set "ROOT=%USERPROFILE%\Slugshot-Marketing-Tools"
where winget >nul 2>&1 || (echo Windows App Installer / winget is required. & pause & exit /b 1)
if not exist "%ROOT%" mkdir "%ROOT%"
echo Installing OBS Studio, Kdenlive and FFmpeg through Windows Package Manager.
echo The installers may request approval. Already-installed packages can be skipped.
winget install --exact --id OBSProject.OBSStudio --source winget --no-upgrade
winget install --exact --id KDE.Kdenlive --source winget --no-upgrade
winget install --exact --id Gyan.FFmpeg --source winget --no-upgrade
winget install --exact --id Python.Python.3.11 --source winget --no-upgrade
winget install --exact --id OpenJS.NodeJS.LTS --source winget --no-upgrade
winget install --exact --id Git.Git --source winget --no-upgrade

echo.
echo Base installation attempted. Check the output above for any errors.
echo Close and reopen your terminal to refresh PATH, then follow the second-stage instructions.
echo Tools workspace: %ROOT%
start "" "%ROOT%"
pause
