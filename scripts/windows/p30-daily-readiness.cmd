@echo off
setlocal
if "%~1"=="" exit /b 2
set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
call "%~dp0project-python.cmd" -m workers.providers.automation --config "%~1"
exit /b %errorlevel%
