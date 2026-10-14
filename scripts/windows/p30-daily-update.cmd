@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" exit /b 2
call "%~dp0project-python.cmd" -m workers.providers.daily --config "%~1"
exit /b %errorlevel%
