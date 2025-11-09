"""
Main entry point for Cartesia deployment
This file is required in the root directory for Cartesia to recognize the FastAPI app
"""
from app.main import app

__all__ = ["app"]

# Cartesia will automatically run this FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
