#!/bin/bash
# Development Server Startup Script for Linux/Mac
# This script starts the FastAPI server with auto-reload for development

echo "========================================"
echo "Starting RapidPark Development Server"
echo "========================================"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "WARNING: Virtual environment not activated!"
    echo "Please run: source .venv/bin/activate"
    echo ""
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "WARNING: .env file not found!"
    echo "Please copy .env.example to .env and configure your settings."
    echo ""
    echo "Run: cp .env.example .env"
    echo "Then edit .env with your API keys"
    echo ""
    exit 1
fi

# Check if requirements are installed
python -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "WARNING: Dependencies not installed!"
    echo "Please run: pip install -r requirements.txt"
    echo ""
    exit 1
fi

echo "[✓] Virtual environment: Active"
echo "[✓] Environment file: Found"
echo "[✓] Dependencies: Installed"
echo ""
echo "Starting server on http://localhost:8000"
echo ""
echo "Available endpoints:"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Health: http://localhost:8000/health"
echo "  - Reservations: http://localhost:8000/api/reservations"
echo "  - Cartesia Webhook: http://localhost:8000/cartesia/webhook"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
