@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
  echo Usage: scripts\windows\stop-alphalens.cmd path-to-private-config.json
  exit /b 2
)
call "%~dp0project-python.cmd" -m alphalens_api.local.cli --config "%~1" stop
exit /b %errorlevel%
