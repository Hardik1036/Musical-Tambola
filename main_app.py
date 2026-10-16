"""
Musical Housie (Tambola) — Master Desktop Suite & Motion Graphics Stage
=======================================================================
A complete, production-grade, 60-FPS multi-screen offline desktop application
featuring a Solid Light & Pastel UI theme (#F4F7FC, #FFFFFF, #E2E8F4):
  - Screen 1: 🎯 Live Ball Roller & Master Stage (3D Physics Ball Drop Chute,
              Shockwave Ring, Audio Deck, 10x9 Master Calling Matrix)
  - Screen 2: 🔮 3D Audio Dot-Sphere Visualizer (280-point 3D Fibonacci Particle
              Lattice, continuous perspective rotation, audio-reactive pulse)
  - Screen 3: 🎰 Mechanical Slot Lucky Draw (Dual-drum mechanical roller,
              multi-winner selection, ttk.Treeview audit log)
  - Screen 4: 🔍 Animated Claim Verifier (Batch registry auto-loader,
              staggered 25ms scanline reveal, real-time automated verdict engine)
  - Screen 5: 🎫 Non-Destructive Ticket Studio (2-strip A4 generator,
              STRICT collision guard protecting pre-printed tickets)

Zero cloud dependencies. Built with Python Tkinter, TTK, and Pygame.
"""

import os
import sys
import re
import json
import math
import time
import random
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any

# Headless & platform environment guards
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# Guard Tkinter imports for headless / cloud container environments
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    TKINTER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    TKINTER_AVAILABLE = False

    class _DummyWidget:
        def __init__(self, *args, **kwargs):
            pass
        def get(self, *args, **kwargs):
            return ""
        def set(self, *args, **kwargs):
            pass
        def pack(self, *args, **kwargs):
            pass
        def grid(self, *args, **kwargs):
            pass
        def place(self, *args, **kwargs):
            pass
        def configure(self, *args, **kwargs):
            pass
        config = configure
        def bind(self, *args, **kwargs):
            pass
        def unbind(self, *args, **kwargs):
            pass
        def destroy(self):
            pass
        def winfo_toplevel(self):
            return self
        def winfo_screenwidth(self):
            return 1920
        def winfo_screenheight(self):
            return 1080
        def mainloop(self):
            pass
        def __call__(self, *args, **kwargs):
            return self

    class _DummyTkMeta(type):
        def __getattr__(cls, name):
            return _DummyWidget

    class _DummyTkModule(metaclass=_DummyTkMeta):
        Tk = _DummyWidget
        Frame = _DummyWidget
        Canvas = _DummyWidget
        Toplevel = _DummyWidget
        Button = _DummyWidget
        Label = _DummyWidget
        Entry = _DummyWidget
        Checkbutton = _DummyWidget
        Radiobutton = _DummyWidget
        StringVar = _DummyWidget
        IntVar = _DummyWidget
        DoubleVar = _DummyWidget
        BooleanVar = _DummyWidget
        Menu = _DummyWidget
        Scrollbar = _DummyWidget
        Text = _DummyWidget
        Event = object
        def __getattr__(self, name):
            return _DummyWidget

    tk = _DummyTkModule()
    ttk = _DummyTkModule()
    messagebox = _DummyTkModule()
    filedialog = _DummyTkModule()

# Guard PIL ImageTk import (ImageTk internally imports _tkinter)
try:
    from PIL import Image, ImageTk
except (ImportError, ModuleNotFoundError):
    from PIL import Image
    ImageTk = None

# Base directory setup
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import TICKETS_ARCHIVE_DIR, BRANDING_DIR, SONGS_DIR
import song_bank
import database
import shutil
from generator.generate_housie_tickets import (
    generate_housie_tickets,
    sanitize_batch_name,
    resolve_unique_batch_name
)

# Initialize Pygame audio mixer safely with headless dummy audio support
try:
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
    HAS_AUDIO = True
except Exception as e:
    HAS_AUDIO = False
    print(f"Notice: Pygame audio mixer initialized in fallback mode: {e}")

# ---------------------------------------------------------------------------
# AUDIO CONFIGURATION & CUE MANAGEMENT (PRD Modules 1 & 2)
# ---------------------------------------------------------------------------
AUDIO_CONFIG_PATH = BASE_DIR / "audio_config.json"
AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac")


def parse_time_to_seconds(val: Any) -> float:
    """
    Converts 'MM:SS' (e.g. '01:15' -> 75.0), 'HH:MM:SS', raw numbers ('45' -> 45.0),
    or strings with unit suffixes ('30s') into float seconds.
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return max(0.0, float(val))
    s = str(val).strip()
    if not s:
        return 0.0
    for suffix in ["seconds", "second", "secs", "sec", "s"]:
        if s.lower().endswith(suffix):
            s = s[:-len(suffix)].strip()
            break
    parts = s.split(":")
    try:
        if len(parts) == 1:
            return max(0.0, float(parts[0]))
        elif len(parts) == 2:
            return max(0.0, int(parts[0]) * 60 + float(parts[1]))
        elif len(parts) == 3:
            return max(0.0, int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2]))
    except Exception:
        return 0.0
    return 0.0


def format_seconds_to_time(val: Any) -> str:
    """Converts float seconds into human-friendly 'MM:SS' (or 'HH:MM:SS') timestamp."""
    try:
        sec = max(0.0, float(val))
    except Exception:
        return "00:00"
    total_sec = int(round(sec))
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def load_audio_config() -> Dict[str, Any]:
    """Loads persistent audio configuration or initializes defaults."""
    default_cfg: Dict[str, Any] = {
        "audio_folder_path": str(SONGS_DIR.resolve()) if SONGS_DIR.exists() else str(BASE_DIR / "songs"),
        "song_cues": {}
    }
    if not AUDIO_CONFIG_PATH.exists():
        try:
            with open(AUDIO_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(default_cfg, f, indent=2)
        except Exception:
            pass
        return default_cfg

    try:
        with open(AUDIO_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            return default_cfg
        if "audio_folder_path" not in cfg:
            cfg["audio_folder_path"] = default_cfg["audio_folder_path"]
        if "song_cues" not in cfg or not isinstance(cfg["song_cues"], dict):
            cfg["song_cues"] = {}
        return cfg
    except Exception as e:
        print(f"Notice: Failed to read {AUDIO_CONFIG_PATH}: {e}")
        return default_cfg


def save_audio_config(cfg: Dict[str, Any]):
    """Saves persistent audio configuration."""
    try:
        with open(AUDIO_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Error saving {AUDIO_CONFIG_PATH}: {e}")


def match_song_number_from_filename(filename: str) -> Optional[int]:
    """
    Smartly matches song number (1-90) from filenames like:
    '1.mp3', '01.mp3', '1 - Song.mp3', '01_Song.mp3', 'Track 01.mp3', 'Song - 07.mp3'.
    """
    stem = Path(filename).stem.strip()

    # 1. Exact number: '1', '01', '90'
    m = re.match(r"^0*([1-9]|[1-8][0-9]|90)$", stem)
    if m:
        return int(m.group(1))

    # 2. Leading number with separator: '1 - Song', '01. Song', 'Track 01 - Song', 'Track_05'
    m = re.match(r"^(?:track[_\s-]*)?0*([1-9]|[1-8][0-9]|90)[\s\._\-]", stem, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # 3. Trailing number with separator: 'Song - 01', 'Song_12'
    m = re.search(r"[\s\._\-]0*([1-9]|[1-8][0-9]|90)$", stem, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # 4. Standalone number anywhere between non-digit boundaries (if exactly one 1-90 number is found)
    nums = re.findall(r"(?<!\d)0*([1-9]|[1-8][0-9]|90)(?!\d)", stem)
    if len(nums) == 1:
        return int(nums[0])

    return None


def scan_audio_folder(folder_path: str) -> Dict[int, str]:
    """
    Scans a directory for audio files matching tracks 1 through 90.
    Returns {number: absolute_file_path}.
    """
    matched: Dict[int, str] = {}
    folder = Path(folder_path)
    if not folder.is_dir():
        return matched

    try:
        for entry in folder.iterdir():
            if entry.is_file() and entry.suffix.lower() in AUDIO_EXTENSIONS:
                num = match_song_number_from_filename(entry.name)
                if num and 1 <= num <= 90 and num not in matched:
                    matched[num] = str(entry.resolve())
    except Exception as e:
        print(f"Error scanning folder {folder_path}: {e}")

    return matched


def get_song_cue(number: Any, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Retrieves resolved metadata, start timestamp, clip duration, and file path for a track.
    Handles number as int 1, string '1', or zero-padded '01'.
    """
    try:
        num_int = int(str(number).strip().lstrip("0") or "0")
    except Exception:
        num_int = 1

    if cfg is None:
        cfg = load_audio_config()

    num_str = str(num_int)
    num_pad = f"{num_int:02d}"
    cues = cfg.get("song_cues", {})
    cue_dict = cues.get(num_str) or cues.get(num_pad) or cues.get(str(number)) or {}

    # Title
    song_info = song_bank.get_song(num_int)
    title = cue_dict.get("title") or (song_info.get("title") if song_info else f"Track #{num_int}")

    # Start time & duration
    start_time = parse_time_to_seconds(cue_dict.get("start_time", 0.0))
    duration = parse_time_to_seconds(cue_dict.get("duration", 0.0))

    # File path resolution
    file_path = cue_dict.get("file_path")
    if file_path and Path(file_path).exists():
        resolved_path = str(Path(file_path).resolve())
    else:
        resolved_path = song_bank.find_audio_file(num_int)

    return {
        "title": title,
        "file_path": resolved_path,
        "start_time": max(0.0, start_time),
        "duration": max(0.0, duration)
    }


def import_catalog_file(filepath: str) -> Tuple[int, List[str]]:
    """
    Imports song catalog and start cue metadata from a .csv or .xlsx file.
    Expected columns:
      - Serial / No / Index (1-90)
      - Song Name / Title (optional)
      - Start Time / Cue (e.g., '01:15' or 75)
      - Duration / Stop (optional, seconds)
    Updates audio_config.json and returns (updated_count, error_messages).
    """
    path = Path(filepath)
    ext = path.suffix.lower()
    errors: List[str] = []
    rows: List[Dict[str, Any]] = []

    if ext == ".csv":
        import csv
        for enc in ["utf-8-sig", "utf-8", "cp1252", "latin-1"]:
            try:
                with open(path, mode="r", encoding=enc) as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        rows.append(r)
                break
            except Exception:
                continue
    elif ext in (".xlsx", ".xls"):
        loaded = False
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=True)
            ws = wb.active
            header_row = next(ws.iter_rows(max_row=1, values_only=True), [])
            headers = [str(h).strip() if h is not None else "" for h in header_row]
            for row_vals in ws.iter_rows(min_row=2, values_only=True):
                r_dict = {}
                for h, val in zip(headers, row_vals):
                    if h:
                        r_dict[h] = val
                if any(v is not None for v in r_dict.values()):
                    rows.append(r_dict)
            loaded = True
        except Exception as e_openpyxl:
            try:
                import pandas as pd
                df = pd.read_excel(path)
                rows = df.to_dict(orient="records")
                loaded = True
            except Exception as e_pd:
                errors.append(f"Failed to load Excel workbook: {e_openpyxl}; pandas: {e_pd}")
    else:
        errors.append(f"Unsupported file type: {ext}. Please upload a .csv or .xlsx file.")
        return 0, errors

    if not rows and not errors:
        errors.append("File is empty or contains no readable rows.")
        return 0, errors

    cfg = load_audio_config()
    updated_count = 0

    col_num_keys = ["no", "no.", "number", "index", "id", "serial", "track", "track #", "track no", "song no", "song number"]
    col_title_keys = ["song name", "song", "title", "track name", "name", "song title"]
    col_start_keys = ["start time", "start", "start cue", "cue", "start_time", "start_cue", "from", "timestamp", "start time (mm:ss)"]
    col_dur_keys = ["duration", "length", "duration (sec)", "duration(sec)", "stop", "clip duration", "stop time", "stop_time", "duration (s)"]

    for row in rows:
        num_val = None
        title_val = None
        start_val = None
        dur_val = None

        for k, v in row.items():
            if v is None:
                continue
            clean_k = str(k).strip().lower()
            if num_val is None and clean_k in col_num_keys:
                num_val = v
            elif title_val is None and clean_k in col_title_keys:
                title_val = str(v).strip()
            elif start_val is None and clean_k in col_start_keys:
                start_val = v
            elif dur_val is None and clean_k in col_dur_keys:
                dur_val = v

        if num_val is None and row:
            first_val = list(row.values())[0]
            try:
                iv = int(float(first_val))
                if 1 <= iv <= 90:
                    num_val = iv
            except Exception:
                pass

        if num_val is None:
            continue

        try:
            num = int(float(num_val))
        except Exception:
            continue

        if not (1 <= num <= 90):
            continue

        num_str = str(num)
        if num_str not in cfg["song_cues"]:
            cfg["song_cues"][num_str] = {}

        cue = cfg["song_cues"][num_str]
        if title_val:
            cue["title"] = str(title_val)
        if start_val is not None:
            cue["start_time"] = parse_time_to_seconds(start_val)
        if dur_val is not None:
            cue["duration"] = parse_time_to_seconds(dur_val)

        updated_count += 1

    if updated_count > 0:
        save_audio_config(cfg)

    return updated_count, errors


# ---------------------------------------------------------------------------
# DESIGN SYSTEM: Solid Light & High-Contrast Pastel Accents
# ---------------------------------------------------------------------------
PALETTE = {
    "bg_body": "#F4F7FC",          # Solid Crisp Off-White Canvas
    "bg_card": "#FFFFFF",          # Elevated Pure White Card
    "bg_card_alt": "#F8FAFC",      # Subtle light card
    "border": "#E2E8F4",           # Crisp Structural Border
    "border_light": "#EDF2F7",     # Subtle inner border

    "primary": "#4F46E5",          # Electric / Soft Indigo
    "primary_hover": "#4338CA",
    "primary_light": "#EEF2FF",    # Light Indigo Pill

    "emerald": "#059669",          # Vivid Emerald (Verified / Success)
    "emerald_light": "#ECFDF5",    # Mint Highlight
    "emerald_dark": "#065F46",

    "coral": "#F43F5E",            # Coral Rose (Active Ball / Call)
    "coral_hover": "#E11D48",
    "coral_light": "#FFF1F2",
    "coral_dark": "#9F1239",

    "amber": "#D97706",            # Warm Amber / Gold
    "amber_light": "#FEF3C7",
    "amber_dark": "#78350F",

    "text_main": "#0F172A",        # Dark Slate Heading
    "text_muted": "#64748B",       # Medium Slate Subtext
    "text_dim": "#94A3B8",         # Dim Slate Muted
    "text_white": "#FFFFFF",

    "cell_blank": "#F1F5F9",       # Blank Tambola Slot
    "cell_blank_border": "#CBD5E1"
}


# ---------------------------------------------------------------------------
# SCREEN 1: Live Ball Roller & Master Stage
# ---------------------------------------------------------------------------
class LiveStageScreen(tk.Frame):
    """
    Screen 1: Live Ball Roller & Master Calling Stage
    - Left Panel: 3D Physics Ball Drop Chute on Canvas with shockwave ring,
      bold hero details, Pygame audio deck, session chips, and quick transition.
    - Right Panel: Master 10x9 Calling Matrix with Satyam, Shivam, Sundaram pillars.
    """
    def __init__(self, master, app_controller):
        super().__init__(master, bg=PALETTE["bg_body"])
        self.app = app_controller

        # Calling state
        self.called_numbers: List[int] = []
        self.current_number: Optional[int] = None

        # Chute Animation State (60 FPS)
        self.is_animating = False
        self.ball_x = 75.0
        self.ball_y = -60.0
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.ball_radius = 36.0
        self.target_number: Optional[int] = None
        self.display_number = "--"
        self.bounce_count = 0
        self.shockwave_radius = 0.0
        self.shockwave_alpha = 0.0
        self.scale_pop = 1.0

        # Matrix button lookup {number: tk.Button}
        self.matrix_buttons: Dict[int, tk.Button] = {}

        # Audio controller reference
        self.is_paused = False
        self.auto_switch_var = tk.BooleanVar(value=False)
        self._stop_timer: Optional[str] = None

        self._init_ui()

    def _init_ui(self):
        # 2-Column Split Layout
        left_container = tk.Frame(self, bg=PALETTE["bg_body"], width=460)
        left_container.pack(side="left", fill="y", padx=(20, 10), pady=16)
        left_container.pack_propagate(False)

        right_container = tk.Frame(self, bg=PALETTE["bg_body"])
        right_container.pack(side="right", fill="both", expand=True, padx=(10, 20), pady=16)

        # -------------------------------------------------------------
        # LEFT PANEL: Ball Chute Canvas & Hero Calling Deck
        # -------------------------------------------------------------
        # 1. 3D Physics Ball Drop Chute Canvas
        self.canvas_chute = tk.Canvas(
            left_container, width=440, height=230,
            bg=PALETTE["bg_card_alt"], highlightthickness=1,
            highlightbackground=PALETTE["border"]
        )
        self.canvas_chute.pack(fill="x", pady=(0, 10))
        self._draw_static_chute()

        # 2. Main Call Action Button (Primary CTA)
        self.btn_draw = tk.Button(
            left_container, text="🎲 DRAW & ROLL NEXT TRACK",
            font=("Segoe UI", 12, "bold"),
            bg=PALETTE["primary"], fg=PALETTE["text_white"],
            activebackground=PALETTE["primary_hover"], activeforeground=PALETTE["text_white"],
            relief="flat", cursor="hand2", height=2,
            command=self.draw_next_track
        )
        self.btn_draw.pack(fill="x", pady=(0, 10))

        # 3. Dynamic Hero Track Details Card
        self.card_hero = tk.Frame(left_container, bg=PALETTE["bg_card"], bd=1, relief="solid")
        self.card_hero.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        self.card_hero.pack(fill="x", pady=(0, 10))

        hero_inner = tk.Frame(self.card_hero, bg=PALETTE["bg_card"], padx=14, pady=10)
        hero_inner.pack(fill="x")

        self.lbl_hero_pillar = tk.Label(
            hero_inner, text="READY TO COMMENCE GAME",
            font=("Segoe UI", 10, "bold"), fg=PALETTE["primary"], bg=PALETTE["bg_card"]
        )
        self.lbl_hero_pillar.pack(anchor="w")

        self.lbl_hero_title = tk.Label(
            hero_inner, text="Press 'Draw Next Track' or Spacebar",
            font=("Segoe UI", 14, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"],
            wraplength=400, justify="left"
        )
        self.lbl_hero_title.pack(anchor="w", pady=(2, 2))

        self.lbl_hero_sub = tk.Label(
            hero_inner, text="90 Evergreen Indian Songs • Full Decade Mapping",
            font=("Segoe UI", 10), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"],
            wraplength=400, justify="left"
        )
        self.lbl_hero_sub.pack(anchor="w")

        # 4. Audio Playback Control Deck
        self.card_audio = tk.Frame(left_container, bg=PALETTE["bg_card"], bd=1, relief="solid")
        self.card_audio.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        self.card_audio.pack(fill="x", pady=(0, 10))

        audio_inner = tk.Frame(self.card_audio, bg=PALETTE["bg_card"], padx=14, pady=8)
        audio_inner.pack(fill="x")

        audio_top = tk.Frame(audio_inner, bg=PALETTE["bg_card"])
        audio_top.pack(fill="x", pady=(0, 6))

        self.lbl_audio_status = tk.Label(
            audio_top, text="Audio: Ready",
            font=("Segoe UI", 10, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]
        )
        self.lbl_audio_status.pack(side="left")

        # Control buttons row
        ctrl_row = tk.Frame(audio_inner, bg=PALETTE["bg_card"])
        ctrl_row.pack(fill="x")

        self.btn_replay = tk.Button(
            ctrl_row, text="↺ Replay", font=("Segoe UI", 9, "bold"),
            bg=PALETTE["bg_card_alt"], fg=PALETTE["text_main"], relief="groove",
            cursor="hand2", padx=8, pady=3, command=self.replay_current_song
        )
        self.btn_replay.pack(side="left", padx=(0, 6))

        self.btn_pause = tk.Button(
            ctrl_row, text="⏸ Pause", font=("Segoe UI", 9, "bold"),
            bg=PALETTE["bg_card_alt"], fg=PALETTE["text_main"], relief="groove",
            cursor="hand2", padx=8, pady=3, command=self.toggle_pause
        )
        self.btn_pause.pack(side="left", padx=(0, 6))

        self.btn_stop = tk.Button(
            ctrl_row, text="⏹ Stop", font=("Segoe UI", 9, "bold"),
            bg=PALETTE["bg_card_alt"], fg=PALETTE["coral"], relief="groove",
            cursor="hand2", padx=8, pady=3, command=self.stop_audio
        )
        self.btn_stop.pack(side="left", padx=(0, 12))

        # Volume scale
        tk.Label(ctrl_row, text="Vol:", font=("Segoe UI", 9), bg=PALETTE["bg_card"], fg=PALETTE["text_muted"]).pack(side="left")
        self.scale_vol = tk.Scale(
            ctrl_row, from_=0, to=100, orient="horizontal", length=80,
            showvalue=0, bg=PALETTE["bg_card"], highlightthickness=0,
            command=self._on_volume_change
        )
        self.scale_vol.set(80)
        self.scale_vol.pack(side="left", padx=(4, 0))

        # 5. Session Counter & Last 5 Drawn Chips
        session_box = tk.Frame(left_container, bg=PALETTE["bg_card"], bd=1, relief="solid")
        session_box.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        session_box.pack(fill="x", pady=(0, 10))

        s_inner = tk.Frame(session_box, bg=PALETTE["bg_card"], padx=12, pady=8)
        s_inner.pack(fill="x")

        self.lbl_session_count = tk.Label(
            s_inner, text="Drawn: 0 / 90  •  Remaining: 90",
            font=("Segoe UI", 10, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"]
        )
        self.lbl_session_count.pack(anchor="w", pady=(0, 4))

        self.chips_frame = tk.Frame(s_inner, bg=PALETTE["bg_card"])
        self.chips_frame.pack(fill="x")
        self.chip_labels: List[tk.Label] = []
        for _ in range(5):
            lbl = tk.Label(
                self.chips_frame, text="—", font=("Segoe UI", 9, "bold"),
                bg=PALETTE["bg_card_alt"], fg=PALETTE["text_dim"],
                relief="solid", bd=1, padx=8, pady=2
            )
            lbl.pack(side="left", padx=(0, 6))
            self.chip_labels.append(lbl)

        # 6. Quick Action to Screen 2 & Auto-Switch Checkbox
        btn_sphere = tk.Button(
            left_container, text="🔮 Open Audio Dot-Sphere →",
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["primary_light"], fg=PALETTE["primary"],
            activebackground=PALETTE["primary"], activeforeground=PALETTE["text_white"],
            relief="flat", cursor="hand2", pady=6,
            command=lambda: self.app.switch_tab(1)
        )
        btn_sphere.pack(fill="x", pady=(0, 6))

        chk_auto = tk.Checkbutton(
            left_container, text="Auto-switch to sphere visualizer 1.5s after call",
            variable=self.auto_switch_var, font=("Segoe UI", 9),
            bg=PALETTE["bg_body"], fg=PALETTE["text_muted"], activebackground=PALETTE["bg_body"]
        )
        chk_auto.pack(anchor="w")

        # -------------------------------------------------------------
        # RIGHT PANEL: Master 10x9 Calling Matrix
        # -------------------------------------------------------------
        card_matrix = tk.Frame(right_container, bg=PALETTE["bg_card"], bd=1, relief="solid")
        card_matrix.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        card_matrix.pack(fill="both", expand=True)

        m_header = tk.Frame(card_matrix, bg=PALETTE["bg_card"], padx=18, pady=12)
        m_header.pack(fill="x")

        lbl_m_title = tk.Label(
            m_header, text="MASTER CALLING BOARD (1–90)",
            font=("Segoe UI", 12, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"]
        )
        lbl_m_title.pack(side="left")

        # Legend Pills
        legend_frame = tk.Frame(m_header, bg=PALETTE["bg_card"])
        legend_frame.pack(side="right")

        tk.Label(
            legend_frame, text="Satyam (1–29)", font=("Segoe UI", 9, "bold"),
            bg=PALETTE["primary_light"], fg=PALETTE["primary"], padx=8, pady=2
        ).pack(side="left", padx=4)

        tk.Label(
            legend_frame, text="Shivam (30–59)", font=("Segoe UI", 9, "bold"),
            bg=PALETTE["amber_light"], fg=PALETTE["amber_dark"], padx=8, pady=2
        ).pack(side="left", padx=4)

        tk.Label(
            legend_frame, text="Sundaram (60–90)", font=("Segoe UI", 9, "bold"),
            bg=PALETTE["emerald_light"], fg=PALETTE["emerald_dark"], padx=8, pady=2
        ).pack(side="left", padx=4)

        # Matrix Grid Scrollable Frame
        grid_container = tk.Frame(card_matrix, bg=PALETTE["bg_card"], padx=14, pady=8)
        grid_container.pack(fill="both", expand=True)

        col_ranges = song_bank.COLUMN_RANGES
        col_headers = ["1–9", "10–19", "20–29", "30–39", "40–49", "50–59", "60–69", "70–79", "80–90"]

        for c_idx, title in enumerate(col_headers):
            lbl_ch = tk.Label(
                grid_container, text=title, font=("Segoe UI", 9, "bold"),
                bg=PALETTE["bg_card_alt"], fg=PALETTE["text_muted"],
                relief="flat", padx=4, pady=4
            )
            lbl_ch.grid(row=0, column=c_idx, sticky="nsew", padx=3, pady=(0, 4))

        for c_idx, (start_n, end_n) in enumerate(col_ranges):
            grid_container.grid_columnconfigure(c_idx, weight=1)
            row_idx = 1
            for n in range(start_n, end_n + 1):
                btn = tk.Button(
                    grid_container, text=f"{n:02d}",
                    font=("Segoe UI", 10, "bold"),
                    bg=PALETTE["bg_card_alt"], fg=PALETTE["text_dim"],
                    relief="solid", bd=1, cursor="hand2",
                    command=lambda num=n: self.manual_call_number(num)
                )
                btn.grid(row=row_idx, column=c_idx, sticky="nsew", padx=3, pady=3)
                self.matrix_buttons[n] = btn
                row_idx += 1

        for r in range(12):
            grid_container.grid_rowconfigure(r, weight=1)

    # -------------------------------------------------------------
    # Chute Physics Animation Loop (60 FPS via Canvas after(16))
    # -------------------------------------------------------------
    def _draw_static_chute(self):
        """Draw acrylic chute structure and center cradle on Canvas."""
        self.canvas_chute.delete("all")
        w, h = 440, 230
        ground_y = 155

        # Curved acrylic chute guide rails (from top-left down to runway)
        self.canvas_chute.create_line(45, 10, 85, 10, fill=PALETTE["border"], width=3)
        self.canvas_chute.create_line(45, 10, 45, ground_y - 30, fill=PALETTE["border"], width=2)
        self.canvas_chute.create_line(85, 10, 85, ground_y - 30, fill=PALETTE["border"], width=2)
        self.canvas_chute.create_arc(45, ground_y - 60, 125, ground_y + 10, start=180, extent=90, style="arc", outline=PALETTE["border"], width=3)

        # Horizontal rolling runway
        self.canvas_chute.create_line(85, ground_y + 5, w - 40, ground_y + 5, fill=PALETTE["border"], width=3)

        # Center Hero Cradle Socket
        cx = 220
        self.canvas_chute.create_rectangle(cx - 50, ground_y, cx + 50, ground_y + 20, fill=PALETTE["bg_card"], outline=PALETTE["border"], width=2)
        self.canvas_chute.create_oval(cx - 30, ground_y - 4, cx + 30, ground_y + 6, fill=PALETTE["border_light"], outline=PALETTE["border"])

        # Initial resting ball if no draw has occurred
        self._render_lotto_ball(cx, ground_y - self.ball_radius, self.display_number, is_active=(self.current_number is not None))

    def _render_lotto_ball(self, x: float, y: float, label: str, is_active: bool = False):
        """Renders 3D-shaded lottery ball with specular highlight, inner disc and text."""
        r = self.ball_radius * self.scale_pop
        ground_y = 155

        # Ground Drop Shadow
        shadow_w = r * 1.5
        shadow_h = 10.0
        self.canvas_chute.create_oval(x - shadow_w / 2, ground_y - 2, x + shadow_w / 2, ground_y + shadow_h, fill="#E2E8F0", outline="")

        # Shockwave Ring (when landing)
        if self.shockwave_radius > 0:
            sw_r = self.shockwave_radius
            self.canvas_chute.create_oval(
                x - sw_r, y - sw_r, x + sw_r, y + sw_r,
                outline=PALETTE["coral"], width=2
            )

        # Outer Ball Sphere (Coral Rose #F43F5E or Neutral)
        base_color = PALETTE["coral"] if is_active else PALETTE["bg_card"]
        outline_col = PALETTE["coral_dark"] if is_active else PALETTE["border"]
        self.canvas_chute.create_oval(x - r, y - r, x + r, y + r, fill=base_color, outline=outline_col, width=2)

        # 3D Depth Crescent Arc
        if is_active:
            self.canvas_chute.create_arc(x - r, y - r, x + r, y + r, start=210, extent=120, fill=PALETTE["coral_hover"], outline="")

        # Inner White Number Disc
        disc_r = r * 0.62
        self.canvas_chute.create_oval(x - disc_r, y - disc_r, x + disc_r, y + disc_r, fill="#FFFFFF", outline=outline_col, width=1)

        # Specular Highlight Gleam (top-left)
        gl_w = r * 0.4
        gl_h = r * 0.22
        self.canvas_chute.create_oval(x - r * 0.45, y - r * 0.65, x - r * 0.45 + gl_w, y - r * 0.65 + gl_h, fill="#FFE4E6", outline="")

        # Number Label
        text_col = PALETTE["coral_dark"] if is_active else PALETTE["text_dim"]
        self.canvas_chute.create_text(
            x, y, text=label,
            font=("Segoe UI", int(14 * self.scale_pop), "bold"),
            fill=text_col
        )

    def draw_next_track(self):
        """Host clicks 'Draw Next Track' or presses Spacebar."""
        if self.is_animating:
            return

        available = [n for n in range(1, 91) if n not in self.called_numbers]
        if not available:
            messagebox.showinfo("Game Complete", "All 90 numbers have been called!")
            return

        self.target_number = random.choice(available)
        self.current_number = self.target_number

        # Start 60-FPS physics animation: spawn at top chute
        self.is_animating = True
        self.ball_x = 65.0
        self.ball_y = -60.0
        self.vel_x = 1.0
        self.vel_y = 3.0
        self.bounce_count = 0
        self.shockwave_radius = 0.0
        self.scale_pop = 1.0

        self._step_physics()

    def _step_physics(self):
        """Simulate gravity ($y = y_0 + 0.5 g t^2$), elastic bounce, and rolling spin."""
        ground_y = 155 - self.ball_radius
        cradle_x = 220.0

        # Phase 1: Dropping down chute
        if self.bounce_count < 2:
            self.vel_y += 1.15  # Gravity acceleration
            self.ball_y += self.vel_y
            self.ball_x += self.vel_x

            # Rapid rotational spin: cycle numbers while rolling
            self.display_number = f"{random.randint(1, 90):02d}"

            # Hit ground / bounce plate
            if self.ball_y >= ground_y:
                self.ball_y = ground_y
                self.vel_y = -self.vel_y * 0.45  # Elastic damping
                self.vel_x = 7.5  # Forward roll impetus
                self.bounce_count += 1
                self.shockwave_radius = self.ball_radius * 1.1

        # Phase 2: Horizontal Rolling into Center Cradle
        else:
            self.ball_x += self.vel_x
            self.vel_x *= 0.955  # Rolling friction deceleration
            self.display_number = f"{random.randint(1, 90):02d}"

            # Expand shockwave ring
            if self.shockwave_radius > 0:
                self.shockwave_radius += 3.5
                if self.shockwave_radius > 90.0:
                    self.shockwave_radius = 0.0

            # Arrived at center cradle
            if self.ball_x >= cradle_x or abs(self.vel_x) < 0.6:
                self.ball_x = cradle_x
                self.vel_x = 0.0
                self.is_animating = False
                self.display_number = f"#{self.target_number:02d}"
                self.scale_pop = 1.25  # Pop reveal

                # Finalize call
                self._on_ball_landed(self.target_number)
                self._draw_static_chute()
                self._animate_scale_settle()
                return

        # Redraw frame
        self._draw_static_chute()
        self._render_lotto_ball(self.ball_x, self.ball_y, self.display_number, is_active=True)
        self.after(16, self._step_physics)

    def _animate_scale_settle(self):
        """Spring back scale pop from 1.25 to 1.0."""
        if self.scale_pop > 1.0:
            self.scale_pop -= 0.03
            self._draw_static_chute()
            self.after(16, self._animate_scale_settle)
        else:
            self.scale_pop = 1.0

    def _on_ball_landed(self, number: int):
        """Called once the ball settles in the center cradle."""
        if number not in self.called_numbers:
            self.called_numbers.append(number)

        self._update_hero_details(number)
        self._update_matrix_board(number)
        self._update_session_chips()
        self.play_song(number)

        # Sync with global app & other screens
        self.app.sync_number_called(number)

        # Auto-switch to visualizer if enabled
        if self.auto_switch_var.get():
            self.after(1500, lambda: self.app.switch_tab(1))

    def manual_call_number(self, number: int):
        """Allow host to click uncalled matrix cell directly with confirmation."""
        if number in self.called_numbers:
            self.play_song(number)
            self._update_hero_details(number)
            return

        if messagebox.askyesno("Confirm Manual Call", f"Call Track #{number:02d} ({song_bank.get_song_title(number)})?"):
            self.target_number = number
            self.current_number = number
            self.is_animating = False
            self.display_number = f"#{number:02d}"
            self._on_ball_landed(number)

    def _update_hero_details(self, number: int):
        song = song_bank.get_song(number)
        title = song.get("title", f"Track #{number}") if song else f"Track #{number}"
        artist = song.get("artist", "Bollywood Evergreen") if song else ""
        year = song.get("year", "") if song else ""

        pillar = "Satyam" if number <= 29 else ("Shivam" if number <= 59 else "Sundaram")
        col_idx = song.get("column", 0) + 1 if song else 1

        self.lbl_hero_pillar.config(text=f"✦ NOW CALLING: {pillar.upper()} • COLUMN {col_idx}")
        self.lbl_hero_title.config(text=f"#{number:02d} • {title}")
        sub = f"Album: {artist}"
        if year:
            sub += f" ({year})"
        self.lbl_hero_sub.config(text=sub)

    def _update_matrix_board(self, active_number: int):
        for n, btn in self.matrix_buttons.items():
            if n == active_number:
                # Active Call: Coral Rose #FFF1F2 bg, #F43F5E text
                btn.config(bg=PALETTE["coral_light"], fg=PALETTE["coral"], relief="solid", bd=2)
            elif n in self.called_numbers:
                # Previously Called: Mint #ECFDF5 bg, #059669 text
                btn.config(bg=PALETTE["emerald_light"], fg=PALETTE["emerald"], relief="solid", bd=1)
            else:
                # Uncalled: #F8FAFC bg, #94A3B8 text
                btn.config(bg=PALETTE["bg_card_alt"], fg=PALETTE["text_dim"], relief="solid", bd=1)

    def _update_session_chips(self):
        drawn = len(self.called_numbers)
        rem = 90 - drawn
        self.lbl_session_count.config(text=f"Drawn: {drawn} / 90  •  Remaining: {rem}")

        last_five = self.called_numbers[-5:] if len(self.called_numbers) >= 5 else self.called_numbers
        for i in range(5):
            idx = len(last_five) - 1 - i
            if idx >= 0:
                n = last_five[idx]
                self.chip_labels[i].config(
                    text=f"#{n:02d}",
                    bg=PALETTE["coral_light"] if i == 0 else PALETTE["emerald_light"],
                    fg=PALETTE["coral"] if i == 0 else PALETTE["emerald"]
                )
            else:
                self.chip_labels[i].config(text="—", bg=PALETTE["bg_card_alt"], fg=PALETTE["text_dim"])

    def play_song(self, number: int):
        if not HAS_AUDIO:
            self.lbl_audio_status.config(text="Audio disabled (mixer unavailable)")
            return

        # Cancel any active duration timer
        if self._stop_timer:
            try:
                self.after_cancel(self._stop_timer)
            except Exception:
                pass
            self._stop_timer = None

        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            except Exception:
                pass

        cue = get_song_cue(number)
        audio_file = cue.get("file_path")
        if not audio_file or not os.path.exists(audio_file):
            audio_file = song_bank.find_audio_file(number)

        start_sec = cue.get("start_time", 0.0)
        duration = cue.get("duration", 0.0)

        if audio_file and os.path.exists(audio_file):
            try:
                pygame.mixer.music.load(audio_file)
                try:
                    pygame.mixer.music.play(start=start_sec)
                except Exception:
                    pygame.mixer.music.play()

                cue_txt = f" (from {format_seconds_to_time(start_sec)})" if start_sec > 0 else ""
                dur_txt = f" • {int(duration)}s clip" if duration > 0 else ""
                self.lbl_audio_status.config(text=f"Playing Track #{number:02d}{cue_txt}{dur_txt}")
                self.btn_pause.config(text="⏸ Pause")
                self.is_paused = False

                # Schedule automatic clip stop if duration is set
                if duration > 0.0:
                    self._stop_timer = self.after(int(duration * 1000), self.stop_audio)
            except Exception as e:
                self.lbl_audio_status.config(text=f"Playback error: {e}")
        else:
            self.lbl_audio_status.config(text=f"Audio for #{number:02d} missing (Silent)")

    def replay_current_song(self):
        if self.current_number:
            self.play_song(self.current_number)

    def toggle_pause(self):
        if not HAS_AUDIO:
            return
        if pygame.mixer.music.get_busy() and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.btn_pause.config(text="▶ Resume")
            self.lbl_audio_status.config(text="Paused")
        elif self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.btn_pause.config(text="⏸ Pause")
            self.lbl_audio_status.config(text=f"Playing Track #{self.current_number:02d}" if self.current_number else "Playing")

    def stop_audio(self):
        if self._stop_timer:
            try:
                self.after_cancel(self._stop_timer)
            except Exception:
                pass
            self._stop_timer = None

        if HAS_AUDIO:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.lbl_audio_status.config(text="Stopped")
        self.btn_pause.config(text="▶ Play")
        self.is_paused = False

    def _on_volume_change(self, val):
        if HAS_AUDIO:
            try:
                pygame.mixer.music.set_volume(int(val) / 100.0)
            except Exception:
                pass

    def reset_game(self):
        """Prompt confirmation before clearing board."""
        if messagebox.askyesno("Reset Game Session", "Are you sure you want to reset the current session?\nAll drawn tracks will be cleared."):
            self.called_numbers.clear()
            self.current_number = None
            self.stop_audio()
            self.display_number = "--"
            self._draw_static_chute()
            self.lbl_hero_pillar.config(text="READY TO COMMENCE GAME")
            self.lbl_hero_title.config(text="Press 'Draw Next Track' or Spacebar")
            self.lbl_hero_sub.config(text="90 Evergreen Indian Songs • Full Decade Mapping")
            self.lbl_audio_status.config(text="Audio: Ready")
            for btn in self.matrix_buttons.values():
                btn.config(bg=PALETTE["bg_card_alt"], fg=PALETTE["text_dim"])
            self._update_session_chips()
            self.app.sync_reset()


# ---------------------------------------------------------------------------
# SCREEN 2: 3D Audio Dot-Sphere Visualizer (Fibonacci Lattice, 60 FPS)
# ---------------------------------------------------------------------------
class DotSphereScreen(tk.Frame):
    """
    Screen 2: 3D Audio "Sphere of Dots" Visualizer
    - Renders 280 points on a Fibonacci spherical lattice using Canvas.
    - Continuous perspective rotation around X & Y axes.
    - Audio-reactive harmonic pulsation synced to pygame audio.
    """
    def __init__(self, master, app_controller):
        super().__init__(master, bg=PALETTE["bg_body"])
        self.app = app_controller

        # 3D Fibonacci Points
        self.num_points = 280
        self.points: List[Tuple[float, float, float]] = []
        self._build_fibonacci_sphere()

        # Dynamic Sphere State
        self.base_radius = 160.0
        self.yaw = 0.0
        self.pitch = 0.0
        self.yaw_speed = 0.015
        self.pitch_speed = 0.008
        self.pulse_phase = 0.0
        self.is_running = False

        self._init_ui()

    def _build_fibonacci_sphere(self):
        """Distribute 280 points evenly over a unit sphere."""
        self.points.clear()
        phi_golden = math.pi * (3.0 - math.sqrt(5.0))  # ~2.39996 rad
        for i in range(self.num_points):
            y = 1.0 - (float(i) / float(self.num_points - 1)) * 2.0  # +1 to -1
            r = math.sqrt(max(0.0, 1.0 - y * y))
            theta = phi_golden * float(i)
            x = r * math.cos(theta)
            z = r * math.sin(theta)
            self.points.append((x, y, z))

    def _init_ui(self):
        # Header Bar
        header = tk.Frame(self, bg=PALETTE["bg_card"], bd=1, relief="solid")
        header.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        header.pack(fill="x", padx=20, pady=(16, 10))

        h_inner = tk.Frame(header, bg=PALETTE["bg_card"], padx=16, pady=10)
        h_inner.pack(fill="x")

        tk.Label(
            h_inner, text="🔮 3D AUDIO DOT-SPHERE VISUALIZER • LIVE SOUND RESONATOR",
            font=("Segoe UI", 12, "bold"), fg=PALETTE["primary"], bg=PALETTE["bg_card"]
        ).pack(side="left")

        btn_back = tk.Button(
            h_inner, text="← Return to Live Stage",
            font=("Segoe UI", 10, "bold"), bg=PALETTE["bg_card_alt"], fg=PALETTE["text_main"],
            relief="groove", cursor="hand2", padx=12, pady=4,
            command=lambda: self.app.switch_tab(0)
        )
        btn_back.pack(side="right")

        # Main 3D Canvas
        self.canvas_sphere = tk.Canvas(
            self, bg=PALETTE["bg_card"], highlightthickness=1,
            highlightbackground=PALETTE["border"]
        )
        self.canvas_sphere.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Bottom Controls HUD
        hud = tk.Frame(self, bg=PALETTE["bg_card"], bd=1, relief="solid")
        hud.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        hud.pack(fill="x", padx=20, pady=(0, 16))

        hud_inner = tk.Frame(hud, bg=PALETTE["bg_card"], padx=16, pady=8)
        hud_inner.pack(fill="x")

        self.lbl_now_playing = tk.Label(
            hud_inner, text="Now Playing: Ready for Calling",
            font=("Segoe UI", 11, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"]
        )
        self.lbl_now_playing.pack(side="left")

        # Speed slider
        tk.Label(hud_inner, text="Rotation Speed:", font=("Segoe UI", 9), bg=PALETTE["bg_card"], fg=PALETTE["text_muted"]).pack(side="left", padx=(24, 4))
        self.scale_speed = tk.Scale(
            hud_inner, from_=5, to=30, orient="horizontal", length=90,
            showvalue=0, bg=PALETTE["bg_card"], highlightthickness=0,
            command=lambda v: setattr(self, "yaw_speed", float(v) * 0.0015)
        )
        self.scale_speed.set(10)
        self.scale_speed.pack(side="left")

        # Size slider
        tk.Label(hud_inner, text="Sphere Size:", font=("Segoe UI", 9), bg=PALETTE["bg_card"], fg=PALETTE["text_muted"]).pack(side="left", padx=(20, 4))
        self.scale_radius = tk.Scale(
            hud_inner, from_=100, to=240, orient="horizontal", length=90,
            showvalue=0, bg=PALETTE["bg_card"], highlightthickness=0,
            command=lambda v: setattr(self, "base_radius", float(v))
        )
        self.scale_radius.set(160)
        self.scale_radius.pack(side="left")

    def start_loop(self):
        """Start 60 FPS animation loop when screen is active."""
        if not self.is_running:
            self.is_running = True
            self._render_frame()

    def stop_loop(self):
        self.is_running = False

    def sync_track_info(self, number: int):
        cue = get_song_cue(number)
        title = cue.get("title") or song_bank.get_song_title(number)
        start_sec = cue.get("start_time", 0.0)
        duration = cue.get("duration", 0.0)
        cue_info = ""
        if start_sec > 0:
            cue_info += f" • Start: {format_seconds_to_time(start_sec)}"
        if duration > 0:
            cue_info += f" • {int(duration)}s clip"
        self.lbl_now_playing.config(text=f"Now Playing: #{number:02d} • {title}{cue_info}")

    def _render_frame(self):
        if not self.is_running:
            return

        w = self.canvas_sphere.winfo_width()
        h = self.canvas_sphere.winfo_height()
        if w < 10 or h < 10:
            self.after(30, self._render_frame)
            return

        cx = w / 2.0
        cy = h / 2.0
        fov = 340.0
        cam_dist = 380.0

        # Update rotation angles
        self.yaw = (self.yaw + self.yaw_speed) % (math.pi * 2)
        self.pitch = (self.pitch + self.pitch_speed) % (math.pi * 2)
        self.pulse_phase += 0.06

        # Audio-Reactive Dynamic Radius Pulse
        is_busy = False
        if HAS_AUDIO:
            try:
                is_busy = pygame.mixer.music.get_busy()
            except Exception:
                is_busy = False

        if is_busy:
            # Multi-frequency harmonic pulse when music is active
            pulse = (
                0.16 * math.sin(self.pulse_phase * 4.0) +
                0.08 * math.sin(self.pulse_phase * 9.5) +
                0.04 * math.sin(self.pulse_phase * 15.0)
            )
            dyn_radius = self.base_radius * (1.0 + pulse)
        else:
            # Gentle ambient breathing when idle
            dyn_radius = self.base_radius * (1.0 + 0.04 * math.sin(self.pulse_phase * 1.5))

        cos_y, sin_y = math.cos(self.yaw), math.sin(self.yaw)
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)

        projected = []
        for bx, by, bz in self.points:
            # Yaw (Y-axis)
            x1 = bx * cos_y + bz * sin_y
            y1 = by
            z1 = -bx * sin_y + bz * cos_y

            # Pitch (X-axis)
            x2 = x1
            y2 = y1 * cos_p - z1 * sin_p
            z2 = y1 * sin_p + z1 * cos_p

            # Perspective projection
            world_z = z2 * dyn_radius
            scale = fov / (cam_dist + world_z)
            sx = cx + (x2 * dyn_radius) * scale
            sy = cy + (y2 * dyn_radius) * scale

            projected.append((z2, sx, sy))

        # Sort back-to-front
        projected.sort(key=lambda p: p[0])

        self.canvas_sphere.delete("all")

        # Draw connecting web lines between nearby front-facing dots
        front_dots = [p for p in projected if p[0] > 0.4]
        for i in range(0, len(front_dots), 3):
            z_a, ax, ay = front_dots[i]
            for j in range(i + 1, min(i + 4, len(front_dots))):
                z_b, bx, by = front_dots[j]
                dist_sq = (ax - bx) ** 2 + (ay - by) ** 2
                if dist_sq < 1400.0:
                    self.canvas_sphere.create_line(ax, ay, bx, by, fill="#EEF2FF", width=1)

        # Render dots with depth shading
        for z_norm, sx, sy in projected:
            t = (z_norm + 1.0) / 2.0  # 0.0 (back) to 1.0 (front)
            dot_r = 1.4 + t * 3.4
            color = PALETTE["primary"] if t > 0.4 else PALETTE["text_dim"]

            self.canvas_sphere.create_oval(
                sx - dot_r, sy - dot_r, sx + dot_r, sy + dot_r,
                fill=color, outline=""
            )

        self.after(16, self._render_frame)


# ---------------------------------------------------------------------------
# SCREEN 3: Mechanical Slot Lucky Draw
# ---------------------------------------------------------------------------
class LuckyDrawScreen(tk.Frame):
    """
    Screen 3: Mechanical Slot Lucky Draw (Tie-Breaker & Raffle Module)
    - Dual-drum mechanical slot roller cycling digits with decelerating frame intervals.
    - Configurable multi-winner selection (1 to 10 winners).
    - Session audit history table with ttk.Treeview.
    """
    def __init__(self, master, app_controller):
        super().__init__(master, bg=PALETTE["bg_body"])
        self.app = app_controller

        # Data references
        self.called_numbers_ref: List[int] = []
        self.registered_tickets_ref: List[Dict[str, Any]] = []

        # Slot drum animation state
        self.is_spinning = False
        self.spin_interval = 30
        self.drum1_target = 0
        self.drum2_target = 0
        self.drum1_locked = False
        self.drum2_locked = False
        self.current_drum1 = 0
        self.current_drum2 = 0
        self.pending_winners: List[Dict[str, Any]] = []

        self._init_ui()

    def _init_ui(self):
        # Header Card
        header = tk.Frame(self, bg=PALETTE["bg_card"], bd=1, relief="solid")
        header.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        header.pack(fill="x", padx=20, pady=(16, 12))

        h_inner = tk.Frame(header, bg=PALETTE["bg_card"], padx=16, pady=10)
        h_inner.pack(fill="x")

        tk.Label(
            h_inner, text="🎰 MECHANICAL SLOT LUCKY DRAW & TIE-BREAKER",
            font=("Segoe UI", 12, "bold"), fg=PALETTE["primary"], bg=PALETTE["bg_card"]
        ).pack(side="left")

        tk.Label(
            h_inner, text="Provably Fair Random Tie-Breakers & Digit Drum Raffle",
            font=("Segoe UI", 10), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]
        ).pack(side="right")

        # Main Split Content
        split_frame = tk.Frame(self, bg=PALETTE["bg_body"])
        split_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        # Left Config Panel (340px)
        cfg_panel = tk.Frame(split_frame, bg=PALETTE["bg_card"], bd=1, relief="solid", width=340)
        cfg_panel.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        cfg_panel.pack(side="left", fill="y", padx=(0, 10))
        cfg_panel.pack_propagate(False)

        cfg_inner = tk.Frame(cfg_panel, bg=PALETTE["bg_card"], padx=14, pady=14)
        cfg_inner.pack(fill="both", expand=True)

        tk.Label(cfg_inner, text="1. Draw Parameters", font=("Segoe UI", 11, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"]).pack(anchor="w", pady=(0, 8))

        # Prize category
        tk.Label(cfg_inner, text="Prize / Claim Category:", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(anchor="w")
        self.combo_prize = ttk.Combobox(cfg_inner, values=[
            "Early 5 Tie-Breaker", "Top Line Tie-Breaker", "Middle Line Tie-Breaker",
            "Bottom Line Tie-Breaker", "Four Corners Tie-Breaker", "Full House Tie-Breaker",
            "Lucky Participant Raffle", "Bumper Jackpot Draw", "Consolation Prize"
        ], font=("Segoe UI", 10))
        self.combo_prize.set("Early 5 Tie-Breaker")
        self.combo_prize.pack(fill="x", pady=(2, 10))

        # Winner Count Spinbox
        tk.Label(cfg_inner, text="Simultaneous Winners (1–10):", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(anchor="w")
        self.spin_count = ttk.Spinbox(cfg_inner, from_=1, to=10, font=("Segoe UI", 10), width=6)
        self.spin_count.set(1)
        self.spin_count.pack(anchor="w", pady=(2, 10))

        # Pool Selection
        tk.Label(cfg_inner, text="Selection Pool:", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(anchor="w")
        self.pool_var = tk.StringVar(value="called")
        tk.Radiobutton(cfg_inner, text="Already Called Numbers (Screen 1)", variable=self.pool_var, value="called", font=("Segoe UI", 9), bg=PALETTE["bg_card"]).pack(anchor="w")
        tk.Radiobutton(cfg_inner, text="Registered Ticket IDs (Screen 4)", variable=self.pool_var, value="tickets", font=("Segoe UI", 9), bg=PALETTE["bg_card"]).pack(anchor="w")

        self.btn_spin = tk.Button(
            cfg_inner, text="🎰 SPIN LUCKY DRUM",
            font=("Segoe UI", 12, "bold"), bg=PALETTE["primary"], fg=PALETTE["text_white"],
            activebackground=PALETTE["primary_hover"], relief="flat", cursor="hand2", height=2,
            command=self.start_draw
        )
        self.btn_spin.pack(fill="x", side="bottom")

        # Right Slot Stage Panel
        slot_panel = tk.Frame(split_frame, bg=PALETTE["bg_card"], bd=1, relief="solid")
        slot_panel.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        slot_panel.pack(side="right", fill="both", expand=True)

        slot_inner = tk.Frame(slot_panel, bg=PALETTE["bg_card"], padx=18, pady=14)
        slot_inner.pack(fill="both", expand=True)

        # Dual Drum Canvas
        self.canvas_drums = tk.Canvas(
            slot_inner, width=400, height=140,
            bg=PALETTE["bg_card_alt"], highlightthickness=1,
            highlightbackground=PALETTE["border"]
        )
        self.canvas_drums.pack(fill="x", pady=(0, 10))
        self._draw_drums(0, 0)

        # Winner Cards Display Area
        tk.Label(slot_inner, text="🏆 Drawn Winner(s):", font=("Segoe UI", 11, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"]).pack(anchor="w")
        self.frame_winners = tk.Frame(slot_inner, bg=PALETTE["bg_card"])
        self.frame_winners.pack(fill="both", expand=True, pady=6)

        # Bottom Audit History Table
        log_panel = tk.Frame(self, bg=PALETTE["bg_card"], bd=1, relief="solid", height=190)
        log_panel.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        log_panel.pack(fill="x", padx=20, pady=(0, 16))
        log_panel.pack_propagate(False)

        log_inner = tk.Frame(log_panel, bg=PALETTE["bg_card"], padx=14, pady=8)
        log_inner.pack(fill="both", expand=True)

        log_top = tk.Frame(log_inner, bg=PALETTE["bg_card"])
        log_top.pack(fill="x", pady=(0, 6))

        tk.Label(log_top, text="📋 Session Raffle Audit Log", font=("Segoe UI", 10, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"]).pack(side="left")

        tk.Button(log_top, text="Copy Log", font=("Segoe UI", 8), bg=PALETTE["bg_card_alt"], relief="groove", cursor="hand2", command=self._copy_log).pack(side="right", padx=(4, 0))
        tk.Button(log_top, text="Clear Log", font=("Segoe UI", 8), bg=PALETTE["bg_card_alt"], fg=PALETTE["coral"], relief="groove", cursor="hand2", command=self._clear_log).pack(side="right")

        # Treeview for Audit History
        cols = ("Time", "Category", "Pool", "Winner ID", "Details")
        self.tree_log = ttk.Treeview(log_inner, columns=cols, show="headings", height=5)
        for c in cols:
            self.tree_log.heading(c, text=c)
        self.tree_log.column("Time", width=80)
        self.tree_log.column("Category", width=160)
        self.tree_log.column("Pool", width=130)
        self.tree_log.column("Winner ID", width=90)
        self.tree_log.column("Details", width=300)
        self.tree_log.pack(fill="both", expand=True)

    def _draw_drums(self, d1: int, d2: int):
        self.canvas_drums.delete("all")
        w, h = 400, 140

        # Outer Chrome Frame
        self.canvas_drums.create_rectangle(15, 12, w - 15, h - 12, fill="#F1F5F9", outline=PALETTE["border"], width=2)

        # Drum 1 (Tens)
        self.canvas_drums.create_rectangle(70, 24, 180, h - 24, fill="#FFFFFF", outline=PALETTE["border"], width=2)
        self.canvas_drums.create_text(125, h / 2, text=str(d1), font=("Segoe UI", 48, "bold"), fill=PALETTE["primary"])

        # Drum 2 (Units)
        self.canvas_drums.create_rectangle(220, 24, 330, h - 24, fill="#FFFFFF", outline=PALETTE["border"], width=2)
        self.canvas_drums.create_text(275, h / 2, text=str(d2), font=("Segoe UI", 48, "bold"), fill=PALETTE["primary"])

        # Center reticle line
        self.canvas_drums.create_line(60, h / 2, 340, h / 2, fill=PALETTE["amber"], dash=(3, 3), width=1)

    def start_draw(self):
        if self.is_spinning:
            return

        pool = self.pool_var.get()
        candidates: List[Dict[str, Any]] = []

        if pool == "called":
            if not self.called_numbers_ref:
                messagebox.showwarning("Empty Pool", "No numbers have been called yet in Screen 1!")
                return
            for n in self.called_numbers_ref:
                title = song_bank.get_song_title(n)
                candidates.append({"id": n, "label": f"#{n:02d}", "details": title, "source": "Called Songs"})
        else:
            if not self.registered_tickets_ref:
                messagebox.showwarning("No Tickets", "Load a batch in Screen 4 first!")
                return
            for t in self.registered_tickets_ref:
                tid = t.get("ticket_id", "001")
                num = int(str(tid).lstrip("#")) if str(tid).isdigit() else 1
                candidates.append({"id": num, "label": f"Ticket #{tid}", "details": "Participant", "source": "Ticket Registry"})

        k = min(int(self.spin_count.get()), len(candidates))
        drawn = random.sample(candidates, k)
        self.pending_winners = drawn

        first = drawn[0]["id"]
        self.drum1_target = (first // 10) % 10
        self.drum2_target = first % 10

        self.is_spinning = True
        self.spin_interval = 30
        self.drum1_locked = False
        self.drum2_locked = False

        self._step_drum_spin()

    def _step_drum_spin(self):
        """Rapidly cycles digits with decelerating frame intervals (30ms down to 140ms)."""
        if not self.drum1_locked:
            self.current_drum1 = random.randint(0, 9)
        if not self.drum2_locked:
            self.current_drum2 = random.randint(0, 9)

        self._draw_drums(self.current_drum1, self.current_drum2)

        # Decelerate interval
        self.spin_interval += 5

        # Sequential locking
        if self.spin_interval >= 85 and not self.drum1_locked:
            self.drum1_locked = True
            self.current_drum1 = self.drum1_target

        if self.spin_interval >= 135 and not self.drum2_locked:
            self.drum2_locked = True
            self.current_drum2 = self.drum2_target
            self.is_spinning = False
            self._finalize_draw()
            return

        self.after(self.spin_interval, self._step_drum_spin)

    def _finalize_draw(self):
        self._draw_drums(self.drum1_target, self.drum2_target)

        # Clear existing winner cards
        for w in self.frame_winners.winfo_children():
            w.destroy()

        cat = self.combo_prize.get()
        now_str = datetime.now().strftime("%H:%M:%S")

        for rank, w in enumerate(self.pending_winners, 1):
            c = tk.Frame(self.frame_winners, bg=PALETTE["emerald_light"], bd=1, relief="solid")
            c.configure(highlightbackground=PALETTE["emerald"], highlightthickness=1)
            c.pack(fill="x", pady=2)

            tk.Label(c, text=f"#{rank} Winner: {w['label']}", font=("Segoe UI", 11, "bold"), fg=PALETTE["emerald_dark"], bg=PALETTE["emerald_light"]).pack(side="left", padx=10, pady=4)
            tk.Label(c, text=w["details"], font=("Segoe UI", 10), fg=PALETTE["text_main"], bg=PALETTE["emerald_light"]).pack(side="left", padx=10)

            # Prepend into audit log
            self.tree_log.insert("", 0, values=(now_str, cat, w["source"], str(w["label"]), str(w["details"])))

    def _copy_log(self):
        rows = []
        for child in self.tree_log.get_children():
            rows.append("\t".join(str(v) for v in self.tree_log.item(child)["values"]))
        self.clipboard_clear()
        self.clipboard_append("\n".join(rows))
        messagebox.showinfo("Copied", "Audit log copied to clipboard!")

    def _clear_log(self):
        if messagebox.askyesno("Clear Log", "Clear session audit log?"):
            for child in self.tree_log.get_children():
                self.tree_log.delete(child)


# ---------------------------------------------------------------------------
# SCREEN 4: Animated Claim Verifier (Dual 2-Strip Sheet Inspector)
# ---------------------------------------------------------------------------
def normalize_ticket_query(query: Any) -> Optional[int]:
    """Extracts integer ticket or sheet number from strings like '#042', ' 042 ', 'Ticket 42', 'Sheet 21'."""
    if query is None:
        return None
    s = str(query).strip().upper()
    for prefix in ["TICKET #", "TICKET#", "TICKET ", "SHEET #", "SHEET#", "SHEET ", "T-", "S-", "#"]:
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
            break
    try:
        return int(s)
    except ValueError:
        return None


def extract_cell_id(cell: Any) -> int:
    """Extracts numeric song ID from integer or dictionary cell."""
    if isinstance(cell, dict):
        return int(cell.get("id", 0))
    elif isinstance(cell, (int, float)):
        return int(cell)
    return 0


def normalize_batch_registry(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes any batch registry (legacy sheets or individual 2-strip pairs) into a unified structure:
    - sheets: {sheet_num: {'sheet': int, 'top': dict, 'bottom': Optional[dict]}}
    - tickets_by_num: {ticket_num: dict}
    - tickets_by_id: {ticket_id_str: dict}
    - ordered_sheet_nums: List[int]
    - tickets_list: List[dict]
    """
    raw_tickets = data.get("tickets", [])
    batch_name = data.get("batch_name", "Unnamed_Batch")
    fmt = data.get("format_mode", "2-strip")
    is_2_strip = "2-strip" in fmt

    sheets: Dict[int, Dict[str, Any]] = {}
    tickets_by_num: Dict[int, Dict[str, Any]] = {}
    tickets_by_id: Dict[str, Dict[str, Any]] = {}
    all_tickets_list: List[Dict[str, Any]] = []

    # Check if raw_tickets already contains individual tickets with 'sheet' and 'grid'
    is_flat_individual = False
    if raw_tickets and "grid" in raw_tickets[0] and "sheet" in raw_tickets[0]:
        is_flat_individual = True

    if is_flat_individual:
        for t in raw_tickets:
            tid_num = normalize_ticket_query(t.get("ticket_id"))
            if tid_num is None:
                continue
            s_num = int(t.get("sheet", (tid_num + 1) // 2 if tid_num % 2 != 0 else tid_num // 2))
            pos = t.get("strip_pos", "Top Strip" if tid_num % 2 != 0 else "Bottom Strip")
            paired = t.get("paired_ticket_id")
            if not paired:
                paired = f"{(tid_num + 1):03d}" if tid_num % 2 != 0 else f"{(tid_num - 1):03d}"

            t_obj = {
                "ticket_id": f"{tid_num:03d}",
                "ticket_num": tid_num,
                "sheet": s_num,
                "strip_pos": pos,
                "paired_ticket_id": paired,
                "grid": t.get("grid", [])
            }
            tickets_by_num[tid_num] = t_obj
            tickets_by_id[f"{tid_num:03d}"] = t_obj
            tickets_by_id[str(tid_num)] = t_obj
            all_tickets_list.append(t_obj)

            if s_num not in sheets:
                sheets[s_num] = {"sheet": s_num, "top": None, "bottom": None}
            if "top" in pos.lower() or tid_num % 2 != 0:
                sheets[s_num]["top"] = t_obj
            else:
                sheets[s_num]["bottom"] = t_obj
    else:
        # Legacy sheets registry where each item in tickets contains strips=[strip1, strip2]
        for s_idx, item in enumerate(raw_tickets, start=1):
            s_num = normalize_ticket_query(item.get("ticket_id", s_idx))
            if s_num is None:
                s_num = s_idx

            strips = item.get("strips", [])
            if not strips:
                continue

            if len(strips) >= 2 or is_2_strip:
                top_tid = s_num * 2 - 1
                bot_tid = s_num * 2

                top_obj = {
                    "ticket_id": f"{top_tid:03d}",
                    "ticket_num": top_tid,
                    "sheet": s_num,
                    "strip_pos": "Top Strip",
                    "paired_ticket_id": f"{bot_tid:03d}",
                    "paired_ticket_num": bot_tid,
                    "grid": strips[0]
                }
                bot_grid = strips[1] if len(strips) > 1 else strips[0]
                bot_obj = {
                    "ticket_id": f"{bot_tid:03d}",
                    "ticket_num": bot_tid,
                    "sheet": s_num,
                    "strip_pos": "Bottom Strip",
                    "paired_ticket_id": f"{top_tid:03d}",
                    "paired_ticket_num": top_tid,
                    "grid": bot_grid
                }

                tickets_by_num[top_tid] = top_obj
                tickets_by_id[f"{top_tid:03d}"] = top_obj
                tickets_by_id[str(top_tid)] = top_obj
                all_tickets_list.append(top_obj)

                tickets_by_num[bot_tid] = bot_obj
                tickets_by_id[f"{bot_tid:03d}"] = bot_obj
                tickets_by_id[str(bot_tid)] = bot_obj
                all_tickets_list.append(bot_obj)

                sheets[s_num] = {"sheet": s_num, "top": top_obj, "bottom": bot_obj}
            else:
                top_obj = {
                    "ticket_id": f"{s_num:03d}",
                    "ticket_num": s_num,
                    "sheet": s_num,
                    "strip_pos": "Single Strip",
                    "paired_ticket_id": None,
                    "paired_ticket_num": None,
                    "grid": strips[0]
                }
                tickets_by_num[s_num] = top_obj
                tickets_by_id[f"{s_num:03d}"] = top_obj
                tickets_by_id[str(s_num)] = top_obj
                all_tickets_list.append(top_obj)
                sheets[s_num] = {"sheet": s_num, "top": top_obj, "bottom": None}

    ordered_sheet_nums = sorted(sheets.keys())
    ordered_ticket_nums = sorted(tickets_by_num.keys())

    return {
        "batch_name": batch_name,
        "total_sheets": len(sheets),
        "total_tickets": len(tickets_by_num),
        "sheets": sheets,
        "tickets_by_num": tickets_by_num,
        "tickets_by_id": tickets_by_id,
        "ordered_sheet_nums": ordered_sheet_nums,
        "ordered_ticket_nums": ordered_ticket_nums,
        "tickets_list": all_tickets_list
    }


def evaluate_strip_patterns(grid: List[List[Any]], called_set: set) -> Dict[str, Any]:
    """Evaluates Tambola claim conditions across a 3x9 grid."""
    all_nums = []
    rows = [[], [], []]
    for r_idx, row in enumerate(grid):
        for cell in row:
            cid = extract_cell_id(cell)
            if cid > 0:
                all_nums.append(cid)
                rows[r_idx].append(cid)

    hits = [n for n in all_nums if n in called_set]
    total_hits = len(hits)
    early5 = total_hits >= 5
    r1 = len(rows[0]) > 0 and all(n in called_set for n in rows[0])
    r2 = len(rows[1]) > 0 and all(n in called_set for n in rows[1])
    r3 = len(rows[2]) > 0 and all(n in called_set for n in rows[2])

    corners = []
    if len(rows[0]) >= 2 and len(rows[2]) >= 2:
        corners = [rows[0][0], rows[0][-1], rows[2][0], rows[2][-1]]
    corn_ok = len(corners) == 4 and all(n in called_set for n in corners)
    fh = len(all_nums) > 0 and total_hits == len(all_nums)

    patterns = []
    if fh: patterns.append("Full House")
    if r1: patterns.append("Top Line")
    if r2: patterns.append("Middle Line")
    if r3: patterns.append("Bottom Line")
    if corn_ok: patterns.append("Four Corners")
    if early5: patterns.append("Early 5")

    return {
        "total_hits": total_hits,
        "total_nums": len(all_nums),
        "early5": early5,
        "r1": r1,
        "r2": r2,
        "r3": r3,
        "corners": corn_ok,
        "full_house": fh,
        "patterns": patterns,
        "r1_hits": sum(1 for n in rows[0] if n in called_set),
        "r2_hits": sum(1 for n in rows[1] if n in called_set),
        "r3_hits": sum(1 for n in rows[2] if n in called_set),
        "corn_hits": sum(1 for n in corners if n in called_set)
    }


class ClaimVerifierScreen(tk.Frame):
    """
    Screen 4: Animated Claim Verifier (Dual 2-Strip Player Sheet Inspector)
    - Full 2-strip sheet pairing: entering either odd or even ticket ID displays the entire player sheet.
    - Prominent live counters: Total Game Drawn, Strip 1 Hits, Strip 2 Hits, and Combined Sheet Total.
    - Staggered scanline reveal with exact call-order badges ([✔ DRAWN — Call #Order]).
    - Automated real-time verdict engine supporting Early 5, Lines, Corners, Full House, and Sheet House.
    """
    def __init__(self, master, app_controller):
        super().__init__(master, bg=PALETTE["bg_body"])
        self.app = app_controller

        self.called_numbers_ref: List[int] = []
        self.batch_files_map: Dict[str, str] = {}
        self.normalized_batch: Optional[Dict[str, Any]] = None
        self.current_tickets: List[Dict[str, Any]] = []  # Backwards compatibility reference

        self.current_sheet_num: Optional[int] = 1
        self.focused_ticket_id: Optional[str] = "001"
        self.dual_view_var = tk.BooleanVar(value=True)

        self.cell_widgets: Dict[Tuple[str, int, int], Tuple[tk.Frame, int]] = {}

        self._init_ui()
        self.reload_batch_registries()

    def _init_ui(self):
        # -------------------------------------------------------------
        # 1. TOP CONTROL HEADER: Batch Selector, Search & Navigation
        # -------------------------------------------------------------
        header = tk.Frame(self, bg=PALETTE["bg_card"], bd=1, relief="solid")
        header.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        header.pack(fill="x", padx=20, pady=(16, 8))

        h_inner = tk.Frame(header, bg=PALETTE["bg_card"], padx=16, pady=10)
        h_inner.pack(fill="x")

        # Row 1: Title and Summary Badge
        top_row = tk.Frame(h_inner, bg=PALETTE["bg_card"])
        top_row.pack(fill="x", pady=(0, 6))

        tk.Label(
            top_row, text="🔍 CLAIM VERIFIER • 2-STRIP PLAYER SHEET INSPECTOR",
            font=("Segoe UI", 12, "bold"), fg=PALETTE["primary"], bg=PALETTE["bg_card"]
        ).pack(side="left")

        self.lbl_batch_stats = tk.Label(
            top_row, text="Scanning archives...",
            font=("Segoe UI", 9, "bold"), fg=PALETTE["emerald_dark"], bg=PALETTE["emerald_light"],
            padx=10, pady=3, relief="solid", bd=1
        )
        self.lbl_batch_stats.pack(side="right")

        # Row 2: Batch Registry Loader & Search Controls
        ctrl_row = tk.Frame(h_inner, bg=PALETTE["bg_card"])
        ctrl_row.pack(fill="x")

        # Left: Batch selector controls
        b_box = tk.Frame(ctrl_row, bg=PALETTE["bg_card"])
        b_box.pack(side="left")

        tk.Label(b_box, text="Batch Registry:", font=("Segoe UI", 9, "bold"), bg=PALETTE["bg_card"], fg=PALETTE["text_muted"]).pack(side="left", padx=(0, 4))
        self.combo_batch = ttk.Combobox(b_box, font=("Segoe UI", 9), width=24)
        self.combo_batch.bind("<<ComboboxSelected>>", self._on_batch_selected)
        self.combo_batch.pack(side="left", padx=(0, 6))

        btn_refresh = tk.Button(
            b_box, text="🔄 Refresh", font=("Segoe UI", 8, "bold"),
            bg=PALETTE["bg_card_alt"], relief="groove", cursor="hand2", padx=6, pady=2,
            command=self.reload_batch_registries
        )
        btn_refresh.pack(side="left", padx=(0, 6))

        btn_browse_json = tk.Button(
            b_box, text="📂 Load External JSON", font=("Segoe UI", 8, "bold"),
            bg=PALETTE["bg_card_alt"], relief="groove", cursor="hand2", padx=6, pady=2,
            command=self.browse_external_registry
        )
        btn_browse_json.pack(side="left", padx=(0, 16))

        # Right: Search & Navigation controls
        s_box = tk.Frame(ctrl_row, bg=PALETTE["bg_card"])
        s_box.pack(side="right")

        tk.Label(s_box, text="Ticket / Sheet #:", font=("Segoe UI", 9, "bold"), bg=PALETTE["bg_card"], fg=PALETTE["text_muted"]).pack(side="left", padx=(0, 4))
        self.txt_search = tk.Entry(s_box, font=("Segoe UI", 10, "bold"), width=8)
        self.txt_search.bind("<Return>", lambda e: self.search_ticket())
        self.txt_search.pack(side="left", padx=(0, 4))

        btn_find = tk.Button(
            s_box, text="🔍 Find", font=("Segoe UI", 9, "bold"),
            bg=PALETTE["primary"], fg=PALETTE["text_white"], activebackground=PALETTE["primary_hover"],
            relief="flat", cursor="hand2", padx=10, pady=2, command=self.search_ticket
        )
        btn_find.pack(side="left", padx=(0, 8))

        btn_prev = tk.Button(
            s_box, text="◀ Prev Sheet", font=("Segoe UI", 8, "bold"),
            bg=PALETTE["bg_card_alt"], relief="groove", cursor="hand2", padx=8, pady=2,
            command=self.prev_sheet
        )
        btn_prev.pack(side="left", padx=(0, 4))

        btn_next = tk.Button(
            s_box, text="Next Sheet ▶", font=("Segoe UI", 8, "bold"),
            bg=PALETTE["bg_card_alt"], relief="groove", cursor="hand2", padx=8, pady=2,
            command=self.next_sheet
        )
        btn_next.pack(side="left", padx=(0, 12))

        chk_dual = tk.Checkbutton(
            s_box, text="Show Full 2-Strip Sheet", variable=self.dual_view_var,
            font=("Segoe UI", 9, "bold"), bg=PALETTE["bg_card"], fg=PALETTE["primary"],
            activebackground=PALETTE["bg_card"], command=self.render_ticket_staggered
        )
        chk_dual.pack(side="left")

        # -------------------------------------------------------------
        # 2. PROMINENT TOP 4 LIVE STATS METRIC CARDS
        # -------------------------------------------------------------
        stats_frame = tk.Frame(self, bg=PALETTE["bg_body"])
        stats_frame.pack(fill="x", padx=20, pady=(0, 8))

        for c_idx in range(4):
            stats_frame.grid_columnconfigure(c_idx, weight=1)

        # Metric 1: Game Drawn Songs
        m1_card = tk.Frame(stats_frame, bg=PALETTE["bg_card"], bd=1, relief="solid")
        m1_card.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        m1_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        m1_inner = tk.Frame(m1_card, bg=PALETTE["bg_card"], padx=12, pady=8)
        m1_inner.pack(fill="both", expand=True)
        tk.Label(m1_inner, text="🎵 GAME SONGS DRAWN", font=("Segoe UI", 8, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(anchor="w")
        self.lbl_stat_game_drawn = tk.Label(m1_inner, text="0 / 90 Drawn", font=("Segoe UI", 14, "bold"), fg=PALETTE["primary"], bg=PALETTE["bg_card"])
        self.lbl_stat_game_drawn.pack(anchor="w")
        self.lbl_stat_game_rem = tk.Label(m1_inner, text="90 Songs Remaining", font=("Segoe UI", 8), fg=PALETTE["text_dim"], bg=PALETTE["bg_card"])
        self.lbl_stat_game_rem.pack(anchor="w")

        # Metric 2: Strip 1 Hits (Top Ticket #ODD)
        m2_card = tk.Frame(stats_frame, bg=PALETTE["bg_card"], bd=1, relief="solid")
        m2_card.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        m2_card.grid(row=0, column=1, sticky="nsew", padx=(0, 6))
        m2_inner = tk.Frame(m2_card, bg=PALETTE["bg_card"], padx=12, pady=8)
        m2_inner.pack(fill="both", expand=True)
        self.lbl_stat_strip1_title = tk.Label(m2_inner, text="🎫 STRIP 1 (#001)", font=("Segoe UI", 8, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"])
        self.lbl_stat_strip1_title.pack(anchor="w")
        self.lbl_stat_strip1_hits = tk.Label(m2_inner, text="0 / 15 Hits", font=("Segoe UI", 14, "bold"), fg=PALETTE["emerald_dark"], bg=PALETTE["bg_card"])
        self.lbl_stat_strip1_hits.pack(anchor="w")
        self.lbl_stat_strip1_status = tk.Label(m2_inner, text="Pending", font=("Segoe UI", 8, "bold"), fg=PALETTE["text_dim"], bg=PALETTE["bg_card"])
        self.lbl_stat_strip1_status.pack(anchor="w")

        # Metric 3: Strip 2 Hits (Bottom Ticket #EVEN)
        m3_card = tk.Frame(stats_frame, bg=PALETTE["bg_card"], bd=1, relief="solid")
        m3_card.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        m3_card.grid(row=0, column=2, sticky="nsew", padx=(0, 6))
        m3_inner = tk.Frame(m3_card, bg=PALETTE["bg_card"], padx=12, pady=8)
        m3_inner.pack(fill="both", expand=True)
        self.lbl_stat_strip2_title = tk.Label(m3_inner, text="🎫 STRIP 2 (#002)", font=("Segoe UI", 8, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"])
        self.lbl_stat_strip2_title.pack(anchor="w")
        self.lbl_stat_strip2_hits = tk.Label(m3_inner, text="0 / 15 Hits", font=("Segoe UI", 14, "bold"), fg=PALETTE["emerald_dark"], bg=PALETTE["bg_card"])
        self.lbl_stat_strip2_hits.pack(anchor="w")
        self.lbl_stat_strip2_status = tk.Label(m3_inner, text="Pending", font=("Segoe UI", 8, "bold"), fg=PALETTE["text_dim"], bg=PALETTE["bg_card"])
        self.lbl_stat_strip2_status.pack(anchor="w")

        # Metric 4: Combined Sheet Total Hits
        m4_card = tk.Frame(stats_frame, bg=PALETTE["bg_card"], bd=1, relief="solid")
        m4_card.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        m4_card.grid(row=0, column=3, sticky="nsew")
        m4_inner = tk.Frame(m4_card, bg=PALETTE["bg_card"], padx=12, pady=8)
        m4_inner.pack(fill="both", expand=True)
        self.lbl_stat_sheet_title = tk.Label(m4_inner, text="🏆 SHEET #1 COMBINED", font=("Segoe UI", 8, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"])
        self.lbl_stat_sheet_title.pack(anchor="w")
        self.lbl_stat_sheet_hits = tk.Label(m4_inner, text="0 / 30 Hits", font=("Segoe UI", 14, "bold"), fg=PALETTE["amber_dark"], bg=PALETTE["bg_card"])
        self.lbl_stat_sheet_hits.pack(anchor="w")
        self.lbl_stat_sheet_status = tk.Label(m4_inner, text="0.0% Match", font=("Segoe UI", 8, "bold"), fg=PALETTE["text_dim"], bg=PALETTE["bg_card"])
        self.lbl_stat_sheet_status.pack(anchor="w")

        # -------------------------------------------------------------
        # 3. REAL-TIME CLAIM VERDICT BANNER & PATTERN CHIPS
        # -------------------------------------------------------------
        self.card_verdict = tk.Frame(self, bg=PALETTE["bg_card"], bd=1, relief="solid")
        self.card_verdict.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        self.card_verdict.pack(fill="x", padx=20, pady=(0, 8))

        v_inner = tk.Frame(self.card_verdict, bg=PALETTE["bg_card"], padx=16, pady=8)
        v_inner.pack(fill="x")

        self.lbl_verdict_title = tk.Label(
            v_inner, text="WAITING FOR TICKET SELECTION",
            font=("Segoe UI", 11, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"]
        )
        self.lbl_verdict_title.pack(anchor="w")

        self.lbl_verdict_sub = tk.Label(
            v_inner, text="Select an archive batch and enter a ticket or sheet number.",
            font=("Segoe UI", 9), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]
        )
        self.lbl_verdict_sub.pack(anchor="w", pady=(1, 4))

        # Progress Chips Row
        self.chips_row = tk.Frame(v_inner, bg=PALETTE["bg_card"])
        self.chips_row.pack(fill="x")

        self.verdict_chips: Dict[str, tk.Label] = {}
        chip_defs = [
            ("s1_e5", "S1 Early 5"), ("s1_l1", "S1 Top Line"), ("s1_l2", "S1 Mid Line"),
            ("s1_l3", "S1 Bot Line"), ("s1_crn", "S1 Corners"), ("s1_fh", "S1 Full House"),
            ("s2_e5", "S2 Early 5"), ("s2_l1", "S2 Top Line"), ("s2_l2", "S2 Mid Line"),
            ("s2_l3", "S2 Bot Line"), ("s2_crn", "S2 Corners"), ("s2_fh", "S2 Full House"),
            ("sheet_house", "Sheet House (30/30)")
        ]

        for k, label in chip_defs:
            lbl = tk.Label(
                self.chips_row, text=f"{label}: —", font=("Segoe UI", 8, "bold"),
                bg=PALETTE["bg_card_alt"], fg=PALETTE["text_dim"],
                relief="solid", bd=1, padx=6, pady=2
            )
            lbl.pack(side="left", padx=(0, 4), pady=2)
            self.verdict_chips[k] = lbl

        # -------------------------------------------------------------
        # 4. SCROLLABLE VISUAL DUAL-STRIP TICKET DISPLAY AREA
        # -------------------------------------------------------------
        card_grids_outer = tk.Frame(self, bg=PALETTE["bg_card"], bd=1, relief="solid")
        card_grids_outer.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        card_grids_outer.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Canvas with Scrollbar for versatile display on all resolutions
        self.canvas_scroll = tk.Canvas(card_grids_outer, bg=PALETTE["bg_card"], highlightthickness=0)
        scroll_y = ttk.Scrollbar(card_grids_outer, orient="vertical", command=self.canvas_scroll.yview)
        self.canvas_scroll.configure(yscrollcommand=scroll_y.set)

        self.scroll_inner = tk.Frame(self.canvas_scroll, bg=PALETTE["bg_card"], padx=14, pady=10)
        self.scroll_window_id = self.canvas_scroll.create_window((0, 0), window=self.scroll_inner, anchor="nw")

        self.scroll_inner.bind("<Configure>", lambda e: self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all")))
        self.canvas_scroll.bind("<Configure>", lambda e: self.canvas_scroll.itemconfig(self.scroll_window_id, width=e.width))

        self.canvas_scroll.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

    # -------------------------------------------------------------
    # REGISTRY BATCH LOADER & EXTERNAL BROWSER
    # -------------------------------------------------------------
    def reload_batch_registries(self):
        """Scans tickets_archive/ for all *_registry.json files."""
        archive_dir = TICKETS_ARCHIVE_DIR
        self.batch_files_map = {}
        if archive_dir.exists():
            for rf in sorted(archive_dir.glob("*_registry.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                disp = rf.name.replace("_registry.json", "")
                self.batch_files_map[disp] = str(rf.resolve())

        items = list(self.batch_files_map.keys())
        self.combo_batch["values"] = items
        if items:
            self.combo_batch.set(items[0])
            self._load_active_registry()
        else:
            self.lbl_batch_stats.config(text="⚠️ No batches in tickets_archive/", bg=PALETTE["amber_light"], fg=PALETTE["amber_dark"])

    def browse_external_registry(self):
        """Allows host to load any external *_registry.json from anywhere on the PC."""
        path = filedialog.askopenfilename(
            title="Select External Ticket Registry JSON",
            filetypes=[("Registry JSON", "*_registry.json *.json"), ("All Files", "*.*")]
        )
        if not path:
            return

        disp_name = Path(path).stem.replace("_registry", "")
        self.batch_files_map[disp_name] = str(Path(path).resolve())
        self.combo_batch["values"] = list(self.batch_files_map.keys())
        self.combo_batch.set(disp_name)
        self._load_active_registry()

    def _on_batch_selected(self, event):
        self._load_active_registry()

    def _load_active_registry(self):
        sel = self.combo_batch.get()
        if sel in self.batch_files_map:
            filepath = self.batch_files_map[sel]
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.normalized_batch = normalize_batch_registry(data)
                self.current_tickets = self.normalized_batch.get("tickets_list", [])
                self.app.sync_tickets_loaded(self.current_tickets)

                tot_sheets = self.normalized_batch["total_sheets"]
                tot_tickets = self.normalized_batch["total_tickets"]
                self.lbl_batch_stats.config(
                    text=f"Loaded: {tot_tickets} Tickets ({tot_sheets} 2-Strip Sheets)",
                    bg=PALETTE["emerald_light"], fg=PALETTE["emerald_dark"]
                )

                # Set initial sheet
                if self.normalized_batch["ordered_sheet_nums"]:
                    self.current_sheet_num = self.normalized_batch["ordered_sheet_nums"][0]
                    first_sheet = self.normalized_batch["sheets"].get(self.current_sheet_num)
                    if first_sheet and first_sheet["top"]:
                        self.focused_ticket_id = first_sheet["top"]["ticket_id"]
                        self.txt_search.delete(0, tk.END)
                        self.txt_search.insert(0, self.focused_ticket_id)

                self.render_ticket_staggered()
            except Exception as e:
                messagebox.showerror("Registry Error", f"Could not load archive registry:\n{e}")

    # -------------------------------------------------------------
    # TICKET SEARCH & SHEET NAVIGATION
    # -------------------------------------------------------------
    def search_ticket(self):
        """
        Searches any entered ticket number (e.g. 1, 001, 2, 42, 042) or sheet number.
        Pulls up that player's entire 2-strip sheet with targeted focus!
        """
        if not self.normalized_batch or not self.normalized_batch["sheets"]:
            messagebox.showwarning("No Batch Loaded", "Please select or load a batch registry above.")
            return

        query_raw = self.txt_search.get().strip()
        num = normalize_ticket_query(query_raw)
        if num is None:
            messagebox.showinfo("Invalid Search", f"Please enter a valid numeric Ticket ID or Sheet Number.")
            return

        # 1. Search directly in tickets_by_num
        if num in self.normalized_batch["tickets_by_num"]:
            t_obj = self.normalized_batch["tickets_by_num"][num]
            self.current_sheet_num = t_obj["sheet"]
            self.focused_ticket_id = t_obj["ticket_id"]
            self.render_ticket_staggered()
            return

        # 2. Search in sheets directly
        if num in self.normalized_batch["sheets"]:
            self.current_sheet_num = num
            sh = self.normalized_batch["sheets"][num]
            self.focused_ticket_id = sh["top"]["ticket_id"] if sh["top"] else f"{num:03d}"
            self.render_ticket_staggered()
            return

        # 3. Mathematically deduce sheet if within overall bounds
        tot_sheets = self.normalized_batch["total_sheets"]
        est_sheet = (num + 1) // 2 if num % 2 != 0 else num // 2
        if est_sheet in self.normalized_batch["sheets"]:
            self.current_sheet_num = est_sheet
            self.focused_ticket_id = f"{num:03d}"
            self.render_ticket_staggered()
            return

        messagebox.showinfo("Ticket Not Found", f"Ticket or Sheet #{num} was not found in active batch '{self.normalized_batch['batch_name']}'.")

    def prev_sheet(self):
        if not self.normalized_batch or not self.normalized_batch["ordered_sheet_nums"]:
            return
        nums = self.normalized_batch["ordered_sheet_nums"]
        if self.current_sheet_num in nums:
            idx = nums.index(self.current_sheet_num)
            if idx > 0:
                self.current_sheet_num = nums[idx - 1]
                sh = self.normalized_batch["sheets"][self.current_sheet_num]
                self.focused_ticket_id = sh["top"]["ticket_id"] if sh["top"] else f"{self.current_sheet_num:03d}"
                self.txt_search.delete(0, tk.END)
                self.txt_search.insert(0, self.focused_ticket_id)
                self.render_ticket_staggered()

    def next_sheet(self):
        if not self.normalized_batch or not self.normalized_batch["ordered_sheet_nums"]:
            return
        nums = self.normalized_batch["ordered_sheet_nums"]
        if self.current_sheet_num in nums:
            idx = nums.index(self.current_sheet_num)
            if idx < len(nums) - 1:
                self.current_sheet_num = nums[idx + 1]
                sh = self.normalized_batch["sheets"][self.current_sheet_num]
                self.focused_ticket_id = sh["top"]["ticket_id"] if sh["top"] else f"{self.current_sheet_num:03d}"
                self.txt_search.delete(0, tk.END)
                self.txt_search.insert(0, self.focused_ticket_id)
                self.render_ticket_staggered()

    # -------------------------------------------------------------
    # 2-STRIP RENDERING & MOTION GRAPHICS SCANLINE REVEAL
    # -------------------------------------------------------------
    def render_current_view(self):
        """Alias for live updates when drawn song counts change."""
        self.render_ticket_staggered()

    def render_ticket_staggered(self):
        """Renders both Strip 1 and Strip 2 on the player's sheet with live counts and scanline animation."""
        for child in self.scroll_inner.winfo_children():
            child.destroy()
        self.cell_widgets.clear()

        if not self.normalized_batch or not self.current_sheet_num:
            return

        sheet_data = self.normalized_batch["sheets"].get(self.current_sheet_num)
        if not sheet_data:
            return

        top_ticket = sheet_data.get("top")
        bottom_ticket = sheet_data.get("bottom")
        if not top_ticket:
            return

        called_set = set(self.called_numbers_ref)
        dual_view = self.dual_view_var.get() and (bottom_ticket is not None)

        # 1. Update Game Drawn Stats
        tot_drawn = len(self.called_numbers_ref)
        self.lbl_stat_game_drawn.config(text=f"{tot_drawn} / 90 Drawn")
        self.lbl_stat_game_rem.config(text=f"{90 - tot_drawn} Songs Remaining")

        # 2. Evaluate Patterns
        ev1 = evaluate_strip_patterns(top_ticket["grid"], called_set)
        ev2 = evaluate_strip_patterns(bottom_ticket["grid"], called_set) if bottom_ticket else None

        # Update Strip 1 Stat Card
        self.lbl_stat_strip1_title.config(text=f"🎫 STRIP 1 (#{top_ticket['ticket_id']})")
        self.lbl_stat_strip1_hits.config(text=f"{ev1['total_hits']} / {ev1['total_nums']} Hits")
        self.lbl_stat_strip1_status.config(
            text=", ".join(ev1["patterns"]) if ev1["patterns"] else f"{ev1['total_nums'] - ev1['total_hits']} Left",
            fg=PALETTE["emerald_dark"] if ev1["patterns"] else PALETTE["text_dim"]
        )

        # Update Strip 2 Stat Card
        if bottom_ticket and ev2:
            self.lbl_stat_strip2_title.config(text=f"🎫 STRIP 2 (#{bottom_ticket['ticket_id']})")
            self.lbl_stat_strip2_hits.config(text=f"{ev2['total_hits']} / {ev2['total_nums']} Hits")
            self.lbl_stat_strip2_status.config(
                text=", ".join(ev2["patterns"]) if ev2["patterns"] else f"{ev2['total_nums'] - ev2['total_hits']} Left",
                fg=PALETTE["emerald_dark"] if ev2["patterns"] else PALETTE["text_dim"]
            )
        else:
            self.lbl_stat_strip2_title.config(text="🎫 STRIP 2 (None)")
            self.lbl_stat_strip2_hits.config(text="—")
            self.lbl_stat_strip2_status.config(text="Single Strip Mode")

        # Update Combined Sheet Stat Card
        combined_hits = ev1["total_hits"] + (ev2["total_hits"] if ev2 else 0)
        combined_total = ev1["total_nums"] + (ev2["total_nums"] if ev2 else 0)
        pct = (combined_hits / combined_total * 100) if combined_total > 0 else 0
        sheet_house_ok = (combined_hits == combined_total and combined_total > 0)

        self.lbl_stat_sheet_title.config(text=f"🏆 SHEET #{self.current_sheet_num} COMBINED")
        self.lbl_stat_sheet_hits.config(text=f"{combined_hits} / {combined_total} Hits")
        self.lbl_stat_sheet_status.config(
            text="🌟 SHEET HOUSE QUALIFIED!" if sheet_house_ok else f"{pct:.1f}% Sheet Match",
            fg=PALETTE["emerald_dark"] if sheet_house_ok else PALETTE["amber_dark"]
        )

        # 3. Update Chips
        self._update_chip("s1_e5", f"{min(5, ev1['total_hits'])}/5", ev1["early5"])
        self._update_chip("s1_l1", f"{ev1['r1_hits']}/5", ev1["r1"])
        self._update_chip("s1_l2", f"{ev1['r2_hits']}/5", ev1["r2"])
        self._update_chip("s1_l3", f"{ev1['r3_hits']}/5", ev1["r3"])
        self._update_chip("s1_crn", f"{ev1['corn_hits']}/4", ev1["corners"])
        self._update_chip("s1_fh", f"{ev1['total_hits']}/15", ev1["full_house"])

        if ev2:
            self._update_chip("s2_e5", f"{min(5, ev2['total_hits'])}/5", ev2["early5"])
            self._update_chip("s2_l1", f"{ev2['r1_hits']}/5", ev2["r1"])
            self._update_chip("s2_l2", f"{ev2['r2_hits']}/5", ev2["r2"])
            self._update_chip("s2_l3", f"{ev2['r3_hits']}/5", ev2["r3"])
            self._update_chip("s2_crn", f"{ev2['corn_hits']}/4", ev2["corners"])
            self._update_chip("s2_fh", f"{ev2['total_hits']}/15", ev2["full_house"])
        else:
            for k in ["s2_e5", "s2_l1", "s2_l2", "s2_l3", "s2_crn", "s2_fh"]:
                self._update_chip(k, "—", False)

        self._update_chip("sheet_house", f"{combined_hits}/{combined_total}", sheet_house_ok)

        # 4. Update Verdict Banner
        all_qualified = []
        if sheet_house_ok:
            all_qualified.append(f"DOUBLE FULL HOUSE (Sheet #{self.current_sheet_num} 30/30)")
        for p in ev1["patterns"]:
            all_qualified.append(f"Strip 1 {p}")
        if ev2:
            for p in ev2["patterns"]:
                all_qualified.append(f"Strip 2 {p}")

        if all_qualified:
            self.lbl_verdict_title.config(
                text=f"🎉 BOGEY VALIDATED: {', '.join(all_qualified[:3])} QUALIFIED!",
                fg=PALETTE["emerald_dark"]
            )
            self.lbl_verdict_sub.config(
                text=f"Sheet #{self.current_sheet_num} meets winning criteria ({combined_hits}/{combined_total} songs verified)."
            )
            self.card_verdict.config(bg=PALETTE["emerald_light"])
        else:
            rem1 = ev1["total_nums"] - ev1["total_hits"]
            rem2 = (ev2["total_nums"] - ev2["total_hits"]) if ev2 else 0
            self.lbl_verdict_title.config(
                text=f"⏳ CLAIM PENDING • Strip 1: {rem1} Left • Strip 2: {rem2} Left",
                fg=PALETTE["coral_dark"]
            )
            self.lbl_verdict_sub.config(
                text=f"Current Match: {combined_hits} of {combined_total} songs drawn. Review individual cells below."
            )
            self.card_verdict.config(bg=PALETTE["bg_card"])

        # -------------------------------------------------------------
        # 5. RENDER DUAL 3x9 GRIDS (STRIP 1 & STRIP 2)
        # -------------------------------------------------------------
        # Determine whether to show both or single strip
        focused_is_bottom = (bottom_ticket and str(self.focused_ticket_id).lstrip("#") == str(bottom_ticket["ticket_id"]).lstrip("#"))

        # Render Strip 1 Card
        if dual_view or not focused_is_bottom:
            self._build_strip_card(
                parent=self.scroll_inner,
                strip_key="strip1",
                ticket_data=top_ticket,
                sheet_num=self.current_sheet_num,
                is_queried=(not focused_is_bottom),
                hits_text=f"{ev1['total_hits']}/15 Hits"
            )

        # Render Strip 2 Card
        if bottom_ticket and (dual_view or focused_is_bottom):
            self._build_strip_card(
                parent=self.scroll_inner,
                strip_key="strip2",
                ticket_data=bottom_ticket,
                sheet_num=self.current_sheet_num,
                is_queried=focused_is_bottom,
                hits_text=f"{ev2['total_hits']}/15 Hits"
            )

        # 6. Execute Staggered Scanline Reveal (20ms per column)
        strips_to_reveal = [("strip1", top_ticket["grid"])]
        if bottom_ticket and (dual_view or focused_is_bottom):
            strips_to_reveal.append(("strip2", bottom_ticket["grid"]))

        for c in range(9):
            self.after(c * 20, lambda col=c, s_list=strips_to_reveal: self._reveal_scanline_column(col, s_list))

    def _build_strip_card(self, parent, strip_key: str, ticket_data: Dict[str, Any], sheet_num: int, is_queried: bool, hits_text: str):
        """Constructs an individual strip card frame and sets up the 3x9 table skeleton."""
        tid = ticket_data["ticket_id"]
        pos = ticket_data.get("strip_pos", "Strip")

        card = tk.Frame(parent, bg=PALETTE["bg_card"], bd=1, relief="solid")
        card_border = PALETTE["primary"] if is_queried else PALETTE["border"]
        card.configure(highlightbackground=card_border, highlightthickness=2 if is_queried else 1)
        card.pack(fill="x", pady=(0, 10))

        # Header Strip
        c_hdr = tk.Frame(card, bg=PALETTE["primary_light"] if is_queried else PALETTE["bg_card_alt"], padx=12, pady=6)
        c_hdr.pack(fill="x")

        # Left label
        hdr_txt = f"🎫 {pos.upper()} • TICKET #{tid}  (PLAYER SHEET #{sheet_num})"
        tk.Label(
            c_hdr, text=hdr_txt, font=("Segoe UI", 10, "bold"),
            fg=PALETTE["primary"] if is_queried else PALETTE["text_main"],
            bg=c_hdr["bg"]
        ).pack(side="left")

        # Right tags
        if is_queried:
            tk.Label(
                c_hdr, text="★ QUERIED TICKET", font=("Segoe UI", 8, "bold"),
                bg=PALETTE["primary"], fg=PALETTE["text_white"], padx=8, pady=2
            ).pack(side="right", padx=(6, 0))
        else:
            tk.Label(
                c_hdr, text="COMPANION STRIP", font=("Segoe UI", 8, "bold"),
                bg=PALETTE["bg_card"], fg=PALETTE["text_muted"], padx=6, pady=2, relief="solid", bd=1
            ).pack(side="right", padx=(6, 0))

        tk.Label(
            c_hdr, text=hits_text, font=("Segoe UI", 9, "bold"),
            bg=PALETTE["emerald_light"], fg=PALETTE["emerald_dark"], padx=8, pady=2, relief="solid", bd=1
        ).pack(side="right")

        # 3x9 Grid Frame
        grid_frame = tk.Frame(card, bg=PALETTE["bg_card"], padx=10, pady=8)
        grid_frame.pack(fill="x")

        for c in range(9):
            grid_frame.grid_columnconfigure(c, weight=1)

        grid = ticket_data.get("grid", [])
        for r_idx, row in enumerate(grid):
            grid_frame.grid_rowconfigure(r_idx, weight=1)
            for c_idx, cell in enumerate(row):
                cid = extract_cell_id(cell)
                box = tk.Frame(grid_frame, bg=PALETTE["bg_card_alt"], bd=1, relief="solid")
                box.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
                box.grid(row=r_idx, column=c_idx, sticky="nsew", padx=2, pady=2)
                self.cell_widgets[(strip_key, r_idx, c_idx)] = (box, cid)

    def _reveal_scanline_column(self, col: int, strips_to_reveal: List[Tuple[str, List[List[Any]]]]):
        """Animates column `col` left-to-right with high-contrast colors, call orders, and hit badges."""
        called_set = set(self.called_numbers_ref)
        last_drawn_num = self.called_numbers_ref[-1] if self.called_numbers_ref else None

        for strip_key, grid in strips_to_reveal:
            for r in range(3):
                key = (strip_key, r, col)
                if key not in self.cell_widgets:
                    continue
                box, cell_id = self.cell_widgets[key]

                for child in box.winfo_children():
                    child.destroy()

                if cell_id > 0:
                    is_hit = cell_id in called_set
                    song_title = song_bank.get_song_title(cell_id)

                    if is_hit:
                        order = self.called_numbers_ref.index(cell_id) + 1
                        is_latest = (cell_id == last_drawn_num)

                        bg_col = PALETTE["emerald_light"]
                        bd_col = PALETTE["coral"] if is_latest else PALETTE["emerald"]
                        box.config(bg=bg_col)
                        box.configure(highlightbackground=bd_col, highlightthickness=2 if is_latest else 1)

                        # Track number
                        tk.Label(
                            box, text=f"#{cell_id:02d}", font=("Segoe UI", 10, "bold"),
                            fg=PALETTE["emerald_dark"], bg=bg_col
                        ).pack(anchor="center", pady=(3, 0))

                        # Song title
                        tk.Label(
                            box, text=song_title, font=("Segoe UI", 8, "bold"),
                            fg=PALETTE["text_main"], bg=bg_col, wraplength=105, justify="center"
                        ).pack(anchor="center")

                        # Call Order Badge
                        if is_latest:
                            badge_text = f"[★ LATEST — Call #{order}]"
                            b_fg = PALETTE["coral"]
                        else:
                            badge_text = f"[✔ DRAWN — Call #{order}]"
                            b_fg = PALETTE["emerald"]

                        tk.Label(
                            box, text=badge_text, font=("Segoe UI", 7, "bold"),
                            fg=b_fg, bg=bg_col
                        ).pack(anchor="center", pady=(2, 3))

                    else:
                        bg_col = "#FFFFFF"
                        box.config(bg=bg_col)
                        box.configure(highlightbackground=PALETTE["border"], highlightthickness=1)

                        tk.Label(
                            box, text=f"#{cell_id:02d}", font=("Segoe UI", 10, "bold"),
                            fg=PALETTE["text_muted"], bg=bg_col
                        ).pack(anchor="center", pady=(3, 0))

                        tk.Label(
                            box, text=song_title, font=("Segoe UI", 8),
                            fg=PALETTE["text_muted"], bg=bg_col, wraplength=105, justify="center"
                        ).pack(anchor="center")

                        tk.Label(
                            box, text="[⏳ PENDING]", font=("Segoe UI", 7),
                            fg=PALETTE["text_dim"], bg=bg_col
                        ).pack(anchor="center", pady=(2, 3))
                else:
                    box.config(bg=PALETTE["cell_blank"])
                    box.configure(highlightbackground=PALETTE["cell_blank_border"], highlightthickness=1)
                    tk.Label(
                        box, text="—", font=("Segoe UI", 11),
                        fg=PALETTE["text_dim"], bg=PALETTE["cell_blank"]
                    ).pack(anchor="center", pady=14)

    def _update_chip(self, chip_key: str, progress: str, is_ok: bool):
        lbl = self.verdict_chips.get(chip_key)
        if lbl:
            txt = lbl.cget("text").split(":")[0]
            if is_ok:
                lbl.config(text=f"{txt}: {progress} ✔", bg=PALETTE["emerald_light"], fg=PALETTE["emerald_dark"])
            else:
                lbl.config(text=f"{txt}: {progress}", bg=PALETTE["bg_card_alt"], fg=PALETTE["text_muted"])


# ---------------------------------------------------------------------------
# SCREEN 5: Non-Destructive Ticket Studio
# ---------------------------------------------------------------------------
class TicketStudioScreen(tk.Frame):
    """
    Screen 5: Non-Destructive Ticket Studio
    - 2-strip landscape A4 generator with .hide-top-slots CSS patch.
    - Strict Non-Destructive Collision Guard: checks os.path.exists() before saving,
      appending unique timestamp suffix so existing tickets are NEVER overwritten.
    """
    def __init__(self, master, app_controller):
        super().__init__(master, bg=PALETTE["bg_body"])
        self.app = app_controller

        self.selected_template_path: Optional[str] = None
        self.last_generated_html: Optional[str] = None

        self._init_ui()

    def _init_ui(self):
        # Header Card
        header = tk.Frame(self, bg=PALETTE["bg_card"], bd=1, relief="solid")
        header.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        header.pack(fill="x", padx=20, pady=(16, 12))

        h_inner = tk.Frame(header, bg=PALETTE["bg_card"], padx=16, pady=10)
        h_inner.pack(fill="x")

        tk.Label(h_inner, text="🎫 TICKET GENERATOR & TEMPLATE STUDIO", font=("Segoe UI", 12, "bold"), fg=PALETTE["primary"], bg=PALETTE["bg_card"]).pack(side="left")

        badge = tk.Label(h_inner, text="🛡️ Strict Non-Destructive Archival Guaranteed", font=("Segoe UI", 9, "bold"), fg=PALETTE["emerald_dark"], bg=PALETTE["emerald_light"], padx=8, pady=3)
        badge.pack(side="right")

        # Split 2 Columns
        split_frame = tk.Frame(self, bg=PALETTE["bg_body"])
        split_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Left Form Panel (440px)
        form_panel = tk.Frame(split_frame, bg=PALETTE["bg_card"], bd=1, relief="solid", width=440)
        form_panel.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        form_panel.pack(side="left", fill="y", padx=(0, 10))
        form_panel.pack_propagate(False)

        f_inner = tk.Frame(form_panel, bg=PALETTE["bg_card"], padx=16, pady=16)
        f_inner.pack(fill="both", expand=True)

        tk.Label(f_inner, text="Batch / Event Name (e.g. Diwali_Gala_2026):", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(anchor="w")
        self.txt_batch = tk.Entry(f_inner, font=("Segoe UI", 10))
        self.txt_batch.insert(0, f"Musical_Housie_{datetime.now().strftime('%Y%m%d')}")
        self.txt_batch.pack(fill="x", pady=(2, 4))

        self.lbl_guard_status = tk.Label(f_inner, text="✓ Collision Guard Active", font=("Segoe UI", 9, "bold"), fg=PALETTE["emerald_dark"], bg=PALETTE["bg_card"])
        self.lbl_guard_status.pack(anchor="w", pady=(0, 12))

        # Template Picker
        tk.Label(f_inner, text="Background Template Image:", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(anchor="w")
        tpl_row = tk.Frame(f_inner, bg=PALETTE["bg_card"])
        tpl_row.pack(fill="x", pady=(2, 12))

        self.combo_tpl = ttk.Combobox(tpl_row, font=("Segoe UI", 9))
        self._populate_templates()
        self.combo_tpl.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.combo_tpl.bind("<<ComboboxSelected>>", self._on_template_picked)

        btn_browse = tk.Button(tpl_row, text="Browse...", font=("Segoe UI", 8), bg=PALETTE["bg_card_alt"], relief="groove", cursor="hand2", command=self._browse_custom_template)
        btn_browse.pack(side="right")

        # Sheet Count
        tk.Label(f_inner, text="Number of Sheets (2 tickets / sheet):", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(anchor="w")
        self.spin_sheets = ttk.Spinbox(f_inner, from_=1, to=500, font=("Segoe UI", 10), width=8)
        self.spin_sheets.set(50)
        self.spin_sheets.pack(anchor="w", pady=(2, 12))

        # Format Mode
        tk.Label(f_inner, text="Format Mode:", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(anchor="w")
        self.combo_fmt = ttk.Combobox(f_inner, values=["2-Strip Landscape (2 tickets per A4)", "1-Strip Landscape (1 ticket per page)"], font=("Segoe UI", 9))
        self.combo_fmt.set("2-Strip Landscape (2 tickets per A4)")
        self.combo_fmt.pack(fill="x", pady=(2, 14))

        # Progress bar
        self.progress = ttk.Progressbar(f_inner, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 12))

        # Generate Button
        self.btn_gen = tk.Button(
            f_inner, text="🚀 GENERATE & ARCHIVE HOUSIE TICKETS",
            font=("Segoe UI", 11, "bold"), bg=PALETTE["primary"], fg=PALETTE["text_white"],
            activebackground=PALETTE["primary_hover"], relief="flat", cursor="hand2", height=2,
            command=self.generate_batch
        )
        self.btn_gen.pack(fill="x", side="bottom")

        # Right Console & Actions Panel
        r_panel = tk.Frame(split_frame, bg=PALETTE["bg_card"], bd=1, relief="solid")
        r_panel.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        r_panel.pack(side="right", fill="both", expand=True)

        r_inner = tk.Frame(r_panel, bg=PALETTE["bg_card"], padx=18, pady=16)
        r_inner.pack(fill="both", expand=True)

        tk.Label(r_inner, text="Template Preview & Generation Console", font=("Segoe UI", 11, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"]).pack(anchor="w")

        self.canvas_tpl_preview = tk.Canvas(r_inner, height=220, bg=PALETTE["bg_card_alt"], highlightthickness=1, highlightbackground=PALETTE["border"])
        self.canvas_tpl_preview.pack(fill="x", pady=10)
        self.canvas_tpl_preview.create_text(200, 110, text="Minimalist Clean Layout (No Template)", font=("Segoe UI", 10), fill=PALETTE["text_muted"])

        self.lbl_gen_status = tk.Label(r_inner, text="Ready to generate immutable ticket batch.", font=("Segoe UI", 10, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"])
        self.lbl_gen_status.pack(anchor="w", pady=(8, 2))

        self.lbl_gen_path = tk.Label(r_inner, text="Output destination: tickets_archive/<Batch_Name>.html", font=("Segoe UI", 9), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"], wraplength=480, justify="left")
        self.lbl_gen_path.pack(anchor="w", pady=(0, 14))

        btn_row = tk.Frame(r_inner, bg=PALETTE["bg_card"])
        btn_row.pack(fill="x")

        self.btn_open_browser = tk.Button(btn_row, text="🌐 Open in Web Browser", font=("Segoe UI", 10, "bold"), bg=PALETTE["bg_card_alt"], relief="groove", cursor="hand2", state="disabled", padx=14, pady=6, command=self._open_in_browser)
        self.btn_open_browser.pack(side="left", padx=(0, 10))

        btn_open_folder = tk.Button(btn_row, text="📁 Open Archive Folder", font=("Segoe UI", 10, "bold"), bg=PALETTE["bg_card_alt"], relief="groove", cursor="hand2", padx=14, pady=6, command=self._open_archive_folder)
        btn_open_folder.pack(side="left")

    def _populate_templates(self):
        self.tpl_map = {"None (Clean Minimalist)": ""}
        brand_dir = BRANDING_DIR
        if brand_dir.exists():
            for p in sorted(brand_dir.glob("*.png")) + sorted(brand_dir.glob("*.jpg")):
                self.tpl_map[p.name] = str(p)
        self.combo_tpl["values"] = list(self.tpl_map.keys())
        self.combo_tpl.set("None (Clean Minimalist)")

    def _on_template_picked(self, event):
        sel = self.combo_tpl.get()
        self.selected_template_path = self.tpl_map.get(sel, "")
        self._render_template_preview()

    def _browse_custom_template(self):
        path = filedialog.askopenfilename(
            title="Select Background Template Image",
            initialdir=str(BRANDING_DIR if BRANDING_DIR.exists() else BASE_DIR),
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")]
        )
        if path:
            name = Path(path).name
            self.tpl_map[name] = path
            self.combo_tpl["values"] = list(self.tpl_map.keys())
            self.combo_tpl.set(name)
            self.selected_template_path = path
            self._render_template_preview()

    def _render_template_preview(self):
        self.canvas_tpl_preview.delete("all")
        if self.selected_template_path and os.path.exists(self.selected_template_path):
            try:
                img = Image.open(self.selected_template_path)
                img.thumbnail((380, 200))
                self.tk_tpl_img = ImageTk.PhotoImage(img)
                self.canvas_tpl_preview.create_image(200, 110, image=self.tk_tpl_img)
                return
            except Exception:
                pass
        self.canvas_tpl_preview.create_text(200, 110, text="Minimalist Clean Layout (No Template)", font=("Segoe UI", 10), fill=PALETTE["text_muted"])

    def generate_batch(self):
        """Generates tickets enforcing strict Non-Destructive Collision Guard."""
        raw_name = self.txt_batch.get().strip()
        if not raw_name:
            messagebox.showwarning("Batch Name", "Please enter an event or batch name.")
            return

        clean = sanitize_batch_name(raw_name)

        # -------------------------------------------------------------
        # STRICT NON-DESTRUCTIVE COLLISION GUARD:
        # Check if file exists, automatically append timestamp if so!
        # -------------------------------------------------------------
        archive_html = TICKETS_ARCHIVE_DIR / f"{clean}.html"
        archive_reg = TICKETS_ARCHIVE_DIR / f"{clean}_registry.json"

        if archive_html.exists() or archive_reg.exists():
            timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_batch_name = f"{clean}_{timestamp_suffix}"
            self.lbl_guard_status.config(
                text=f"🛡️ Safeguarded: Batch existed. Auto-incremented to {target_batch_name}",
                fg=PALETTE["amber_dark"]
            )
        else:
            target_batch_name = clean
            self.lbl_guard_status.config(text="✓ Available Unique Batch Name", fg=PALETTE["emerald_dark"])

        sheets = int(self.spin_sheets.get())
        fmt_mode = "2-strip" if "2-Strip" in self.combo_fmt.get() else "1-strip"

        try:
            self.btn_gen.config(state="disabled")
            self.progress.start(10)
            self.lbl_gen_status.config(text=f"Generating {sheets} balanced sheets for '{target_batch_name}'...")
            self.update_idletasks()

            out_html = generate_housie_tickets(
                num_sheets=sheets,
                format_mode=fmt_mode,
                template_path=self.selected_template_path,
                show_participant_slots=True,
                batch_name=target_batch_name
            )

            self.last_generated_html = out_html
            self.btn_open_browser.config(state="normal")
            self.lbl_gen_status.config(text=f"✔ Successfully Archived: {target_batch_name}.html")
            self.lbl_gen_path.config(text=f"Saved at: {out_html}")

            self.app.sync_batch_generated(out_html)

            messagebox.showinfo(
                "Generation Success",
                f"Tickets generated successfully without touching prior batches!\n\n"
                f"Archived: {target_batch_name}.html\n"
                f"Registry: {target_batch_name}_registry.json\n\n"
                f"Click 'Open in Web Browser' to view & print."
            )
        except Exception as e:
            messagebox.showerror("Generation Error", f"Failed to generate tickets: {e}")
            self.lbl_gen_status.config(text="Generation encountered an error.")
        finally:
            self.progress.stop()
            self.btn_gen.config(state="normal")

    def _open_in_browser(self):
        if self.last_generated_html and os.path.exists(self.last_generated_html):
            webbrowser.open(Path(self.last_generated_html).resolve().as_uri())

    def _open_archive_folder(self):
        folder = str(TICKETS_ARCHIVE_DIR.resolve())
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            webbrowser.open(Path(folder).as_uri())


# ---------------------------------------------------------------------------
# SCREEN 6: Audio Catalog & Song Studio (PRD Module 2.1)
# ---------------------------------------------------------------------------
class AudioCatalogScreen(tk.Frame):
    """
    Screen 6: Audio Catalog & Song Asset Studio
    - Custom Songs Folder Selector with smart 1-90 file matching.
    - Song Catalog Upload (.csv / .xlsx) with Start Time & Clip Duration parsing.
    - Live Search & Pillar Filters (Satyam, Shivam, Sundaram, Missing Audio).
    - 90-Track Catalog Treeview (Serial, Pillar, Title, Start Cue, Path, File Status, Game Status).
    - Right Panel: Interactive Timestamp & Clip Cue Editor, Test Playback from Start Cue,
      Animated Equalizer Canvas, and Single File Linker.
    """
    def __init__(self, master, app_controller):
        super().__init__(master, bg=PALETTE["bg_body"])
        self.app = app_controller

        self.selected_song_id: Optional[int] = 1
        self.active_filter = "all"
        self.search_query = ""

        # Mini Equalizer & Preview Playback State
        self.is_preview_playing = False
        self._preview_timer: Optional[str] = None
        self.eq_step = 0
        self.eq_bars = [4.0] * 14

        self._init_ui()
        self._update_folder_label()
        self.populate_catalog()

    def _init_ui(self):
        # -------------------------------------------------------------
        # TOP CONTROL CARD: Title, Folder Path, Catalog Upload & Filters
        # -------------------------------------------------------------
        card_filter = tk.Frame(self, bg=PALETTE["bg_card"], bd=1, relief="solid")
        card_filter.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        card_filter.pack(fill="x", padx=20, pady=(16, 12))

        f_inner = tk.Frame(card_filter, bg=PALETTE["bg_card"], padx=16, pady=10)
        f_inner.pack(fill="x")

        # Row 1: Title & Ready Files Summary Badge
        top_row = tk.Frame(f_inner, bg=PALETTE["bg_card"])
        top_row.pack(fill="x", pady=(0, 8))

        tk.Label(
            top_row, text="🎵 AUDIO CATALOG & SONG ASSET STUDIO",
            font=("Segoe UI", 12, "bold"), fg=PALETTE["primary"], bg=PALETTE["bg_card"]
        ).pack(side="left")

        self.lbl_summary_badge = tk.Label(
            top_row, text="Scanning songs...",
            font=("Segoe UI", 9, "bold"), fg=PALETTE["emerald_dark"], bg=PALETTE["emerald_light"],
            padx=10, pady=3, relief="solid", bd=1
        )
        self.lbl_summary_badge.pack(side="right")

        # Row 2: Folder Path Configuration & Batch Tools
        tools_row = tk.Frame(f_inner, bg=PALETTE["bg_card"])
        tools_row.pack(fill="x", pady=(0, 8))

        btn_folder = tk.Button(
            tools_row, text="📁 Set Songs Folder Path",
            font=("Segoe UI", 9, "bold"), bg=PALETTE["primary_light"], fg=PALETTE["primary"],
            activebackground=PALETTE["primary"], activeforeground=PALETTE["text_white"],
            relief="flat", cursor="hand2", padx=10, pady=4,
            command=self.choose_audio_folder
        )
        btn_folder.pack(side="left", padx=(0, 8))

        self.lbl_folder_path = tk.Label(
            tools_row, text="Active Folder: songs/ (Default)",
            font=("Segoe UI", 9), fg=PALETTE["text_main"], bg=PALETTE["bg_card_alt"],
            relief="solid", bd=1, padx=10, pady=3
        )
        self.lbl_folder_path.pack(side="left", padx=(0, 16))

        btn_upload = tk.Button(
            tools_row, text="📄 Upload Catalog (Excel/CSV)",
            font=("Segoe UI", 9, "bold"), bg=PALETTE["emerald_light"], fg=PALETTE["emerald_dark"],
            activebackground=PALETTE["emerald"], activeforeground=PALETTE["text_white"],
            relief="flat", cursor="hand2", padx=10, pady=4,
            command=self.upload_catalog_file
        )
        btn_upload.pack(side="right", padx=(8, 0))

        btn_rescan = tk.Button(
            tools_row, text="🔄 Re-scan Directory",
            font=("Segoe UI", 9, "bold"), bg=PALETTE["bg_card_alt"], fg=PALETTE["text_main"],
            relief="groove", cursor="hand2", padx=10, pady=4,
            command=self.rescan_directory
        )
        btn_rescan.pack(side="right")

        # Row 3: Live Search Entry & Decade / Missing Filters
        ctrl_row = tk.Frame(f_inner, bg=PALETTE["bg_card"])
        ctrl_row.pack(fill="x")

        tk.Label(ctrl_row, text="Search Track:", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(side="left", padx=(0, 6))
        self.txt_search = tk.Entry(ctrl_row, font=("Segoe UI", 10), width=18)
        self.txt_search.pack(side="left", padx=(0, 16))
        self.txt_search.bind("<KeyRelease>", self._on_search_changed)

        self.filter_buttons: Dict[str, tk.Button] = {}
        filters_meta = [
            ("all", "All (1–90)"),
            ("satyam", "सत्यम / Satyam (1–29)"),
            ("shivam", "शिवम / Shivam (30–59)"),
            ("sundaram", "सुन्दरम / Sundaram (60–90)"),
            ("missing", "⚠️ Missing Audio Only")
        ]

        pills_box = tk.Frame(ctrl_row, bg=PALETTE["bg_card"])
        pills_box.pack(side="left")

        for f_key, f_label in filters_meta:
            btn = tk.Button(
                pills_box, text=f_label, font=("Segoe UI", 9, "bold"),
                bg=PALETTE["primary"] if f_key == "all" else PALETTE["bg_card_alt"],
                fg=PALETTE["text_white"] if f_key == "all" else PALETTE["text_muted"],
                relief="flat", cursor="hand2", padx=10, pady=3,
                command=lambda k=f_key: self.set_filter(k)
            )
            btn.pack(side="left", padx=3)
            self.filter_buttons[f_key] = btn

        # -------------------------------------------------------------
        # MAIN SPLIT CONTENT: Treeview (Left) + Inspector Deck (Right)
        # -------------------------------------------------------------
        split_frame = tk.Frame(self, bg=PALETTE["bg_body"])
        split_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Left / Center Table Card
        table_card = tk.Frame(split_frame, bg=PALETTE["bg_card"], bd=1, relief="solid")
        table_card.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        table_card.pack(side="left", fill="both", expand=True, padx=(0, 12))

        t_inner = tk.Frame(table_card, bg=PALETTE["bg_card"], padx=12, pady=12)
        t_inner.pack(fill="both", expand=True)

        cols = ("serial", "pillar", "title", "start_cue", "file_path", "file_status", "game_status")
        self.tree_catalog = ttk.Treeview(t_inner, columns=cols, show="headings", selectmode="browse")

        self.tree_catalog.heading("serial", text="Serial")
        self.tree_catalog.heading("pillar", text="Pillar / Column")
        self.tree_catalog.heading("title", text="Song Title")
        self.tree_catalog.heading("start_cue", text="Start Cue (MM:SS)")
        self.tree_catalog.heading("file_path", text="Audio File Path")
        self.tree_catalog.heading("file_status", text="File Status")
        self.tree_catalog.heading("game_status", text="Game Status")

        self.tree_catalog.column("serial", width=65, anchor="center")
        self.tree_catalog.column("pillar", width=135, anchor="w")
        self.tree_catalog.column("title", width=210, anchor="w")
        self.tree_catalog.column("start_cue", width=125, anchor="center")
        self.tree_catalog.column("file_path", width=165, anchor="w")
        self.tree_catalog.column("file_status", width=100, anchor="center")
        self.tree_catalog.column("game_status", width=95, anchor="center")

        scroll_y = ttk.Scrollbar(t_inner, orient="vertical", command=self.tree_catalog.yview)
        self.tree_catalog.configure(yscrollcommand=scroll_y.set)

        self.tree_catalog.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        self.tree_catalog.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree_catalog.bind("<Double-1>", lambda e: self.test_start_cue())

        # -------------------------------------------------------------
        # RIGHT PANEL: Track Inspector & Interactive Start-Time Editor
        # -------------------------------------------------------------
        self.preview_panel = tk.Frame(split_frame, bg=PALETTE["bg_card"], bd=1, relief="solid", width=390)
        self.preview_panel.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        self.preview_panel.pack(side="right", fill="y")
        self.preview_panel.pack_propagate(False)

        p_inner = tk.Frame(self.preview_panel, bg=PALETTE["bg_card"], padx=16, pady=14)
        p_inner.pack(fill="both", expand=True)

        tk.Label(p_inner, text="Track Inspector & Audio Deck", font=("Segoe UI", 11, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"]).pack(anchor="w")

        # Serial / Pillar Badge Box
        self.badge_box = tk.Frame(p_inner, bg=PALETTE["primary_light"], padx=10, pady=4)
        self.badge_box.pack(anchor="w", pady=(6, 4))
        self.lbl_deck_serial = tk.Label(self.badge_box, text="Track #01", font=("Segoe UI", 10, "bold"), fg=PALETTE["primary"], bg=PALETTE["primary_light"])
        self.lbl_deck_serial.pack(side="left")
        self.lbl_deck_pillar = tk.Label(self.badge_box, text=" • Satyam (Col 1)", font=("Segoe UI", 10), fg=PALETTE["primary"], bg=PALETTE["primary_light"])
        self.lbl_deck_pillar.pack(side="left")

        # Track Title & Album
        self.lbl_deck_title = tk.Label(
            p_inner, text="Select a song from catalog",
            font=("Segoe UI", 12, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"],
            wraplength=350, justify="left"
        )
        self.lbl_deck_title.pack(anchor="w", pady=(2, 2))

        self.lbl_deck_artist = tk.Label(
            p_inner, text="", font=("Segoe UI", 9), fg=PALETTE["text_muted"],
            bg=PALETTE["bg_card"], wraplength=350, justify="left"
        )
        self.lbl_deck_artist.pack(anchor="w", pady=(0, 6))

        # File Status Card
        self.card_status = tk.Frame(p_inner, bg=PALETTE["bg_card_alt"], bd=1, relief="solid")
        self.card_status.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        self.card_status.pack(fill="x", pady=(0, 8))

        cs_inner = tk.Frame(self.card_status, bg=PALETTE["bg_card_alt"], padx=10, pady=6)
        cs_inner.pack(fill="x")

        self.lbl_deck_status = tk.Label(
            cs_inner, text="Status: Verifying file...",
            font=("Segoe UI", 9, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card_alt"]
        )
        self.lbl_deck_status.pack(anchor="w")

        self.lbl_deck_path = tk.Label(
            cs_inner, text="Path: —",
            font=("Segoe UI", 8), fg=PALETTE["text_muted"], bg=PALETTE["bg_card_alt"],
            wraplength=330, justify="left"
        )
        self.lbl_deck_path.pack(anchor="w", pady=(2, 0))

        # -------------------------------------------------------------
        # INTERACTIVE START-TIME & CLIP DURATION CUE EDITOR
        # -------------------------------------------------------------
        self.card_cue = tk.Frame(p_inner, bg=PALETTE["bg_card"], bd=1, relief="solid")
        self.card_cue.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        self.card_cue.pack(fill="x", pady=(0, 10))

        cue_inner = tk.Frame(self.card_cue, bg=PALETTE["bg_card"], padx=12, pady=10)
        cue_inner.pack(fill="x")

        tk.Label(
            cue_inner, text="⏱️ Start Cue & Clip Duration",
            font=("Segoe UI", 10, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"]
        ).pack(anchor="w")

        tk.Label(
            cue_inner, text="Drop into song at specific beat for game & preview",
            font=("Segoe UI", 8), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]
        ).pack(anchor="w", pady=(0, 6))

        # Start Time Row
        row_st = tk.Frame(cue_inner, bg=PALETTE["bg_card"])
        row_st.pack(fill="x", pady=2)
        tk.Label(row_st, text="Start Time:", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"], width=12, anchor="w").pack(side="left")
        self.txt_start_time = tk.Entry(row_st, font=("Segoe UI", 10), width=9)
        self.txt_start_time.pack(side="left", padx=(0, 6))
        self.txt_start_time.insert(0, "00:00")
        tk.Label(row_st, text="(MM:SS or sec)", font=("Segoe UI", 8), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(side="left")

        # Duration Row
        row_dur = tk.Frame(cue_inner, bg=PALETTE["bg_card"])
        row_dur.pack(fill="x", pady=2)
        tk.Label(row_dur, text="Clip Duration:", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_main"], bg=PALETTE["bg_card"], width=12, anchor="w").pack(side="left")
        self.txt_duration = tk.Entry(row_dur, font=("Segoe UI", 10), width=9)
        self.txt_duration.pack(side="left", padx=(0, 6))
        self.txt_duration.insert(0, "0")
        tk.Label(row_dur, text="(sec, 0 = Full)", font=("Segoe UI", 8), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(side="left")

        # Action Buttons Row
        cue_btn_row = tk.Frame(cue_inner, bg=PALETTE["bg_card"])
        cue_btn_row.pack(fill="x", pady=(8, 4))

        self.btn_save_cue = tk.Button(
            cue_btn_row, text="💾 Save Cue",
            font=("Segoe UI", 9, "bold"), bg=PALETTE["primary"], fg=PALETTE["text_white"],
            activebackground=PALETTE["primary_hover"], activeforeground=PALETTE["text_white"],
            relief="flat", cursor="hand2", padx=10, pady=4,
            command=lambda: self.save_current_cue(show_alert=True)
        )
        self.btn_save_cue.pack(side="left", padx=(0, 6))

        self.btn_test_cue = tk.Button(
            cue_btn_row, text="▶️ Test from Start Cue",
            font=("Segoe UI", 9, "bold"), bg=PALETTE["emerald_light"], fg=PALETTE["emerald_dark"],
            activebackground=PALETTE["emerald"], activeforeground=PALETTE["text_white"],
            relief="flat", cursor="hand2", padx=10, pady=4,
            command=self.test_start_cue
        )
        self.btn_test_cue.pack(side="left", fill="x", expand=True)

        self.lbl_cue_feedback = tk.Label(
            cue_inner, text="", font=("Segoe UI", 8, "bold"),
            fg=PALETTE["emerald_dark"], bg=PALETTE["bg_card"]
        )
        self.lbl_cue_feedback.pack(anchor="w", pady=(2, 0))

        # Animated Mini-Equalizer Canvas (50px)
        tk.Label(p_inner, text="Live Resonance:", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"]).pack(anchor="w", pady=(0, 2))
        self.canvas_eq = tk.Canvas(
            p_inner, width=350, height=50,
            bg=PALETTE["bg_card_alt"], highlightthickness=1,
            highlightbackground=PALETTE["border"]
        )
        self.canvas_eq.pack(fill="x", pady=(0, 10))
        self._draw_equalizer_bars()

        # Playback Preview Controls
        deck_ctrls = tk.Frame(p_inner, bg=PALETTE["bg_card"])
        deck_ctrls.pack(fill="x", pady=(0, 8))

        self.btn_preview_play = tk.Button(
            deck_ctrls, text="▶️ Play from 00:00",
            font=("Segoe UI", 9, "bold"), bg=PALETTE["bg_card_alt"], fg=PALETTE["text_main"],
            relief="groove", cursor="hand2", padx=8, pady=5,
            command=self.play_preview_full
        )
        self.btn_preview_play.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_preview_stop = tk.Button(
            deck_ctrls, text="⏹ Stop",
            font=("Segoe UI", 9, "bold"), bg=PALETTE["bg_card_alt"], fg=PALETTE["coral"],
            relief="groove", cursor="hand2", padx=10, pady=5,
            command=self.stop_preview
        )
        self.btn_preview_stop.pack(side="right")

        # Single Audio File Link Button
        btn_link = tk.Button(
            p_inner, text="📁 Link / Replace Single File",
            font=("Segoe UI", 9, "bold"), bg=PALETTE["bg_card_alt"], fg=PALETTE["text_main"],
            relief="solid", bd=1, cursor="hand2", pady=6,
            command=self.link_replace_audio
        )
        btn_link.pack(fill="x", pady=(0, 4))

        lbl_hint = tk.Label(
            p_inner, text="Auditioning tracks here does not alter live game called numbers.",
            font=("Segoe UI", 8), fg=PALETTE["text_dim"], bg=PALETTE["bg_card"],
            wraplength=340, justify="center"
        )
        lbl_hint.pack(side="bottom", pady=2)

    def _update_folder_label(self):
        """Displays active songs directory path."""
        cfg = load_audio_config()
        fp = cfg.get("audio_folder_path")
        if fp and Path(fp).exists():
            try:
                rel = str(Path(fp).relative_to(BASE_DIR))
                disp = f"Active Folder: {rel}"
            except Exception:
                p = Path(fp)
                disp = f"Active Folder: {p.name}" if len(str(p)) > 30 else f"Active: {p}"
        else:
            disp = "Active Folder: songs/ (Default)"
        self.lbl_folder_path.config(text=disp)

    def choose_audio_folder(self):
        """Host selects custom directory containing tracks 1 to 90."""
        folder = filedialog.askdirectory(
            title="Select Custom Songs Folder (Arranged by track 1 to 90)"
        )
        if not folder:
            return

        cfg = load_audio_config()
        cfg["audio_folder_path"] = str(Path(folder).resolve())

        # Scan folder and map tracks by number 1-90
        matched = scan_audio_folder(folder)
        for num, fpath in matched.items():
            num_str = str(num)
            if num_str not in cfg["song_cues"]:
                cfg["song_cues"][num_str] = {}
            cfg["song_cues"][num_str]["file_path"] = fpath

        save_audio_config(cfg)
        self._update_folder_label()
        self.populate_catalog()
        if self.selected_song_id:
            self._update_preview_deck(self.selected_song_id)

        messagebox.showinfo(
            "Songs Folder Configured",
            f"Active Songs Folder set to:\n{folder}\n\n"
            f"Successfully matched and mapped {len(matched)} of 90 audio tracks."
        )

    def upload_catalog_file(self):
        """Host uploads Excel or CSV containing Start Times and song cues."""
        filepath = filedialog.askopenfilename(
            title="Upload Song Catalog (Excel / CSV)",
            filetypes=[
                ("Supported Catalogs", "*.csv *.xlsx *.xls"),
                ("CSV Files", "*.csv"),
                ("Excel Workbooks", "*.xlsx *.xls")
            ]
        )
        if not filepath:
            return

        count, errors = import_catalog_file(filepath)
        self.populate_catalog()
        if self.selected_song_id:
            self._update_preview_deck(self.selected_song_id)

        if count > 0:
            notice = f"Successfully updated start cues for {count} songs from:\n{Path(filepath).name}"
            if errors:
                notice += "\n\nNotices:\n" + "\n".join(errors[:3])
            messagebox.showinfo("Catalog Uploaded", notice)
        else:
            err_msg = "\n".join(errors[:4]) if errors else "No rows matched numbers 1 to 90."
            messagebox.showwarning("Upload Warning", f"Could not import song cues from file:\n{err_msg}")

    def save_current_cue(self, show_alert: bool = False):
        """Saves start time and clip duration for currently selected track."""
        if not self.selected_song_id:
            return

        st_val = self.txt_start_time.get().strip()
        dur_val = self.txt_duration.get().strip()

        start_sec = parse_time_to_seconds(st_val)
        dur_sec = parse_time_to_seconds(dur_val)

        cfg = load_audio_config()
        num_str = str(self.selected_song_id)
        if num_str not in cfg["song_cues"]:
            cfg["song_cues"][num_str] = {}

        cfg["song_cues"][num_str]["start_time"] = start_sec
        cfg["song_cues"][num_str]["duration"] = dur_sec
        save_audio_config(cfg)

        time_str = format_seconds_to_time(start_sec)
        dur_txt = f"{int(dur_sec)}s" if dur_sec > 0 else "Full"
        cue_display = f"{time_str} ({dur_txt})"

        # Update Treeview row in place
        try:
            vals = list(self.tree_catalog.item(num_str)["values"])
            if len(vals) == 7:
                vals[3] = cue_display
                self.tree_catalog.item(num_str, values=vals)
        except Exception:
            pass

        self.lbl_cue_feedback.config(
            text=f"✅ Saved! Start: {time_str} • Duration: {dur_txt}",
            fg=PALETTE["emerald_dark"]
        )

        if show_alert:
            messagebox.showinfo(
                "Cue Saved",
                f"Track #{self.selected_song_id:02d} cue updated:\n"
                f"Start Time: {time_str}\n"
                f"Duration: {dur_txt}"
            )

    def test_start_cue(self):
        """Immediately test playback from configured start cue with duration auto-stop."""
        if not self.selected_song_id or not HAS_AUDIO:
            return
        # Save current typed entries first so the audition reflects user edits
        self.save_current_cue(show_alert=False)
        self.play_preview(from_start_cue=True)

    def play_preview_full(self):
        """Play track from timestamp 00:00."""
        self.play_preview(from_start_cue=False)

    def play_preview(self, from_start_cue: bool = True):
        if not self.selected_song_id or not HAS_AUDIO:
            return

        # Cancel any previous preview auto-stop timer
        if self._preview_timer:
            try:
                self.after_cancel(self._preview_timer)
            except Exception:
                pass
            self._preview_timer = None

        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            except Exception:
                pass

        cue = get_song_cue(self.selected_song_id)
        audio_path = cue.get("file_path")
        if not audio_path or not os.path.exists(audio_path):
            audio_path = song_bank.find_audio_file(self.selected_song_id)
        if audio_path and os.path.exists(audio_path):
            try:
                pygame.mixer.music.load(audio_path)
                start_sec = cue.get("start_time", 0.0) if from_start_cue else 0.0
                duration = cue.get("duration", 0.0) if from_start_cue else 0.0

                try:
                    pygame.mixer.music.play(start=start_sec)
                except Exception:
                    pygame.mixer.music.play()

                self.is_preview_playing = True
                cue_str = f" from {format_seconds_to_time(start_sec)}" if start_sec > 0 else ""
                self.btn_preview_play.config(text="▶️ Playing...")
                self._step_equalizer()

                # Auto-stop preview after clip duration
                if duration > 0.0:
                    self._preview_timer = self.after(int(duration * 1000), self.stop_preview)
            except Exception as e:
                messagebox.showerror("Playback Error", f"Could not play audio: {e}")
        else:
            messagebox.showwarning(
                "Missing Audio",
                f"No audio file found for Track #{self.selected_song_id:02d}.\n"
                f"Use 'Set Songs Folder Path' or 'Link / Replace Single File' to map this track."
            )

    def stop_preview(self):
        if self._preview_timer:
            try:
                self.after_cancel(self._preview_timer)
            except Exception:
                pass
            self._preview_timer = None

        if HAS_AUDIO:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.is_preview_playing = False
        self.btn_preview_play.config(text="▶️ Play from 00:00")
        self.eq_bars = [4.0] * 14
        self._draw_equalizer_bars()

    def _draw_equalizer_bars(self):
        self.canvas_eq.delete("all")
        w = 350
        h = 50
        num_bars = len(self.eq_bars)
        bar_w = 16.0
        spacing = (w - (num_bars * bar_w)) / float(num_bars + 1)
        colors = [PALETTE["primary"], PALETTE["emerald"], PALETTE["amber"], PALETTE["coral"]]
        for i, bar_h in enumerate(self.eq_bars):
            bx = spacing + i * (bar_w + spacing)
            by = h - 4 - (bar_h * 0.8)
            col = colors[i % len(colors)]
            self.canvas_eq.create_rectangle(bx, by, bx + bar_w, h - 4, fill=col, outline="")
            self.canvas_eq.create_oval(bx, by - 2, bx + bar_w, by + 4, fill=col, outline="")

    def _step_equalizer(self):
        if not self.is_preview_playing:
            return
        if HAS_AUDIO:
            try:
                if not pygame.mixer.music.get_busy():
                    self.stop_preview()
                    return
            except Exception:
                pass

        self.eq_step += 1
        for i in range(len(self.eq_bars)):
            wave = math.sin(self.eq_step * 0.35 + i * 0.5)
            h = max(5.0, min(42.0, 22.0 + wave * 16.0 + random.uniform(-3, 5)))
            self.eq_bars[i] = h

        self._draw_equalizer_bars()
        self.after(50, self._step_equalizer)

    def set_filter(self, filter_key: str):
        self.active_filter = filter_key
        for k, btn in self.filter_buttons.items():
            if k == filter_key:
                btn.config(bg=PALETTE["primary"], fg=PALETTE["text_white"])
            else:
                btn.config(bg=PALETTE["bg_card_alt"], fg=PALETTE["text_muted"])
        self.populate_catalog()

    def _on_search_changed(self, event):
        self.search_query = self.txt_search.get().strip().lower()
        self.populate_catalog()

    def populate_catalog(self):
        for item in self.tree_catalog.get_children():
            self.tree_catalog.delete(item)

        cfg = load_audio_config()
        called_set = set(self.app.screen_live.called_numbers)
        total_ready = 0

        for num in range(1, 91):
            cue = get_song_cue(num, cfg)
            title = cue.get("title") or song_bank.get_song_title(num)
            song = song_bank.get_song(num)
            artist = song.get("artist", "") if song else ""
            col_idx = (song.get("column", 0) + 1) if song else 1

            pillar_name = "Satyam" if num <= 29 else ("Shivam" if num <= 59 else "Sundaram")
            pillar_display = f"{pillar_name} (Col {col_idx})"

            audio_file = cue.get("file_path")
            has_audio = bool(audio_file and os.path.exists(audio_file))
            if has_audio:
                total_ready += 1

            is_called = num in called_set

            # Pillar filter
            if self.active_filter == "satyam" and num > 29:
                continue
            if self.active_filter == "shivam" and (num < 30 or num > 59):
                continue
            if self.active_filter == "sundaram" and num < 60:
                continue
            if self.active_filter == "missing" and has_audio:
                continue

            # Search query
            if self.search_query:
                match_num = self.search_query in str(num) or self.search_query in f"#{num:02d}"
                match_title = self.search_query in title.lower()
                match_artist = self.search_query in artist.lower()
                if not (match_num or match_title or match_artist):
                    continue

            # Start cue formatting
            start_sec = cue.get("start_time", 0.0)
            dur_sec = cue.get("duration", 0.0)
            time_str = format_seconds_to_time(start_sec)
            if dur_sec > 0:
                cue_display = f"{time_str} ({int(dur_sec)}s)"
            elif start_sec > 0:
                cue_display = f"{time_str} (Full)"
            else:
                cue_display = "00:00 (Full)"

            # Path formatting
            if audio_file:
                try:
                    rel_path = str(Path(audio_file).relative_to(BASE_DIR))
                except Exception:
                    rel_path = Path(audio_file).name
            else:
                rel_path = f"songs/{num}.wav (missing)"

            f_status = "✅ Ready" if has_audio else "❌ Missing"
            g_status = "Called ✔" if is_called else "Pending ⏳"

            self.tree_catalog.insert(
                "", "end", iid=str(num),
                values=(f"#{num:02d}", pillar_display, title, cue_display, rel_path, f_status, g_status)
            )

        # Update summary badge
        if total_ready == 90:
            self.lbl_summary_badge.config(
                text="✅ 90/90 Audio Files Ready",
                bg=PALETTE["emerald_light"], fg=PALETTE["emerald_dark"]
            )
        else:
            self.lbl_summary_badge.config(
                text=f"⚠️ {total_ready}/90 Files Ready ({90 - total_ready} Missing)",
                bg=PALETTE["amber_light"], fg=PALETTE["amber_dark"]
            )

        # Select first available item if none selected
        children = self.tree_catalog.get_children()
        if children:
            target = str(self.selected_song_id) if str(self.selected_song_id) in children else children[0]
            self.tree_catalog.selection_set(target)
            self.tree_catalog.focus(target)
            self._update_preview_deck(int(target))

    def _on_tree_select(self, event):
        sel = self.tree_catalog.selection()
        if sel:
            try:
                num = int(sel[0])
                self._update_preview_deck(num)
            except Exception:
                pass

    def _update_preview_deck(self, num: int):
        self.selected_song_id = num
        cue = get_song_cue(num)
        title = cue.get("title") or song_bank.get_song_title(num)
        song = song_bank.get_song(num)
        artist = song.get("artist", "") if song else ""
        year = song.get("year", "") if song else ""
        col_idx = (song.get("column", 0) + 1) if song else 1

        pillar_name = "Satyam" if num <= 29 else ("Shivam" if num <= 59 else "Sundaram")

        self.lbl_deck_serial.config(text=f"Track #{num:02d}")
        self.lbl_deck_pillar.config(text=f" • {pillar_name} (Col {col_idx})")
        self.lbl_deck_title.config(text=title)

        sub = f"Artist: {artist}" if artist else "Bollywood Evergreen Hit"
        if year:
            sub += f" ({year})"
        self.lbl_deck_artist.config(text=sub)

        # Update cue inputs
        self.txt_start_time.delete(0, "end")
        self.txt_start_time.insert(0, format_seconds_to_time(cue.get("start_time", 0.0)))

        dur = cue.get("duration", 0.0)
        self.txt_duration.delete(0, "end")
        self.txt_duration.insert(0, str(int(dur)) if dur > 0 else "0")

        self.lbl_cue_feedback.config(text="")

        audio_file = cue.get("file_path")
        if audio_file and os.path.exists(audio_file):
            try:
                rel = str(Path(audio_file).relative_to(BASE_DIR))
            except Exception:
                rel = Path(audio_file).name
            self.lbl_deck_status.config(text="Status: ✅ Audio File Verified", fg=PALETTE["emerald_dark"])
            self.lbl_deck_path.config(text=f"Path: {rel}", fg=PALETTE["text_muted"])
            self.card_status.configure(highlightbackground=PALETTE["emerald"])
        else:
            self.lbl_deck_status.config(text="Status: ❌ Audio File Missing", fg=PALETTE["coral_dark"])
            self.lbl_deck_path.config(text=f"Expected: songs/{num}.wav or custom folder track", fg=PALETTE["coral"])
            self.card_status.configure(highlightbackground=PALETTE["coral"])

    def link_replace_audio(self):
        if not self.selected_song_id:
            return
        path = filedialog.askopenfilename(
            title=f"Select Audio File for Track #{self.selected_song_id:02d}",
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg *.m4a *.aac *.flac")]
        )
        if path:
            try:
                cfg = load_audio_config()
                num_str = str(self.selected_song_id)
                if num_str not in cfg["song_cues"]:
                    cfg["song_cues"][num_str] = {}
                cfg["song_cues"][num_str]["file_path"] = str(Path(path).resolve())
                save_audio_config(cfg)

                # Also update database & song_bank if available
                try:
                    database.update_audio_path(self.selected_song_id, str(path))
                    song_bank.sync_with_database()
                except Exception:
                    pass

                self.populate_catalog()
                self._update_preview_deck(self.selected_song_id)
                messagebox.showinfo(
                    "Asset Linked",
                    f"Audio file mapped successfully for Track #{self.selected_song_id:02d}:\n{Path(path).name}"
                )
            except Exception as e:
                messagebox.showerror("Error Linking File", f"Failed to link audio file: {e}")

    def rescan_directory(self):
        cfg = load_audio_config()
        folder = cfg.get("audio_folder_path") or str(SONGS_DIR.resolve())
        matched = scan_audio_folder(folder) if Path(folder).is_dir() else {}
        for num, fpath in matched.items():
            num_str = str(num)
            if num_str not in cfg["song_cues"]:
                cfg["song_cues"][num_str] = {}
            cfg["song_cues"][num_str]["file_path"] = fpath
        save_audio_config(cfg)

        try:
            song_bank.sync_with_database()
        except Exception:
            pass

        self._update_folder_label()
        self.populate_catalog()
        if self.selected_song_id:
            self._update_preview_deck(self.selected_song_id)

        ready_count = sum(1 for n in range(1, 91) if get_song_cue(n).get("file_path"))
        messagebox.showinfo("Directory Scanned", f"Scanned active directory:\n{folder}\n\n{ready_count} of 90 audio tracks ready.")

    def sync_game_status(self):
        """Updates Called/Pending statuses in the treeview without losing selection."""
        called_set = set(self.app.screen_live.called_numbers)
        for num_str in self.tree_catalog.get_children():
            try:
                num = int(num_str)
                vals = list(self.tree_catalog.item(num_str)["values"])
                if len(vals) == 7:
                    vals[6] = "Called ✔" if num in called_set else "Pending ⏳"
                    self.tree_catalog.item(num_str, values=vals)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# MAIN MULTI-SCREEN APPLICATION CONTAINER
# ---------------------------------------------------------------------------
class MusicalHousieApp(tk.Tk):
    """
    Main Tkinter application hub hosting custom top navigation bar
    and 6 high-frame-rate animated screens.
    """
    def __init__(self):
        super().__init__()
        self.title("Musical Housie (Tambola) — Offline Motion Graphics Suite")
        self.geometry("1380x880")
        self.minsize(1140, 760)
        self.configure(bg=PALETTE["bg_body"])

        # Top Navigation & Screen Switching Setup
        self._init_top_navbar()
        self._init_screens()

        # Keyboard shortcuts
        self.bind("<space>", self._on_space_pressed)

    def _init_top_navbar(self):
        nav_frame = tk.Frame(self, bg=PALETTE["bg_card"], bd=1, relief="solid")
        nav_frame.configure(highlightbackground=PALETTE["border"], highlightthickness=1)
        nav_frame.pack(fill="x", padx=16, pady=(12, 0))

        nav_inner = tk.Frame(nav_frame, bg=PALETTE["bg_card"], padx=14, pady=8)
        nav_inner.pack(fill="x")

        # Logo Title & Offline Tag
        tk.Label(nav_inner, text="🎵 MUSICAL HOUSIE", font=("Segoe UI", 14, "bold"), fg=PALETTE["primary"], bg=PALETTE["bg_card"]).pack(side="left", padx=(0, 10))

        lbl_off = tk.Label(nav_inner, text="🟢 OFFLINE MASTER STUDIO", font=("Segoe UI", 9, "bold"), fg=PALETTE["emerald_dark"], bg=PALETTE["emerald_light"], padx=8, pady=2)
        lbl_off.pack(side="left", padx=(0, 20))

        # 6 Tab Navigation Buttons
        self.tab_buttons: List[tk.Button] = []
        tabs_meta = [
            ("🎯 Live Stage", 0),
            ("🔮 3D Dot-Sphere", 1),
            ("🎰 Lucky Draw", 2),
            ("🔍 Claim Verifier", 3),
            ("🎫 Ticket Studio", 4),
            ("🎵 Audio Catalog", 5),
        ]

        pills_container = tk.Frame(nav_inner, bg=PALETTE["bg_card"])
        pills_container.pack(side="left")

        for label, idx in tabs_meta:
            btn = tk.Button(
                pills_container, text=label, font=("Segoe UI", 10, "bold"),
                bg=PALETTE["bg_card_alt"], fg=PALETTE["text_muted"],
                relief="flat", cursor="hand2", padx=12, pady=4,
                command=lambda i=idx: self.switch_tab(i)
            )
            btn.pack(side="left", padx=3)
            self.tab_buttons.append(btn)

        # Right Side Status & Reset
        self.lbl_global_session = tk.Label(
            nav_inner, text="Session: 0 / 90 Numbers Called",
            font=("Segoe UI", 9, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["bg_card_alt"],
            relief="solid", bd=1, padx=10, pady=3
        )
        self.lbl_global_session.pack(side="right", padx=(10, 0))

        btn_reset = tk.Button(
            nav_inner, text="Reset Game", font=("Segoe UI", 9, "bold"),
            bg=PALETTE["bg_card_alt"], fg=PALETTE["coral"], relief="groove",
            cursor="hand2", padx=10, pady=3,
            command=self._on_reset_clicked
        )
        btn_reset.pack(side="right")

    def _init_screens(self):
        self.container = tk.Frame(self, bg=PALETTE["bg_body"])
        self.container.pack(fill="both", expand=True)

        self.screen_live = LiveStageScreen(self.container, self)
        self.screen_sphere = DotSphereScreen(self.container, self)
        self.screen_lucky = LuckyDrawScreen(self.container, self)
        self.screen_verifier = ClaimVerifierScreen(self.container, self)
        self.screen_studio = TicketStudioScreen(self.container, self)
        self.screen_catalog = AudioCatalogScreen(self.container, self)

        self.screens = [
            self.screen_live,
            self.screen_sphere,
            self.screen_lucky,
            self.screen_verifier,
            self.screen_studio,
            self.screen_catalog
        ]

        self.active_tab_idx = 0
        self.switch_tab(0)

    def switch_tab(self, index: int):
        self.active_tab_idx = index

        # Highlight active pill
        for i, btn in enumerate(self.tab_buttons):
            if i == index:
                btn.config(bg=PALETTE["primary"], fg=PALETTE["text_white"])
            else:
                btn.config(bg=PALETTE["bg_card_alt"], fg=PALETTE["text_muted"])

        # Display selected screen & manage preview audio
        for i, scr in enumerate(self.screens):
            if i == index:
                scr.pack(fill="both", expand=True)
                if i == 1:
                    self.screen_sphere.start_loop()
                elif i == 5:
                    self.screen_catalog.sync_game_status()
                else:
                    self.screen_sphere.stop_loop()
            else:
                scr.pack_forget()

        if index != 5 and hasattr(self, "screen_catalog"):
            self.screen_catalog.stop_preview()

    def sync_number_called(self, num: int):
        called = self.screen_live.called_numbers
        self.lbl_global_session.config(text=f"Session: {len(called)} / 90 Numbers Called (Last: #{num:02d})")
        self.screen_sphere.sync_track_info(num)
        self.screen_lucky.called_numbers_ref = called
        self.screen_verifier.called_numbers_ref = called
        if self.screen_verifier.current_tickets:
            self.screen_verifier.render_ticket_staggered()
        if hasattr(self, "screen_catalog"):
            self.screen_catalog.sync_game_status()

    def sync_reset(self):
        self.lbl_global_session.config(text="Session: 0 / 90 Numbers Called")
        self.screen_lucky.called_numbers_ref = []
        self.screen_verifier.called_numbers_ref = []
        if hasattr(self, "screen_catalog"):
            self.screen_catalog.sync_game_status()

    def sync_tickets_loaded(self, tickets: List[Dict[str, Any]]):
        self.screen_lucky.registered_tickets_ref = tickets

    def sync_batch_generated(self, html_path: str):
        self.screen_verifier.reload_batch_registries()

    def _on_reset_clicked(self):
        self.screen_live.reset_game()

    def _on_space_pressed(self, event):
        if self.active_tab_idx == 0:
            self.screen_live.draw_next_track()


def main():
    if not TKINTER_AVAILABLE:
        print("Notice: Tkinter GUI environment is not available in headless runtime.")
        sys.exit(1)
    app = MusicalHousieApp()
    app.mainloop()


if __name__ == "__main__":
    main()

