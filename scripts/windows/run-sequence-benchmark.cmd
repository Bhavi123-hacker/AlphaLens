@echo off
setlocal
cd /d "%~dp0..\.."
if not exist ".local-data\lstm-cpu-env\Scripts\python.exe" (
  echo Optional CPU PyTorch research environment is not installed. See the operator runbook.
  exit /b 2
)
set "PYTHONPATH=%CD%;%CD%\apps\api\src;%CD%\ml\data\src;%CD%\ml\features\src;%CD%\ml\labels\src;%CD%\ml\training\src;%CD%\ml\evaluation\src;%CD%\backtesting\src;%CD%\decision\src;%CD%\portfolio\src"
set "OPENBLAS_NUM_THREADS=2"
set "OMP_NUM_THREADS=2"
set "MKL_NUM_THREADS=2"
".local-data\lstm-cpu-env\Scripts\python.exe" -m workers.nse_market.sequence %*
exit /b %errorlevel%
