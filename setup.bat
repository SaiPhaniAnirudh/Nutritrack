@echo off
REM ──────────────────────────────────────────────────────────────────────────
REM  NutriTrack — setup.bat  (Windows first-run setup)
REM  Run once from the project root to configure your local dev environment.
REM ──────────────────────────────────────────────────────────────────────────

echo.
echo ==============================================
echo   NutriTrack - First-Run Setup (Windows)
echo ==============================================
echo.

REM ── 1. Check Python ────────────────────────────────────────────────────────
echo [1/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python not found. Install from https://python.org
    pause
    exit /b 1
)
python --version
echo.

REM ── 2. Virtual environment ─────────────────────────────────────────────────
echo [2/4] Setting up virtual environment...
if not exist ".venv" (
    python -m venv .venv
    echo  Created .venv
) else (
    echo  .venv already exists
)

call .venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo  Python dependencies installed
echo.

REM ── 3. .env file ───────────────────────────────────────────────────────────
echo [3/4] Checking .env...
if not exist ".env" (
    copy .env.example .env >nul
    echo  .env created from .env.example
    echo  Edit .env to customize settings if needed
) else (
    echo  .env already exists
)
echo.

REM ── 4. Ollama model ────────────────────────────────────────────────────────
echo [4/4] Checking Ollama...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  WARNING: Ollama not found.
    echo  Download from: https://ollama.com/download
    echo  After installing, run: ollama pull llava-phi3
) else (
    echo  Ollama found. Pulling llava-phi3 model (~2.9 GB, one-time download)...
    ollama pull llava-phi3
    echo  Model ready.
)
echo.

REM ── Done ───────────────────────────────────────────────────────────────────
echo ==============================================
echo   Setup complete! Start NutriTrack:
echo ==============================================
echo.
echo  Step 1 - Start Ollama (if not already running):
echo     ollama serve
echo.
echo  Step 2 - Open a NEW terminal, activate venv, start AI server:
echo     .venv\Scripts\activate.bat
echo     python llm\Llm_server.py
echo.
echo  Step 3 - Open ANOTHER terminal, start Flask API:
echo     .venv\Scripts\activate.bat
echo     python backend\App.py
echo.
echo  Step 4 - Open in browser:
echo     http://localhost:5000
echo.
echo ==============================================
pause
