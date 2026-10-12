@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
  echo Usage: scripts\windows\start-alphalens.cmd path-to-private-config.json
  exit /b 2
)
rem Bound native-library threads for this local read server; preserve explicit overrides.
if not defined OPENBLAS_NUM_THREADS set "OPENBLAS_NUM_THREADS=1"
if not defined OMP_NUM_THREADS set "OMP_NUM_THREADS=1"
if not defined MKL_NUM_THREADS set "MKL_NUM_THREADS=1"
if not defined NUMEXPR_NUM_THREADS set "NUMEXPR_NUM_THREADS=1"
call "%~dp0project-python.cmd" -m alphalens_api.local.cli --config "%~1" start
exit /b %errorlevel%
