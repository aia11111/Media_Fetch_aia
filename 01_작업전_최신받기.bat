@echo off
set "GITBASH=C:\Program Files\Git\bin\bash.exe"
set "REPO_UNIX=/d/AI/coding/Playground/new_youtube_downloader_gpt"

if not exist "%GITBASH%" (
    echo Git Bash not found:
    echo %GITBASH%
    pause
    exit /b 1
)

"%GITBASH%" -lc "cd '%REPO_UNIX%' && echo [START] Pulling latest changes... && git pull"

echo.
echo Done. Latest files have been downloaded.
pause