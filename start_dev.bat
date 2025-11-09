@echo off
REM Development Server Startup Script for Windows
REM This script starts the FastAPI server with auto-reload for development

echo ========================================
echo Starting RapidPark Development Server
echo ========================================
echo.

REM Check if virtual environment is activated
if not defined VIRTUAL_ENV (
    echo WARNING: Virtual environment not activated!
    echo Please run: .venv\Scripts\activate
    echo.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Please copy .env.example to .env and configure your settings.
    echo.
    echo Run: copy .env.example .env
    echo Then edit .env with your API keys
    echo.
    pause
    exit /b 1
)

REM Check if requirements are installed
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo WARNING: Dependencies not installed!
    echo Please run: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo [✓] Virtual environment: Active
echo [✓] Environment file: Found
echo [✓] Dependencies: Installed
echo.
echo Starting server on http://localhost:8000
echo.
echo Available endpoints:
echo   - API Docs: http://localhost:8000/docs
echo   - Health: http://localhost:8000/health
echo   - Reservations: http://localhost:8000/api/reservations
echo   - Cartesia Webhook: http://localhost:8000/cartesia/webhook
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
