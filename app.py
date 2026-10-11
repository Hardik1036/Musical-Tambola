"""
app.py / player_app.py - Unified Desktop Studio for Musical Tambola
Multi-tab dashboard using Tkinter ttk.Notebook providing:
Tab 1: Ticket Generator & Template Studio (PRD 2.2) with custom batch naming,
       tickets_archive/ systematic storage, and quick folder/browser actions.
Tab 2: Game Host & Caller Dashboard (PRD 2.3 & 2.4)
Tab 3: Claim Verifier (PRD 2.5) with game-day batch archive loading.
"""
import os
import sys
import json
import random
import webbrowser
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# Base directories
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import TICKETS_ARCHIVE_DIR
import song_bank
import database
from generator.generate_housie_tickets import generate_housie_tickets, sanitize_batch_name

# Initialize audio
try:
    import pygame
    pygame.mixer.init()
    HAS_AUDIO = True
except Exception as e:
    HAS_AUDIO = False
    print(f"Warning: Pygame mixer could not be initialized: {e}")

# Color Scheme
THEME = {
    "bg_dark": "#0B1120",
    "bg_card": "#1E293B",
    "bg_card_hover": "#334155",
    "bg_subtle": "#0F172A",
    "border": "#334155",
    "crimson": "#E11D48",
    "crimson_hover": "#BE123C",
    "gold": "#F59E0B",
    "gold_hover": "#D97706",
    "emerald": "#10B981",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
}


class MusicalTambolaStudio(tk.Tk):
    """Unified Musical Tambola Desktop Application."""

    def __init__(self):
        super().__init__()
        self.title("🎶 Musical Tambola — Host Studio & Archive Generator")
        self.geometry("1280x880")
        self.minsize(1050, 720)
        self.configure(bg=THEME["bg_dark"])

        # State
        self.current_template_path: Optional[str] = None
        self.template_thumb_img: Optional[ImageTk.PhotoImage] = None
        self.last_generated_html: Optional[str] = None
        self.session_id: str = ""
        self.called_numbers: List[int] = []
        self.current_song_id: Optional[int] = None
        self.current_playing_id: Optional[int] = None
        self.auto_play: bool = True

        # Archive state for Claim Verifier
        self.loaded_archive_name: Optional[str] = None
        self.loaded_archive_tickets: Dict[str, Dict[str, Any]] = {}

        # Database initialization
        database.init_db()
        database.seed_default_songs()
        self.session_id = database.get_or_create_active_session()
        self.called_numbers = database.get_called_numbers(self.session_id)

        self._setup_styles()
        self._build_ui()
        self._load_default_template()
        self._refresh_master_board()
        self._refresh_archive_batch_dropdown()

    def _setup_styles(self):
        """Configure ttk styling for tabs, buttons, and frames."""
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure(
            "TNotebook",
            background=THEME["bg_dark"],
            borderwidth=0
        )
        self.style.configure(
            "TNotebook.Tab",
            background=THEME["bg_card"],
            foreground=THEME["text_secondary"],
            font=("Segoe UI", 11, "bold"),
            padding=[20, 10],
            borderwidth=0
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", THEME["crimson"]), ("active", THEME["bg_card_hover"])],
            foreground=[("selected", "#FFFFFF"), ("active", "#FFFFFF")]
        )

        self.style.configure("TFrame", background=THEME["bg_dark"])
        self.style.configure("Card.TFrame", background=THEME["bg_card"])
        self.style.configure("Subtle.TFrame", background=THEME["bg_subtle"])

        self.style.configure(
            "Primary.TButton",
            background=THEME["crimson"],
            foreground="white",
            font=("Segoe UI", 11, "bold"),
            borderwidth=0,
            padding=[14, 8]
        )
        self.style.map(
            "Primary.TButton",
            background=[("active", THEME["crimson_hover"])]
        )

        self.style.configure(
            "Gold.TButton",
            background=THEME["gold"],
            foreground="#0F172A",
            font=("Segoe UI", 11, "bold"),
            borderwidth=0,
            padding=[14, 8]
        )
        self.style.map(
            "Gold.TButton",
            background=[("active", THEME["gold_hover"])]
        )

    def _build_ui(self):
        # Top Header Bar
        header = tk.Frame(self, bg="#1E1B4B", height=60, padx=20, pady=10)
        header.pack(fill="x")

        lbl_logo = tk.Label(
            header,
            text="🎶 MUSICAL TAMBOLA HOST STUDIO",
            font=("Segoe UI", 16, "bold"),
            bg="#1E1B4B",
            fg=THEME["gold"]
        )
        lbl_logo.pack(side="left")

        lbl_sub = tk.Label(
            header,
            text="Professional Live Host, Template Studio & Archive System",
            font=("Segoe UI", 10),
            bg="#1E1B4B",
            fg=THEME["text_secondary"]
        )
        lbl_sub.pack(side="left", padx=15)

        lbl_badge = tk.Label(
            header,
            text="● OFFLINE ARCHIVE READY",
            font=("Segoe UI", 9, "bold"),
            bg="#0F172A",
            fg=THEME["emerald"],
            padx=10,
            pady=4,
            relief="solid",
            bd=1
        )
        lbl_badge.pack(side="right")

        # Tab Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=8)

        # Tab 1: Ticket Generator & Template Studio
        self.tab_generator = tk.Frame(self.notebook, bg=THEME["bg_dark"])
        self.notebook.add(self.tab_generator, text="🎫 Ticket Generator & Template Studio")
        self._build_tab_generator()

        # Tab 2: Game Host & Caller Dashboard
        self.tab_host = tk.Frame(self.notebook, bg=THEME["bg_dark"])
        self.notebook.add(self.tab_host, text="🎲 Game Host & Caller Dashboard")
        self._build_tab_host()

        # Tab 3: Claim Verifier
        self.tab_verifier = tk.Frame(self.notebook, bg=THEME["bg_dark"])
        self.notebook.add(self.tab_verifier, text="🔍 Claim Verifier")
        self._build_tab_verifier()

    # ==========================================
    # TAB 1: TICKET GENERATOR & TEMPLATE STUDIO
    # ==========================================
    def _build_tab_generator(self):
        container = tk.Frame(self.tab_generator, bg=THEME["bg_dark"], padx=15, pady=12)
        container.pack(fill="both", expand=True)

        # Left Column: Configuration & Controls
        left_panel = tk.Frame(container, bg=THEME["bg_card"], padx=18, pady=16, relief="solid", bd=1)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        lbl_sec1 = tk.Label(
            left_panel,
            text="1. BACKGROUND TEMPLATE SELECTION",
            font=("Segoe UI", 11, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["gold"]
        )
        lbl_sec1.pack(anchor="w", pady=(0, 6))

        btn_select_tpl = tk.Button(
            left_panel,
            text="📁 Upload / Select Background Template (.png, .jpg)",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_subtle"],
            fg=THEME["text_primary"],
            activebackground=THEME["bg_card_hover"],
            activeforeground="white",
            relief="groove",
            bd=1,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._select_template_file
        )
        btn_select_tpl.pack(fill="x", pady=4)

        self.lbl_tpl_path = tk.Label(
            left_panel,
            text="Using default festive template",
            font=("Segoe UI", 9),
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"],
            wraplength=480,
            justify="left"
        )
        self.lbl_tpl_path.pack(anchor="w", pady=2)

        # Separator
        ttk.Separator(left_panel, orient="horizontal").pack(fill="x", pady=10)

        lbl_sec2 = tk.Label(
            left_panel,
            text="2. BATCH & STORAGE CONFIGURATION",
            font=("Segoe UI", 11, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["gold"]
        )
        lbl_sec2.pack(anchor="w", pady=(0, 8))

        # Custom Batch / Event Name
        row_batch = tk.Frame(left_panel, bg=THEME["bg_card"])
        row_batch.pack(fill="x", pady=4)
        tk.Label(
            row_batch,
            text="Batch / Event Name:",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["text_primary"]
        ).pack(side="left")

        default_name = datetime.now().strftime("musical_housie_tickets_%Y%m%d")
        self.txt_batch_name = tk.Entry(
            row_batch,
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_subtle"],
            fg=THEME["gold"],
            insertbackground="white"
        )
        self.txt_batch_name.insert(0, default_name)
        self.txt_batch_name.pack(side="right", fill="x", expand=True, padx=(10, 0))

        lbl_archive_hint = tk.Label(
            left_panel,
            text="Stored in tickets_archive/<Batch_Name>.html and _registry.json for game day",
            font=("Segoe UI", 8),
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"]
        )
        lbl_archive_hint.pack(anchor="w", pady=(0, 6))

        # Number of sheets
        row_sheets = tk.Frame(left_panel, bg=THEME["bg_card"])
        row_sheets.pack(fill="x", pady=4)
        tk.Label(
            row_sheets,
            text="Number of Sheets / Players:",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["text_primary"]
        ).pack(side="left")

        self.spin_sheets = tk.Spinbox(
            row_sheets,
            from_=1,
            to=1000,
            font=("Segoe UI", 10),
            width=8,
            justify="center"
        )
        self.spin_sheets.delete(0, "end")
        self.spin_sheets.insert(0, "100")  # Default: 100 sheets
        self.spin_sheets.pack(side="right")

        # Format selector
        row_format = tk.Frame(left_panel, bg=THEME["bg_card"])
        row_format.pack(fill="x", pady=4)
        tk.Label(
            row_format,
            text="Ticket Format:",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["text_primary"]
        ).pack(side="left")

        self.var_format = tk.StringVar(value="2-Strip per Page (Combined Single Person)")
        self.combo_format = ttk.Combobox(
            row_format,
            textvariable=self.var_format,
            values=[
                "2-Strip per Page (Combined Single Person)",
                "1-Strip per Page"
            ],
            state="readonly",
            width=36
        )
        self.combo_format.pack(side="right")

        # Participant Slots Checkbox
        self.var_slots = tk.BooleanVar(value=True)
        chk_slots = tk.Checkbutton(
            left_panel,
            text="Include Participant Name & Mobile Slots in Overlay",
            variable=self.var_slots,
            font=("Segoe UI", 10),
            bg=THEME["bg_card"],
            fg=THEME["text_primary"],
            selectcolor=THEME["bg_subtle"],
            activebackground=THEME["bg_card"]
        )
        chk_slots.pack(anchor="w", pady=6)

        # Action Buttons
        ttk.Separator(left_panel, orient="horizontal").pack(fill="x", pady=8)

        btn_gen = tk.Button(
            left_panel,
            text="✨ GENERATE & ARCHIVE HOUSIE TICKETS",
            font=("Segoe UI", 11, "bold"),
            bg=THEME["crimson"],
            fg="white",
            activebackground=THEME["crimson_hover"],
            activeforeground="white",
            relief="flat",
            pady=10,
            cursor="hand2",
            command=self._generate_tickets
        )
        btn_gen.pack(fill="x", pady=4)

        row_quick_btns = tk.Frame(left_panel, bg=THEME["bg_card"])
        row_quick_btns.pack(fill="x", pady=4)

        btn_open_folder = tk.Button(
            row_quick_btns,
            text="📂 Open Tickets Folder",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_subtle"],
            fg=THEME["text_primary"],
            relief="solid",
            bd=1,
            pady=7,
            cursor="hand2",
            command=self._open_tickets_folder
        )
        btn_open_folder.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_preview = tk.Button(
            row_quick_btns,
            text="🌐 Open in Browser",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["gold"],
            fg="#0F172A",
            activebackground=THEME["gold_hover"],
            relief="flat",
            pady=7,
            cursor="hand2",
            command=self._preview_in_browser
        )
        btn_preview.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Right Column: Template Thumbnail Preview & Resolution
        right_panel = tk.Frame(container, bg=THEME["bg_card"], padx=18, pady=16, relief="solid", bd=1)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))

        lbl_sec3 = tk.Label(
            right_panel,
            text="TEMPLATE PREVIEW & RESOLUTION",
            font=("Segoe UI", 11, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["gold"]
        )
        lbl_sec3.pack(anchor="w", pady=(0, 6))

        self.lbl_resolution = tk.Label(
            right_panel,
            text="Resolution: None detected",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["emerald"]
        )
        self.lbl_resolution.pack(anchor="w", pady=(0, 6))

        self.canvas_preview = tk.Canvas(
            right_panel,
            bg=THEME["bg_subtle"],
            bd=1,
            relief="solid",
            highlightthickness=0
        )
        self.canvas_preview.pack(fill="both", expand=True, pady=4)

    def _load_default_template(self):
        """Auto-load default festive template if present."""
        candidates = [
            BASE_DIR / "generator" / "ticket_template.png",
            BASE_DIR / "assets" / "branding" / "Festive_Musical_Housie_Template.png",
        ]
        for c in candidates:
            if c.is_file():
                self._update_template_preview(str(c))
                break

    def _select_template_file(self):
        """Prompt user to select a template image."""
        selected = filedialog.askopenfilename(
            title="Select Ticket Background Template",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.webp"),
                ("All files", "*.*")
            ],
            initialdir=str(BASE_DIR)
        )
        if selected:
            self._update_template_preview(selected)

    def _update_template_preview(self, file_path: str):
        """Load image, display resolution, and render thumbnail preview."""
        p = Path(file_path)
        if not p.is_file():
            messagebox.showerror("Invalid File", f"Template file does not exist:\n{file_path}")
            return

        try:
            with Image.open(p) as img:
                w, h = img.size
                self.current_template_path = str(p.resolve())
                self.lbl_tpl_path.config(text=f"Template: {p.name}\nPath: {self.current_template_path}")
                self.lbl_resolution.config(text=f"Resolution: {w} × {h} px  •  Format: {img.format}")

                thumb = img.copy()
                thumb.thumbnail((480, 320), Image.Resampling.LANCZOS)
                self.template_thumb_img = ImageTk.PhotoImage(thumb)

                self.canvas_preview.delete("all")
                cw = self.canvas_preview.winfo_width()
                ch = self.canvas_preview.winfo_height()
                if cw < 50:
                    cw = 480
                if ch < 50:
                    ch = 320
                self.canvas_preview.create_image(
                    cw // 2,
                    ch // 2,
                    anchor="center",
                    image=self.template_thumb_img
                )
        except Exception as e:
            messagebox.showerror("Image Load Error", f"Failed to load image preview:\n{e}")

    def _open_tickets_folder(self):
        """Open tickets_archive directory in system file explorer."""
        folder = str(TICKETS_ARCHIVE_DIR)
        TICKETS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == 'nt':
                os.startfile(folder)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', folder])
            else:
                subprocess.Popen(['xdg-open', folder])
        except Exception as e:
            messagebox.showerror("Folder Error", f"Could not open tickets archive folder:\n{e}")

    def _generate_tickets(self):
        """Trigger generation engine and save systematically to tickets_archive/."""
        try:
            sheets = int(self.spin_sheets.get().strip())
            if sheets < 1 or sheets > 2000:
                raise ValueError("Number of sheets must be between 1 and 2000.")
        except Exception as e:
            messagebox.showerror("Input Error", f"Invalid number of sheets: {e}")
            return

        fmt = "2-strip" if "2-Strip" in self.var_format.get() else "1-strip"
        show_slots = self.var_slots.get()
        raw_name = self.txt_batch_name.get().strip()
        clean_batch = sanitize_batch_name(raw_name)

        try:
            output_file = generate_housie_tickets(
                num_sheets=sheets,
                format_mode=fmt,
                template_path=self.current_template_path,
                show_participant_slots=show_slots,
                batch_name=clean_batch
            )
            self.last_generated_html = output_file

            # Refresh claim verifier archives dropdown
            self._refresh_archive_batch_dropdown()
            self._refresh_verifier_ticket_list()

            archive_html = TICKETS_ARCHIVE_DIR / f"{clean_batch}.html"
            archive_json = TICKETS_ARCHIVE_DIR / f"{clean_batch}_registry.json"

            messagebox.showinfo(
                "Archive Generation Success",
                f"Successfully generated and archived {sheets} {fmt.upper()} sheets!\n\n"
                f"📁 Dedicated Archive Storage:\n"
                f"• Printable Document: tickets_archive/{clean_batch}.html\n"
                f"• Layout Registry: tickets_archive/{clean_batch}_registry.json\n\n"
                f"Click 'Open in Browser' to preview or print."
            )
        except Exception as e:
            messagebox.showerror("Generation Failed", f"An error occurred during ticket generation:\n{e}")

    def _preview_in_browser(self):
        """Open generated HTML file in default browser with error handling."""
        target = None
        if self.last_generated_html and Path(self.last_generated_html).is_file():
            target = Path(self.last_generated_html)
        else:
            # Check for current batch name or fallback to most recent file in tickets_archive
            raw_name = self.txt_batch_name.get().strip()
            clean_batch = sanitize_batch_name(raw_name)
            cand = TICKETS_ARCHIVE_DIR / f"{clean_batch}.html"
            if cand.is_file():
                target = cand
            else:
                html_files = sorted(TICKETS_ARCHIVE_DIR.glob("*.html"), key=os.path.getmtime, reverse=True)
                if html_files:
                    target = html_files[0]
                else:
                    compat = BASE_DIR / "generator" / "housie_tickets_output.html"
                    if compat.is_file():
                        target = compat

        if not target or not target.is_file():
            messagebox.showwarning(
                "No Generated File",
                "Please click 'Generate & Archive Housie Tickets' first before previewing."
            )
            return

        try:
            uri = target.resolve().as_uri()
            webbrowser.open_new_tab(uri)
        except Exception as e:
            messagebox.showerror("Browser Error", f"Could not launch browser:\n{e}")

    # ==========================================
    # TAB 2: GAME HOST & CALLER DASHBOARD
    # ==========================================
    def _build_tab_host(self):
        container = tk.Frame(self.tab_host, bg=THEME["bg_dark"], padx=15, pady=10)
        container.pack(fill="both", expand=True)

        # Top Control Ribbon: Current Number, Call Button, Audio Controls
        top_ribbon = tk.Frame(container, bg=THEME["bg_card"], padx=15, pady=12, relief="solid", bd=1)
        top_ribbon.pack(fill="x", pady=(0, 10))

        # Current Song Display Box
        box_current = tk.Frame(top_ribbon, bg=THEME["bg_subtle"], padx=15, pady=8, relief="solid", bd=1)
        box_current.pack(side="left")

        self.lbl_current_num = tk.Label(
            box_current,
            text="--",
            font=("Segoe UI", 36, "bold"),
            bg=THEME["bg_subtle"],
            fg=THEME["gold"]
        )
        self.lbl_current_num.pack(side="left", padx=(0, 15))

        box_meta = tk.Frame(box_current, bg=THEME["bg_subtle"])
        box_meta.pack(side="left")
        self.lbl_current_title = tk.Label(
            box_meta,
            text="Ready to Start Live Game",
            font=("Segoe UI", 13, "bold"),
            bg=THEME["bg_subtle"],
            fg=THEME["text_primary"],
            anchor="w"
        )
        self.lbl_current_title.pack(anchor="w")

        self.lbl_current_info = tk.Label(
            box_meta,
            text="Press 'Draw Next Song' to pick randomly without replacement (1-90)",
            font=("Segoe UI", 9),
            bg=THEME["bg_subtle"],
            fg=THEME["text_secondary"],
            anchor="w"
        )
        self.lbl_current_info.pack(anchor="w")

        # Caller Draw & Undo Buttons
        box_draw_actions = tk.Frame(top_ribbon, bg=THEME["bg_card"])
        box_draw_actions.pack(side="left", padx=20)

        btn_draw = tk.Button(
            box_draw_actions,
            text="🎲 DRAW NEXT SONG",
            font=("Segoe UI", 12, "bold"),
            bg=THEME["crimson"],
            fg="white",
            activebackground=THEME["crimson_hover"],
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._draw_next_number
        )
        btn_draw.pack(side="left", padx=4)

        btn_undo = tk.Button(
            box_draw_actions,
            text="↩ Undo Last",
            font=("Segoe UI", 10),
            bg=THEME["bg_subtle"],
            fg=THEME["text_secondary"],
            activebackground=THEME["bg_card_hover"],
            activeforeground="white",
            relief="solid",
            bd=1,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._undo_last_call
        )
        btn_undo.pack(side="left", padx=4)

        # Audio Playback Controls
        box_audio = tk.Frame(top_ribbon, bg=THEME["bg_card"])
        box_audio.pack(side="right")

        btn_play = tk.Button(
            box_audio,
            text="▶ Play",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["emerald"],
            fg="white",
            relief="flat",
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._play_current_song
        )
        btn_play.pack(side="left", padx=3)

        btn_stop = tk.Button(
            box_audio,
            text="⏹ Stop",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_subtle"],
            fg=THEME["text_primary"],
            relief="solid",
            bd=1,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._stop_audio
        )
        btn_stop.pack(side="left", padx=3)

        btn_replay = tk.Button(
            box_audio,
            text="🔄 Replay",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["gold"],
            fg="#0F172A",
            relief="flat",
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._replay_current_song
        )
        btn_replay.pack(side="left", padx=3)

        # Main Layout: 10x9 Master Calling Board + Lucky Draw Sidebar
        mid_container = tk.Frame(container, bg=THEME["bg_dark"])
        mid_container.pack(fill="both", expand=True)

        # 10x9 Master Calling Board
        board_frame = tk.Frame(mid_container, bg=THEME["bg_card"], padx=10, pady=10, relief="solid", bd=1)
        board_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        lbl_board_hdr = tk.Label(
            board_frame,
            text="10×9 MASTER CALLING BOARD (NUMBERS 1 TO 90)",
            font=("Segoe UI", 11, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["gold"]
        )
        lbl_board_hdr.pack(anchor="w", pady=(0, 6))

        grid_frame = tk.Frame(board_frame, bg=THEME["bg_card"])
        grid_frame.pack(fill="both", expand=True)

        self.board_cells: Dict[int, tk.Label] = {}
        for num in range(1, 91):
            row = (num - 1) // 10
            col = (num - 1) % 10

            lbl = tk.Label(
                grid_frame,
                text=str(num),
                font=("Segoe UI", 11, "bold"),
                bg=THEME["bg_subtle"],
                fg=THEME["text_secondary"],
                relief="solid",
                bd=1,
                cursor="hand2"
            )
            lbl.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
            lbl.bind("<Button-1>", lambda e, n=num: self._on_cell_clicked(n))
            self.board_cells[num] = lbl

        for r in range(9):
            grid_frame.rowconfigure(r, weight=1)
        for c in range(10):
            grid_frame.columnconfigure(c, weight=1)

        # Lucky Draw Sidebar
        lucky_panel = tk.Frame(mid_container, bg=THEME["bg_card"], width=320, padx=15, pady=15, relief="solid", bd=1)
        lucky_panel.pack(side="right", fill="y")
        lucky_panel.pack_propagate(False)

        lbl_lucky_title = tk.Label(
            lucky_panel,
            text="🎁 LUCKY DRAW & TIE-BREAKER",
            font=("Segoe UI", 11, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["gold"]
        )
        lbl_lucky_title.pack(anchor="w", pady=(0, 8))

        tk.Label(
            lucky_panel,
            text="Number of Winners:",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["text_primary"]
        ).pack(anchor="w", pady=(4, 2))

        self.spin_lucky_winners = tk.Spinbox(lucky_panel, from_=1, to=10, width=6, font=("Segoe UI", 10), justify="center")
        self.spin_lucky_winners.delete(0, "end")
        self.spin_lucky_winners.insert(0, "1")
        self.spin_lucky_winners.pack(anchor="w", pady=(0, 8))

        tk.Label(
            lucky_panel,
            text="Winner Pool:",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["text_primary"]
        ).pack(anchor="w", pady=(4, 2))

        self.combo_lucky_pool = ttk.Combobox(
            lucky_panel,
            values=["Active Called Songs (1-90)", "Registered Ticket IDs", "All 1-90 Numbers"],
            state="readonly"
        )
        self.combo_lucky_pool.current(0)
        self.combo_lucky_pool.pack(fill="x", pady=(0, 12))

        btn_spin = tk.Button(
            lucky_panel,
            text="🎉 DRAW WINNERS",
            font=("Segoe UI", 11, "bold"),
            bg=THEME["gold"],
            fg="#0F172A",
            relief="flat",
            pady=8,
            cursor="hand2",
            command=self._spin_lucky_draw
        )
        btn_spin.pack(fill="x", pady=4)

        self.lbl_lucky_result = tk.Label(
            lucky_panel,
            text="Winners will appear here.",
            font=("Segoe UI", 10),
            bg=THEME["bg_subtle"],
            fg=THEME["text_secondary"],
            wraplength=280,
            justify="center",
            relief="solid",
            bd=1,
            padx=10,
            pady=15
        )
        self.lbl_lucky_result.pack(fill="both", expand=True, pady=10)

    def _refresh_master_board(self):
        """Update 10x9 board colors based on called numbers and active song."""
        for num, lbl in self.board_cells.items():
            if num == self.current_song_id:
                lbl.config(bg=THEME["gold"], fg="#0F172A")
            elif num in self.called_numbers:
                lbl.config(bg=THEME["crimson"], fg="#FFFFFF")
            else:
                lbl.config(bg=THEME["bg_subtle"], fg=THEME["text_secondary"])

    def _draw_next_number(self):
        """Pick next random uncalled number without replacement."""
        uncalled = [n for n in range(1, 91) if n not in self.called_numbers]
        if not uncalled:
            messagebox.showinfo("Game Over", "All 90 numbers have been called!")
            return

        picked = random.choice(uncalled)
        self._call_number(picked)

    def _call_number(self, num: int):
        """Call a specific number and trigger audio."""
        if num not in self.called_numbers:
            database.call_number(self.session_id, num)
            self.called_numbers.append(num)

        self.current_song_id = num
        song_meta = song_bank.get_song(num)
        title = song_meta["title"] if song_meta else f"Song #{num}"
        artist = f"{song_meta.get('artist', '')} ({song_meta.get('year', '')})" if song_meta else ""

        self.lbl_current_num.config(text=f"{num:02d}")
        self.lbl_current_title.config(text=f"#{num} — {title}")
        self.lbl_current_info.config(text=artist)

        self._refresh_master_board()
        if self.auto_play:
            self._play_song_id(num)

    def _undo_last_call(self):
        """Undo last called number."""
        if not self.called_numbers:
            return
        last = database.undo_last_call(self.session_id)
        if last:
            if last in self.called_numbers:
                self.called_numbers.remove(last)
            self.current_song_id = self.called_numbers[-1] if self.called_numbers else None
            self._stop_audio()

            if self.current_song_id:
                sm = song_bank.get_song(self.current_song_id)
                self.lbl_current_num.config(text=f"{self.current_song_id:02d}")
                self.lbl_current_title.config(text=f"#{self.current_song_id} — {sm['title'] if sm else ''}")
            else:
                self.lbl_current_num.config(text="--")
                self.lbl_current_title.config(text="Ready to Start Live Game")
                self.lbl_current_info.config(text="")

            self._refresh_master_board()

    def _on_cell_clicked(self, num: int):
        """Call or preview cell clicked on the master board."""
        self._call_number(num)

    def _play_song_id(self, song_id: int):
        """Resolve and play audio file for song_id."""
        if not HAS_AUDIO:
            return

        audio_path = song_bank.find_audio_file(song_id, base_dir=BASE_DIR)
        if not audio_path or not Path(audio_path).is_file():
            print(f"Notice: Audio file for song #{song_id} not found in songs/ or assets/songs/")
            return

        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            self.current_playing_id = song_id
        except Exception as e:
            print(f"Audio playback error for #{song_id}: {e}")

    def _play_current_song(self):
        if self.current_song_id:
            self._play_song_id(self.current_song_id)

    def _stop_audio(self):
        if HAS_AUDIO:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def _replay_current_song(self):
        self._stop_audio()
        self._play_current_song()

    def _spin_lucky_draw(self):
        """Raffle selector for lucky draw winners."""
        pool_type = self.combo_lucky_pool.get()
        try:
            num_winners = int(self.spin_lucky_winners.get())
        except ValueError:
            num_winners = 1

        candidates = []
        if "Called" in pool_type:
            candidates = [f"Song #{n} ({song_bank.get_song_title(n)})" for n in self.called_numbers]
        elif "Ticket" in pool_type:
            # Use active tickets or loaded batch tickets
            if self.loaded_archive_tickets:
                candidates = [f"Ticket #{t['ticket_id']}" for t in self.loaded_archive_tickets.values()]
            else:
                all_tickets = database.get_all_tickets()
                candidates = [f"Ticket #{t['ticket_id']}" for t in all_tickets]
        else:
            candidates = [f"Song #{n} ({song_bank.get_song_title(n)})" for n in range(1, 91)]

        if not candidates:
            self.lbl_lucky_result.config(text="Pool is empty! Call songs or generate tickets first.")
            return

        winners = random.sample(candidates, min(num_winners, len(candidates)))
        result_text = "🏆 WINNERS:\n\n" + "\n".join(f"• {w}" for w in winners)
        self.lbl_lucky_result.config(text=result_text, fg=THEME["emerald"])

    # ==========================================
    # TAB 3: CLAIM VERIFIER & BATCH LOADER
    # ==========================================
    def _build_tab_verifier(self):
        container = tk.Frame(self.tab_verifier, bg=THEME["bg_dark"], padx=20, pady=12)
        container.pack(fill="both", expand=True)

        # Batch Selection Bar
        batch_bar = tk.Frame(container, bg=THEME["bg_card"], padx=15, pady=8, relief="solid", bd=1)
        batch_bar.pack(fill="x", pady=(0, 8))

        tk.Label(
            batch_bar,
            text="📁 Game Day Ticket Batch Archive:",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["gold"]
        ).pack(side="left", padx=(0, 8))

        self.combo_batch_archive = ttk.Combobox(batch_bar, state="readonly", width=42)
        self.combo_batch_archive.pack(side="left", padx=4)
        self.combo_batch_archive.bind("<<ComboboxSelected>>", self._on_batch_archive_selected)

        btn_refresh_batches = tk.Button(
            batch_bar,
            text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=THEME["bg_subtle"],
            fg=THEME["text_secondary"],
            relief="solid",
            bd=1,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._refresh_archive_batch_dropdown
        )
        btn_refresh_batches.pack(side="left", padx=6)

        self.lbl_batch_status = tk.Label(
            batch_bar,
            text="Source: Active SQLite Database",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["emerald"]
        )
        self.lbl_batch_status.pack(side="right")

        # Ticket ID Lookup Bar
        top_bar = tk.Frame(container, bg=THEME["bg_card"], padx=15, pady=10, relief="solid", bd=1)
        top_bar.pack(fill="x", pady=(0, 10))

        tk.Label(
            top_bar,
            text="Ticket ID to Verify:",
            font=("Segoe UI", 11, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["gold"]
        ).pack(side="left", padx=(0, 8))

        self.txt_verify_id = tk.Entry(top_bar, font=("Segoe UI", 11), width=10, justify="center")
        self.txt_verify_id.insert(0, "001")
        self.txt_verify_id.pack(side="left", padx=4)

        btn_verify = tk.Button(
            top_bar,
            text="🔍 Verify Layout",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["crimson"],
            fg="white",
            relief="flat",
            padx=14,
            pady=5,
            cursor="hand2",
            command=self._verify_ticket_claim
        )
        btn_verify.pack(side="left", padx=8)

        tk.Label(
            top_bar,
            text="Or Pick From Batch:",
            font=("Segoe UI", 9),
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"]
        ).pack(side="left", padx=(15, 4))

        self.combo_tickets = ttk.Combobox(top_bar, state="readonly", width=18)
        self.combo_tickets.pack(side="left", padx=4)
        self.combo_tickets.bind("<<ComboboxSelected>>", self._on_ticket_selected)

        # Ticket Display Frame
        self.verifier_display = tk.Frame(container, bg=THEME["bg_dark"])
        self.verifier_display.pack(fill="both", expand=True)

        self.lbl_verifier_status = tk.Label(
            self.verifier_display,
            text="Enter a Ticket ID above to verify winning claims.",
            font=("Segoe UI", 12),
            bg=THEME["bg_dark"],
            fg=THEME["text_secondary"]
        )
        self.lbl_verifier_status.pack(pady=40)

    def _refresh_archive_batch_dropdown(self):
        """Scan tickets_archive/ for *_registry.json files."""
        TICKETS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        json_files = sorted(TICKETS_ARCHIVE_DIR.glob("*_registry.json"), key=os.path.getmtime, reverse=True)
        items = ["-- Active SQLite Database (Default) --"]
        for jf in json_files:
            items.append(jf.name)

        self.combo_batch_archive["values"] = items
        if items:
            self.combo_batch_archive.current(0)
            self.loaded_archive_name = None
            self.loaded_archive_tickets = {}

    def _on_batch_archive_selected(self, event):
        """Load selected batch JSON registry into verifier memory."""
        sel = self.combo_batch_archive.get()
        if not sel or "-- Active SQLite" in sel:
            self.loaded_archive_name = None
            self.loaded_archive_tickets = {}
            self.lbl_batch_status.config(text="Source: Active SQLite Database", fg=THEME["emerald"])
            self._refresh_verifier_ticket_list()
            return

        json_path = TICKETS_ARCHIVE_DIR / sel
        if not json_path.is_file():
            messagebox.showerror("Error", f"Archive registry file not found:\n{json_path}")
            return

        try:
            with open(json_path, "r", encoding="utf-8") as rf:
                reg_data = json.load(rf)

            raw_tickets = reg_data.get("tickets", [])
            self.loaded_archive_tickets = {str(t["ticket_id"]): t for t in raw_tickets}
            self.loaded_archive_name = reg_data.get("batch_name", sel)

            count = len(self.loaded_archive_tickets)
            self.lbl_batch_status.config(
                text=f"Batch: {self.loaded_archive_name} ({count} tickets loaded)",
                fg=THEME["gold"]
            )
            self._refresh_verifier_ticket_list()
            messagebox.showinfo(
                "Batch Loaded",
                f"Successfully loaded '{self.loaded_archive_name}' with {count} tickets from tickets_archive/!"
            )
        except Exception as e:
            messagebox.showerror("Registry Load Error", f"Failed to load archive registry:\n{e}")

    def _refresh_verifier_ticket_list(self):
        """Update ticket ID combobox from active database or loaded archive."""
        if self.loaded_archive_tickets:
            items = [f"Ticket #{tid}" for tid in sorted(self.loaded_archive_tickets.keys())]
        else:
            tickets = database.get_all_tickets()
            items = [f"Ticket #{t['ticket_id']}" for t in tickets]

        self.combo_tickets["values"] = items
        if items:
            self.combo_tickets.current(0)

    def _on_ticket_selected(self, event):
        val = self.combo_tickets.get()
        if "#" in val:
            tid = val.split("#")[1].strip()
            self.txt_verify_id.delete(0, "end")
            self.txt_verify_id.insert(0, tid)
            self._verify_ticket_claim()

    def _verify_ticket_claim(self):
        """Render 3x9 grid for ticket and mark called songs."""
        tid = self.txt_verify_id.get().strip()
        ticket = None

        # 1. Check loaded batch archive first if active
        if self.loaded_archive_tickets:
            ticket = self.loaded_archive_tickets.get(tid)
            if not ticket and tid.isdigit():
                # Try padded/unpadded
                ticket = self.loaded_archive_tickets.get(f"{int(tid):03d}")

        # 2. Fallback to active SQLite database
        if not ticket:
            ticket = database.get_ticket(tid)

        if not ticket:
            src = f"batch '{self.loaded_archive_name}'" if self.loaded_archive_name else "active database"
            messagebox.showwarning("Not Found", f"Ticket #{tid} not found in {src}.")
            return

        for w in self.verifier_display.winfo_children():
            w.destroy()

        strips = ticket.get("strips", [])
        total_songs = sum(1 for s in strips for r in s for c in r if c > 0)
        matched_songs = sum(1 for s in strips for r in s for c in r if c > 0 and c in self.called_numbers)

        header_box = tk.Frame(self.verifier_display, bg=THEME["bg_card"], padx=15, pady=8, relief="solid", bd=1)
        header_box.pack(fill="x", pady=(0, 10))

        batch_tag = f"[{self.loaded_archive_name}] " if self.loaded_archive_name else ""
        tk.Label(
            header_box,
            text=f"{batch_tag}TICKET #{tid} — {matched_songs}/{total_songs} SONGS CALLED",
            font=("Segoe UI", 12, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["gold"]
        ).pack(side="left")

        # Early 5 badge
        e5_text = "✓ Early 5: COMPLETE" if matched_songs >= 5 else f"Early 5: {matched_songs}/5"
        e5_color = THEME["emerald"] if matched_songs >= 5 else THEME["text_secondary"]
        tk.Label(
            header_box,
            text=e5_text,
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_card"],
            fg=e5_color
        ).pack(side="right", padx=10)

        # Render Strips
        for s_idx, strip in enumerate(strips, start=1):
            s_frame = tk.Frame(self.verifier_display, bg=THEME["bg_card"], padx=10, pady=8, relief="solid", bd=1)
            s_frame.pack(fill="x", pady=5)

            tk.Label(
                s_frame,
                text=f"STRIP {s_idx}",
                font=("Segoe UI", 10, "bold"),
                bg=THEME["bg_card"],
                fg=THEME["crimson"]
            ).pack(anchor="w", pady=(0, 4))

            tbl = tk.Frame(s_frame, bg=THEME["border"])
            tbl.pack(fill="x")

            for r_idx, row in enumerate(strip):
                for c_idx, sid in enumerate(row):
                    if sid > 0:
                        is_called = (sid in self.called_numbers)
                        bg_c = THEME["emerald"] if is_called else THEME["bg_card"]
                        fg_c = "#FFFFFF" if is_called else THEME["text_primary"]
                        txt = f"{sid}\n{song_bank.get_song_title(sid)[:14]}"
                    else:
                        bg_c = THEME["bg_subtle"]
                        fg_c = THEME["text_secondary"]
                        txt = ""

                    c_lbl = tk.Label(
                        tbl,
                        text=txt,
                        font=("Segoe UI", 9, "bold" if sid > 0 else "normal"),
                        bg=bg_c,
                        fg=fg_c,
                        height=2,
                        relief="solid",
                        bd=1
                    )
                    c_lbl.grid(row=r_idx, column=c_idx, sticky="nsew", padx=1, pady=1)

            for c in range(9):
                tbl.columnconfigure(c, weight=1)


def main():
    app = MusicalTambolaStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
