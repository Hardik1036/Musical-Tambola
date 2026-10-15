"""
player_app.py - Host Studio & Caller Entry Point
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from main_app import main

if __name__ == "__main__":
    main()
