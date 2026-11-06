@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
  echo Usage: run-v2-research.cmd PRIVATE_CONFIG [--dry-run^|--collect^|--scheduled]
  exit /b 2
)
if not exist "%~f1" (
  echo Private V2 configuration was not found.
  exit /b 2
)
if not "%~3"=="" (
  echo Unexpected arguments. No collection was started.
  exit /b 2
)
if "%~2"=="" goto dryrun
if "%~2"=="--dry-run" goto dryrun
if "%~2"=="--collect" goto collect
if "%~2"=="--scheduled" goto scheduled
echo Unsupported operation. No collection was started.
exit /b 2
:dryrun
call "%~dp0project-python.cmd" -m workers.experimental_nse_v2 run --config "%~f1" --dry-run
exit /b %errorlevel%
:collect
call "%~dp0project-python.cmd" -m workers.experimental_nse_v2 run --config "%~f1" --collect
exit /b %errorlevel%
:scheduled
rem The worker independently requires the exact approved cadence/cohort/quota receipt.
call "%~dp0project-python.cmd" -m workers.experimental_nse_v2 run --config "%~f1" --scheduled
exit /b %errorlevel%
