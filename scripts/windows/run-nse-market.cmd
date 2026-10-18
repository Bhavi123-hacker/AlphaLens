@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" goto usage
if not "%~4"=="" goto usage
if not exist "%~f1" (
  echo Protected NSE research configuration was not found.
  exit /b 2
)
if "%~3"=="" goto dryrun
if "%~3"=="--dry-run" goto dryrun
if "%~3"=="--collect" goto collect
if "%~3"=="--scheduled" goto scheduled
goto usage
:dryrun
if "%~2"=="" goto autodry
if "%~2"=="auto" goto autodry
call "%~dp0project-python.cmd" -m workers.nse_market run --config "%~f1" --session "%~2"
exit /b %errorlevel%
:autodry
call "%~dp0project-python.cmd" -m workers.nse_market run --config "%~f1"
exit /b %errorlevel%
:collect
if "%~2"=="auto" goto autocollect
call "%~dp0project-python.cmd" -m workers.nse_market run --config "%~f1" --session "%~2" --collect
exit /b %errorlevel%
:autocollect
call "%~dp0project-python.cmd" -m workers.nse_market run --config "%~f1" --collect
exit /b %errorlevel%
:scheduled
if "%~2"=="auto" goto autoscheduled
rem A disabled default and exact independent approval receipt protect this path.
call "%~dp0project-python.cmd" -m workers.nse_market run --config "%~f1" --session "%~2" --scheduled
exit /b %errorlevel%
:autoscheduled
call "%~dp0project-python.cmd" -m workers.nse_market run --config "%~f1" --scheduled
exit /b %errorlevel%
:usage
echo Usage: run-nse-market.cmd PRIVATE_CONFIG [auto^|YYYY-MM-DD] [--dry-run^|--collect^|--scheduled]
echo Default is dry run. This script does not register or enable a scheduled task.
exit /b 2
