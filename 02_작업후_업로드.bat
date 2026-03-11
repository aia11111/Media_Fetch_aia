@echo off
set "GITBASH=C:\Program Files\Git\bin\bash.exe"
set "REPO_UNIX=/d/AI/coding/Playground/new_youtube_downloader_gpt"

if not exist "%GITBASH%" (
    echo Git Bash not found:
    echo %GITBASH%
    pause
    exit /b 1
)

"%GITBASH%" -lc "cd '%REPO_UNIX%' && echo [END] Adding files... && git add . && if git diff --cached --quiet; then echo No changes to commit.; else git commit -m 'sync from pc'; git push; fi"

echo.
echo Done. Files have been uploaded.
pause