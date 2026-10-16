"""
Musical Tambola - Cloud & Headless FastAPI Server Entrypoint
Antideploy / Cloud Production Entrypoint for Musical Tambola FastAPI application.
Exposes 'app' and launches uvicorn when executed directly.
"""
import os
import sys
from pathlib import Path

# Configure headless environment defaults immediately before any other module loads
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# Ensure base directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Import FastAPI application
from web_app import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Musical Tambola Cloud Server on http://{host}:{port}")
    uvicorn.run("web_server:app", host=host, port=port, reload=False)
