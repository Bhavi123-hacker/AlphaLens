@echo off
setlocal
cd /d "%~dp0..\.."
if "%~2"=="" (
  echo Usage: scripts\windows\backup-alphalens.cmd private-config.json NEW-backup-directory
  exit /b 2
)
call "%~dp0project-python.cmd" -m alphalens_api.local.cli --config "%~1" backup --destination "%~2"
exit /b %errorlevel%
