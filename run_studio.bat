@echo off
:: ── Launch VoxCPM Studio using the local venv ─────────────────
setlocal
set "VENV_PYTHON=%~dp0venv\Scripts\python.exe"
set "SCRIPT=%~dp0voxcpm_studio.py"

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found. Run setup_venv.bat first!
    pause
    exit /b 1
)

echo Launching VoxCPM Studio...
"%VENV_PYTHON%" "%SCRIPT%"
endlocal
