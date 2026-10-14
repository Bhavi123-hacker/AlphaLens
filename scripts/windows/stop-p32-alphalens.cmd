@echo off
setlocal
cd /d "%~dp0..\.."
call "%~dp0stop-alphalens.cmd" "%CD%\.local-data\p32-runtime\operator-config.json"
if errorlevel 1 exit /b 1
call "%~dp0project-python.cmd" -m scripts.p30_local_database stop
exit /b %errorlevel%
