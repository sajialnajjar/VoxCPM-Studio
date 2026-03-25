@echo off
:: ╔══════════════════════════════════════════════════════════════╗
:: ║      VoxCPM Studio — Virtual Environment Setup Script       ║
:: ║      Uses Python 3.10  (required for voxcpm compatibility)  ║
:: ╚══════════════════════════════════════════════════════════════╝

setlocal enabledelayedexpansion

set "PYTHON310=python"
set "VENV_DIR=%~dp0venv"
set "REQ_FILE=%~dp0requirements.txt"

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   VoxCPM Studio — Environment Setup     ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── Check Python 3.10 ────────────────────────────────────────
"%PYTHON310%" --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python was not found in your system PATH!
    echo.
    echo  Please install Python 3.10 from:
    echo  https://www.python.org/downloads/release/python-31011/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo  [OK]  Found Python 3.10: %PYTHON310%
"%PYTHON310%" --version
echo.

:: ── Create venv ───────────────────────────────────────────────
if exist "%VENV_DIR%" (
    echo  [INFO] Virtual environment already exists at: %VENV_DIR%
    echo         Skipping creation, proceeding to dependency install...
    echo.
) else (
    echo  [STEP 1/3] Creating virtual environment in: %VENV_DIR%
    "%PYTHON310%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo  [OK]   Virtual environment created.
    echo.
)

:: ── Upgrade pip ───────────────────────────────────────────────
echo  [STEP 2/4] Upgrading pip...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
echo.

:: ── Install PyTorch with CUDA 12.1 (for Nvidia GPU) ──────────────
echo  [STEP 3a/4] Installing PyTorch with CUDA 12.1 support (RTX 3060)...
echo             (This may take a while — ~2.5 GB download)
echo.
"%VENV_DIR%\Scripts\pip.exe" install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 (
    echo  [WARNING] CUDA PyTorch install failed — falling back to CPU version.
)
echo.

:: ── Install dependencies ──────────────────────────────────────
echo  [STEP 3b/4] Installing packages from requirements.txt...
echo             This may take 10-30 minutes.
echo.
"%VENV_DIR%\Scripts\pip.exe" install -r "%REQ_FILE%"
if errorlevel 1 (
    echo.
    echo  [WARNING] Some packages may have failed. Check output above.
    echo            You can retry by running this script again.
) else (
    echo.
    echo  ╔══════════════════════════════════════════════════════════╗
    echo  ║   SUCCESS! All packages installed.                      ║
    echo  ║                                                          ║
    echo  ║   To launch VoxCPM Studio, run:                         ║
    echo  ║      run_studio.bat                                      ║
    echo  ╚══════════════════════════════════════════════════════════╝
)

echo.
pause
endlocal
