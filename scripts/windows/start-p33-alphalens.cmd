@echo off
setlocal
cd /d "%~dp0..\.."
call "%~dp0project-python.cmd" -m scripts.p30_local_database start
if errorlevel 1 exit /b 1
call "%~dp0start-alphalens.cmd" "%CD%\.local-data\p33-runtime\operator-config.json"
exit /b %errorlevel%
