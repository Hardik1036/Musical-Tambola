"""
Musical Housie (Tambola) - Master Desktop Application & Host Studio
===================================================================
A complete, production-grade, multi-screen offline desktop application
implementing a clean, solid body aesthetic using light pastel/accent colors
(#F4F6FB, #FFFFFF, #E5EAF2, #5B61F4, #05B384, #FF5A5F, #F49D37).

Features:
  - Screen 1: Live Caller & Master Stage (Hero Calling Deck, Animated Equalizer,
              Seek Scrubber, 10x9 Calling Board with Satyam/Shivam/Sundaram pillars)
  - Screen 2: Lucky Draw & Raffle Module (Animated rolling lottery slot effect,
              configurable winners, tie-breaker categories, persistent audit log)
  - Screen 3: Claim Verifier & Ticket Inspector (Batch registry auto-loader,
              interactive 3x9 visual grid overlay, real-time auto-verdict engine)
  - Screen 4: Ticket Generator & Template Studio (Print-ahead batch generator,
              strict non-destructive collision protection, template picker & browser)

Zero cloud dependencies. Built with PyQt/PySide and Pygame.
"""

import os
import sys
import json
import math
import time
import random
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Qt Compatibility Layer
from qt_compat import (
    Qt, QTimer, pyqtSignal,
    QFont, QColor, QIcon, QPainter, QPen, QBrush, QLinearGradient, QPainterPath, QPixmap, QRect, QRectF,
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSlider, QProgressBar, QFrame, QMessageBox, QScrollArea,
    QCheckBox, QRadioButton, QButtonGroup, QSizePolicy, QSpinBox, QComboBox,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QTabWidget, QStatusBar
)

# Core Engine Modules
import song_bank
from config import TICKETS_ARCHIVE_DIR, ASSETS_DIR, BRANDING_DIR, SONGS_DIR
from modules.audio_player import AudioPlayer
from generator.generate_housie_tickets import (
    generate_housie_tickets,
    sanitize_batch_name,
    resolve_unique_batch_name
)

# ---------------------------------------------------------------------------
# Design System & Color Palette Tokens (Light Pastel / Accent System)
# ---------------------------------------------------------------------------
PALETTE = {
    "bg_main": "#F4F6FB",          # Solid off-white main background
    "bg_card": "#FFFFFF",          # Pure white container cards
    "bg_card_alt": "#F8FAFD",      # Light tinted card
    "border": "#E5EAF2",           # Crisp border
    "border_light": "#EDF2F7",     # Ultra-subtle border
    "border_focus": "#5B61F4",     # Soft indigo border highlight

    "indigo": "#5B61F4",           # Soft Indigo (Primary action)
    "indigo_hover": "#4D53E8",
    "indigo_light": "#EEF0FE",
    "indigo_dark": "#3B40B5",

    "emerald": "#05B384",          # Emerald (Called / Verified / Success)
    "emerald_hover": "#04966F",
    "emerald_light": "#E6F8F3",
    "emerald_dark": "#036C50",

    "coral": "#FF5A5F",            # Coral (Pending / Warning / Alert)
    "coral_hover": "#E84E53",
    "coral_light": "#FFF0F1",
    "coral_dark": "#BA3A3E",

    "amber": "#F49D37",            # Amber / Gold (Active Track / Highlight)
    "amber_hover": "#E08C25",
    "amber_light": "#FEF5EB",
    "amber_dark": "#B36B15",

    "text_primary": "#1E293B",     # Dark Slate primary text
    "text_secondary": "#64748B",   # Medium Slate secondary text
    "text_muted": "#94A3B8",       # Muted slate text
    "text_white": "#FFFFFF",

    "cell_blank": "#F1F5F9",       # Blank Tambola slot gray
    "cell_blank_border": "#E2E8F0"
}

GLOBAL_STYLESHEET = f"""
QMainWindow, QWidget#root_container {{
    background-color: {PALETTE['bg_main']};
    color: {PALETTE['text_primary']};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', Roboto, Arial, sans-serif;
}}

/* Top Navigation Bar / Tab Widget */
QTabWidget::pane {{
    border: none;
    background-color: {PALETTE['bg_main']};
}}

QTabBar::tab {{
    background-color: {PALETTE['bg_card']};
    color: {PALETTE['text_secondary']};
    font-weight: 600;
    font-size: 13px;
    padding: 10px 20px;
    margin-right: 8px;
    margin-top: 6px;
    border: 1px solid {PALETTE['border']};
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    min-width: 130px;
}}

QTabBar::tab:selected {{
    background-color: {PALETTE['indigo']};
    color: {PALETTE['text_white']};
    border-color: {PALETTE['indigo']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {PALETTE['indigo_light']};
    color: {PALETTE['indigo']};
}}

/* Cards & Frames */
QFrame.card-panel {{
    background-color: {PALETTE['bg_card']};
    border: 1px solid {PALETTE['border']};
    border-radius: 12px;
}}

QFrame.card-subtle {{
    background-color: {PALETTE['bg_card_alt']};
    border: 1px solid {PALETTE['border_light']};
    border-radius: 10px;
}}

/* Standard Buttons */
QPushButton {{
    background-color: {PALETTE['bg_card']};
    color: {PALETTE['text_primary']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {PALETTE['bg_card_alt']};
    border-color: #CBD5E1;
}}

QPushButton.btn-primary {{
    background-color: {PALETTE['indigo']};
    color: {PALETTE['text_white']};
    border: 1px solid {PALETTE['indigo']};
}}
QPushButton.btn-primary:hover {{
    background-color: {PALETTE['indigo_hover']};
    border-color: {PALETTE['indigo_hover']};
}}

QPushButton.btn-emerald {{
    background-color: {PALETTE['emerald']};
    color: {PALETTE['text_white']};
    border: 1px solid {PALETTE['emerald']};
}}
QPushButton.btn-emerald:hover {{
    background-color: {PALETTE['emerald_hover']};
    border-color: {PALETTE['emerald_hover']};
}}

QPushButton.btn-amber {{
    background-color: {PALETTE['amber']};
    color: {PALETTE['text_white']};
    border: 1px solid {PALETTE['amber']};
}}
QPushButton.btn-amber:hover {{
    background-color: {PALETTE['amber_hover']};
    border-color: {PALETTE['amber_hover']};
}}

QPushButton.btn-coral {{
    background-color: {PALETTE['coral']};
    color: {PALETTE['text_white']};
    border: 1px solid {PALETTE['coral']};
}}
QPushButton.btn-coral:hover {{
    background-color: {PALETTE['coral_hover']};
    border-color: {PALETTE['coral_hover']};
}}

/* Inputs, Spinners & Combos */
QLineEdit, QSpinBox, QComboBox {{
    background-color: {PALETTE['bg_card']};
    color: {PALETTE['text_primary']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {PALETTE['indigo']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

/* Tables */
QTableWidget {{
    background-color: {PALETTE['bg_card']};
    color: {PALETTE['text_primary']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    gridline-color: {PALETTE['border_light']};
    font-size: 12px;
}}

QHeaderView::section {{
    background-color: {PALETTE['bg_card_alt']};
    color: {PALETTE['text_secondary']};
    font-weight: 700;
    font-size: 11px;
    padding: 8px 6px;
    border: none;
    border-bottom: 1.5px solid {PALETTE['border']};
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 6px;
    background: {PALETTE['border']};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {PALETTE['indigo']};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {PALETTE['indigo']};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
    border: 2px solid #FFFFFF;
}}
QSlider::handle:horizontal:hover {{
    background: {PALETTE['indigo_hover']};
}}

/* Progress Bar */
QProgressBar {{
    background-color: {PALETTE['border_light']};
    border: 1px solid {PALETTE['border']};
    border-radius: 6px;
    text-align: center;
    color: {PALETTE['text_primary']};
    font-size: 11px;
    font-weight: 700;
    height: 14px;
}}
QProgressBar::chunk {{
    background-color: {PALETTE['emerald']};
    border-radius: 5px;
}}

/* Scrollbar */
QScrollBar:vertical {{
    border: none;
    background: {PALETTE['bg_main']};
    width: 8px;
    margin: 0;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #CBD5E1;
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94A3B8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""


# ---------------------------------------------------------------------------
# Animated Equalizer Graphic Widget
# ---------------------------------------------------------------------------
class EqualizerVisualizer(QWidget):
    """
    Real-time animated reactive sound equalizer bar graphic.
    Pulses rhythmically when music is playing, drops to a gentle idle baseline when stopped.
    """
    def __init__(self, num_bars: int = 24, parent=None):
        super().__init__(parent)
        self.num_bars = num_bars
        self.is_active = False
        self.setMinimumHeight(44)
        self.setMaximumHeight(54)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Bar heights and velocities
        self.levels = [0.15] * self.num_bars
        self.target_levels = [0.15] * self.num_bars
        self.phase = 0.0

        # Animation timer (35ms ~ 28 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_levels)
        self.timer.start(35)

    def set_active(self, active: bool):
        self.is_active = active

    def _update_levels(self):
        self.phase += 0.12
        if self.is_active:
            for i in range(self.num_bars):
                # Harmonic wave pattern with slight random jitter
                wave1 = math.sin(self.phase + i * 0.4) * 0.45
                wave2 = math.cos(self.phase * 1.5 - i * 0.25) * 0.35
                jitter = random.uniform(0.0, 0.25)
                val = max(0.12, min(1.0, 0.45 + wave1 + wave2 + jitter))
                self.target_levels[i] = val
        else:
            # Gentle breathing baseline
            for i in range(self.num_bars):
                idle_wave = 0.12 + 0.06 * math.sin(self.phase * 0.5 + i * 0.3)
                self.target_levels[i] = idle_wave

        # Smooth interpolation (lerp)
        for i in range(self.num_bars):
            self.levels[i] += (self.target_levels[i] - self.levels[i]) * 0.35

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_w = max(2.0, (w - (self.num_bars - 1) * 3) / self.num_bars)

        for i in range(self.num_bars):
            bar_h = max(3.0, self.levels[i] * (h - 6))
            x = i * (bar_w + 3)
            y = h - bar_h - 2

            # Smooth pastel gradient: Indigo to Emerald/Amber
            grad = QLinearGradient(x, y + bar_h, x, y)
            if self.is_active:
                grad.setColorAt(0.0, QColor(PALETTE["indigo"]))
                grad.setColorAt(0.65, QColor(PALETTE["emerald"]))
                grad.setColorAt(1.0, QColor(PALETTE["amber"]))
            else:
                grad.setColorAt(0.0, QColor("#CBD5E1"))
                grad.setColorAt(1.0, QColor("#94A3B8"))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            rect = QRectF(x, y, bar_w, bar_h)
            painter.drawRoundedRect(rect, 2.0, 2.0)


# ---------------------------------------------------------------------------
# Pulsing Hero Call Badge Widget
# ---------------------------------------------------------------------------
class HeroCallBadge(QWidget):
    """
    Hero calling deck track badge displaying current number (#01 to #90)
    with subtle zoom/pulse animation on call.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self.current_number: Optional[int] = None
        self.pulse_scale = 1.0
        self.anim_step = 0

        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._animate_pulse)

    def trigger_call(self, number: int):
        self.current_number = number
        self.pulse_scale = 1.25
        self.anim_step = 0
        self.pulse_timer.start(25)
        self.update()

    def reset(self):
        self.current_number = None
        self.pulse_scale = 1.0
        self.update()

    def _animate_pulse(self):
        self.anim_step += 1
        self.pulse_scale -= 0.02
        if self.pulse_scale <= 1.0:
            self.pulse_scale = 1.0
            self.pulse_timer.stop()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        base_radius = 56.0 * self.pulse_scale

        # Outer soft glow circle
        if self.current_number is not None:
            glow_grad = QLinearGradient(0, 0, self.width(), self.height())
            glow_grad.setColorAt(0.0, QColor(PALETTE["amber_light"]))
            glow_grad.setColorAt(1.0, QColor(PALETTE["indigo_light"]))
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(QPen(QColor(PALETTE["amber"]), 3.0))
        else:
            painter.setBrush(QBrush(QColor(PALETTE["bg_card_alt"])))
            painter.setPen(QPen(QColor(PALETTE["border"]), 2.0))

        painter.drawEllipse(QRectF(center_x - base_radius, center_y - base_radius, base_radius * 2, base_radius * 2))

        # Text rendering
        painter.setPen(QColor(PALETTE["amber_dark"] if self.current_number else PALETTE["text_muted"]))
        if self.current_number is not None:
            painter.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
            num_str = f"#{self.current_number:02d}"
        else:
            painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
            num_str = "READY"

        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, num_str)


# ---------------------------------------------------------------------------
# SCREEN 1: Live Caller & Master Stage (PRD 2.3)
# ---------------------------------------------------------------------------
class LiveCallerStageScreen(QWidget):
    """
    Split-view gameplay stage:
      - Left: Hero calling deck with animated equalizer, song details, audio controls, seek slider.
      - Right: 10x9 Master Calling Board organized into Satyam/Shivam/Sundaram pillars.
    """
    number_called = pyqtSignal(int)
    game_reset = pyqtSignal()

    def __init__(self, audio_player: AudioPlayer, parent=None):
        super().__init__(parent)
        self.audio_player = audio_player
        self.called_numbers: List[int] = []
        self.current_number: Optional[int] = None

        # Auto-Draw mode
        self.auto_draw_timer = QTimer(self)
        self.auto_draw_timer.timeout.connect(self.draw_next_track)

        # Scrubber & position tracking timer
        self.position_timer = QTimer(self)
        self.position_timer.timeout.connect(self._update_playback_position)
        self.position_timer.start(100)

        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        # -------------------------------------------------------------------
        # LEFT PANEL: Hero Calling Deck
        # -------------------------------------------------------------------
        left_panel = QFrame()
        left_panel.setProperty("class", "card-panel")
        left_panel.setFixedWidth(430)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(18, 16, 18, 16)
        left_layout.setSpacing(10)

        # Hero Header Pill
        deck_header = QHBoxLayout()
        header_title = QLabel("🎙️ MASTER CALLING DECK")
        header_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header_title.setStyleSheet(f"color: {PALETTE['indigo']}; letter-spacing: 0.5px;")
        deck_header.addWidget(header_title)
        deck_header.addStretch()

        self.call_counter_badge = QLabel("0 / 90")
        self.call_counter_badge.setStyleSheet(
            f"background: {PALETTE['indigo_light']}; color: {PALETTE['indigo']}; "
            f"font-weight: 700; font-size: 12px; padding: 3px 10px; border-radius: 12px;"
        )
        deck_header.addWidget(self.call_counter_badge)
        left_layout.addLayout(deck_header)

        # Centered Hero Call Badge
        badge_container = QHBoxLayout()
        badge_container.addStretch()
        self.hero_badge = HeroCallBadge(self)
        badge_container.addWidget(self.hero_badge)
        badge_container.addStretch()
        left_layout.addLayout(badge_container)

        # Animated Reactive Equalizer
        self.equalizer = EqualizerVisualizer(num_bars=24, parent=self)
        left_layout.addWidget(self.equalizer)

        # Song Details Card
        details_box = QFrame()
        details_box.setProperty("class", "card-subtle")
        details_layout = QVBoxLayout(details_box)
        details_layout.setContentsMargins(12, 10, 12, 10)
        details_layout.setSpacing(4)

        self.lbl_pillar_tag = QLabel("PILLAR: READY TO DRAW")
        self.lbl_pillar_tag.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_pillar_tag.setStyleSheet(f"color: {PALETTE['amber_dark']};")
        details_layout.addWidget(self.lbl_pillar_tag)

        self.lbl_song_title = QLabel("Press 'Draw Next Track' to Begin")
        self.lbl_song_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.lbl_song_title.setStyleSheet(f"color: {PALETTE['text_primary']};")
        self.lbl_song_title.setWordWrap(True)
        details_layout.addWidget(self.lbl_song_title)

        self.lbl_song_sub = QLabel("Master 90 Evergreen Bollywood & Indian Hits")
        self.lbl_song_sub.setFont(QFont("Segoe UI", 11, QFont.Weight.Normal))
        self.lbl_song_sub.setStyleSheet(f"color: {PALETTE['text_secondary']};")
        self.lbl_song_sub.setWordWrap(True)
        details_layout.addWidget(self.lbl_song_sub)

        self.lbl_audio_status = QLabel("")
        self.lbl_audio_status.setStyleSheet("font-size: 11px; font-weight: 600; color: #FF5A5F;")
        details_layout.addWidget(self.lbl_audio_status)

        left_layout.addWidget(details_box)

        # Real-time Audio Seek Scrubber
        scrubber_container = QVBoxLayout()
        scrubber_container.setSpacing(2)

        scrubber_labels = QHBoxLayout()
        self.lbl_cur_time = QLabel("00:00")
        self.lbl_cur_time.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 11px; font-weight: 600;")
        self.lbl_tot_time = QLabel("00:00")
        self.lbl_tot_time.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 11px; font-weight: 600;")
        scrubber_labels.addWidget(self.lbl_cur_time)
        scrubber_labels.addStretch()
        scrubber_labels.addWidget(self.lbl_tot_time)
        scrubber_container.addLayout(scrubber_labels)

        self.slider_seek = QSlider(Qt.Orientation.Horizontal)
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.setValue(0)
        self.slider_seek.sliderMoved.connect(self._on_seek_moved)
        scrubber_container.addWidget(self.slider_seek)
        left_layout.addLayout(scrubber_container)

        # Audio Transport Buttons
        transport_layout = QHBoxLayout()
        transport_layout.setSpacing(6)

        self.btn_play_pause = QPushButton("▶ Play")
        self.btn_play_pause.setProperty("class", "btn-primary")
        self.btn_play_pause.clicked.connect(self._toggle_play_pause)
        transport_layout.addWidget(self.btn_play_pause)

        self.btn_replay = QPushButton("↺ Replay")
        self.btn_replay.clicked.connect(self._replay_current_track)
        transport_layout.addWidget(self.btn_replay)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.clicked.connect(self._stop_playback)
        transport_layout.addWidget(self.btn_stop)

        left_layout.addLayout(transport_layout)

        # Volume Slider
        vol_layout = QHBoxLayout()
        lbl_vol = QLabel("🔊")
        vol_layout.addWidget(lbl_vol)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(80)
        self.slider_vol.valueChanged.connect(self._on_volume_changed)
        vol_layout.addWidget(self.slider_vol)

        self.lbl_vol_val = QLabel("80%")
        self.lbl_vol_val.setFixedWidth(36)
        self.lbl_vol_val.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 11px; font-weight: 600;")
        vol_layout.addWidget(self.lbl_vol_val)
        left_layout.addLayout(vol_layout)

        # Draw Next Action Button (Vibrant & Hero)
        self.btn_draw = QPushButton("🎲 Draw Next Track (Space)")
        self.btn_draw.setProperty("class", "btn-emerald")
        self.btn_draw.setMinimumHeight(44)
        self.btn_draw.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.btn_draw.clicked.connect(self.draw_next_track)
        left_layout.addWidget(self.btn_draw)

        # Session Progress & Stats
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 90)
        self.progress_bar.setValue(0)
        stats_layout.addWidget(self.progress_bar)

        stats_row = QHBoxLayout()
        self.lbl_stats = QLabel("Called: 0 • Remaining: 90")
        self.lbl_stats.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 11px; font-weight: 600;")
        stats_row.addWidget(self.lbl_stats)
        stats_row.addStretch()

        self.btn_reset = QPushButton("Reset Game")
        self.btn_reset.setStyleSheet(f"font-size: 11px; color: {PALETTE['coral']}; border: none; font-weight: 700; padding: 2px 4px;")
        self.btn_reset.clicked.connect(self.confirm_reset_game)
        stats_row.addWidget(self.btn_reset)
        stats_layout.addLayout(stats_row)

        left_layout.addLayout(stats_layout)

        # Auto-Draw Mode Row
        auto_layout = QHBoxLayout()
        self.chk_auto = QCheckBox("Auto-Call")
        self.chk_auto.setStyleSheet("font-size: 12px; font-weight: 600;")
        self.chk_auto.toggled.connect(self._toggle_auto_draw)
        auto_layout.addWidget(self.chk_auto)

        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(8, 60)
        self.spin_interval.setValue(18)
        self.spin_interval.setSuffix(" sec")
        auto_layout.addWidget(self.spin_interval)
        auto_layout.addStretch()

        self.btn_prev = QPushButton("⏮ Re-check Last")
        self.btn_prev.setStyleSheet("font-size: 11px;")
        self.btn_prev.clicked.connect(self._replay_last_call)
        auto_layout.addWidget(self.btn_prev)

        left_layout.addLayout(auto_layout)
        main_layout.addWidget(left_panel)

        # -------------------------------------------------------------------
        # RIGHT PANEL: 10x9 Master Calling Board
        # -------------------------------------------------------------------
        right_panel = QFrame()
        right_panel.setProperty("class", "card-panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(18, 16, 18, 16)
        right_layout.setSpacing(10)

        # Traditional Pillars Header
        pillars_header = QHBoxLayout()
        pillars_header.setSpacing(10)

        # Satyam (Cols 1-3)
        lbl_satyam = QLabel("🌸 SATYAM (Cols 1–3 • Nos 1–29)")
        lbl_satyam.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_satyam.setStyleSheet(
            f"background: {PALETTE['indigo_light']}; color: {PALETTE['indigo']}; "
            f"font-weight: 700; font-size: 12px; padding: 6px; border-radius: 8px;"
        )
        pillars_header.addWidget(lbl_satyam, 3)

        # Shivam (Cols 4-6)
        lbl_shivam = QLabel("🌿 SHIVAM (Cols 4–6 • Nos 30–59)")
        lbl_shivam.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_shivam.setStyleSheet(
            f"background: {PALETTE['emerald_light']}; color: {PALETTE['emerald_dark']}; "
            f"font-weight: 700; font-size: 12px; padding: 6px; border-radius: 8px;"
        )
        pillars_header.addWidget(lbl_shivam, 3)

        # Sundaram (Cols 7-9)
        lbl_sundaram = QLabel("✨ SUNDARAM (Cols 7–9 • Nos 60–90)")
        lbl_sundaram.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sundaram.setStyleSheet(
            f"background: {PALETTE['amber_light']}; color: {PALETTE['amber_dark']}; "
            f"font-weight: 700; font-size: 12px; padding: 6px; border-radius: 8px;"
        )
        pillars_header.addWidget(lbl_sundaram, 3)
        right_layout.addLayout(pillars_header)

        # 10x9 Grid of Interactive Cells
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")

        grid_container = QWidget()
        grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setSpacing(6)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)

        self.cell_buttons: Dict[int, QPushButton] = {}
        for num in range(1, 91):
            col = song_bank.get_column_for_index(num)
            start_num, _ = song_bank.COLUMN_RANGES[col]
            row = num - start_num

            btn = QPushButton(f"{num}")
            btn.setFixedSize(54, 44)
            btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            s_meta = song_bank.get_song(num)
            title = s_meta.get("title", f"Track #{num}") if s_meta else f"Track #{num}"
            btn.setToolTip(f"#{num}: {title}\n(Click to inspect or play)")
            btn.clicked.connect(lambda _, n=num: self._on_cell_clicked(n))

            # Store and apply pending style
            self.cell_buttons[num] = btn
            self._apply_cell_style(btn, status="pending")
            self.grid_layout.addWidget(btn, row, col)

        scroll_area.setWidget(grid_container)
        right_layout.addWidget(scroll_area)
        main_layout.addWidget(right_panel, 1)

    def _apply_cell_style(self, btn: QPushButton, status: str):
        """Dynamic color states for calling board cells."""
        if status == "active":
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETTE['amber_light']};
                    color: {PALETTE['amber_dark']};
                    border: 2px solid {PALETTE['amber']};
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 800;
                }}
            """)
        elif status == "called":
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETTE['emerald_light']};
                    color: {PALETTE['emerald_dark']};
                    border: 1.5px solid {PALETTE['emerald']};
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: #D1F5EA;
                }}
            """)
        else: # pending
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETTE['bg_card']};
                    color: {PALETTE['text_secondary']};
                    border: 1px solid {PALETTE['border']};
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {PALETTE['bg_card_alt']};
                    border-color: #CBD5E1;
                }}
            """)

    def draw_next_track(self):
        """Draw next track non-repeating from remaining numbers 1-90."""
        available = [i for i in range(1, 91) if i not in self.called_numbers]
        if not available:
            self.auto_draw_timer.stop()
            self.chk_auto.setChecked(False)
            QMessageBox.information(self, "House Full", "All 90 numbers have been called!")
            return

        next_num = random.choice(available)
        self.call_number(next_num)

    def call_number(self, num: int):
        """Process drawing a specific number."""
        if num in self.called_numbers:
            return

        # Demote previous active cell to called
        if self.current_number and self.current_number in self.cell_buttons:
            self._apply_cell_style(self.cell_buttons[self.current_number], "called")

        self.current_number = num
        self.called_numbers.append(num)

        # Highlight cell
        if num in self.cell_buttons:
            self._apply_cell_style(self.cell_buttons[num], "active")

        # Update hero deck
        self.hero_badge.trigger_call(num)
        self.audio_player.play_draw_chime()

        # Update metadata
        s_meta = song_bank.get_song(num)
        if s_meta:
            title = s_meta.get("title", f"Track #{num}")
            artist = s_meta.get("artist", "")
            year = s_meta.get("year", "")
            col = s_meta.get("column", 0)
            pillar = "SATYAM" if col < 3 else ("SHIVAM" if col < 6 else "SUNDARAM")

            self.lbl_pillar_tag.setText(f"PILLAR: {pillar} (COL {col + 1}) • TRACK #{num}")
            self.lbl_song_title.setText(title)
            self.lbl_song_sub.setText(f"{artist} • {year}" if artist or year else "Evergreen Hit")
        else:
            self.lbl_pillar_tag.setText(f"TRACK #{num}")
            self.lbl_song_title.setText(f"Song #{num}")
            self.lbl_song_sub.setText("")

        # Update stats
        called_count = len(self.called_numbers)
        self.call_counter_badge.setText(f"{called_count} / 90")
        self.lbl_stats.setText(f"Called: {called_count} • Remaining: {90 - called_count}")
        self.progress_bar.setValue(called_count)

        # Audio playback with graceful missing audio fallback
        audio_file = song_bank.find_audio_file(num)
        if audio_file and Path(audio_file).is_file():
            self.lbl_audio_status.setText("")
            self.audio_player.play_track(audio_file, start_pos=0.0)
            self.btn_play_pause.setText("⏸ Pause")
            self.equalizer.set_active(True)
        else:
            self.lbl_audio_status.setText("⚠️ Audio clip missing (Visual mode active)")
            self.audio_player.stop()
            self.btn_play_pause.setText("▶ Play")
            self.equalizer.set_active(False)

        # Emit signal for verifier & raffle
        self.number_called.emit(num)

    def _on_cell_clicked(self, num: int):
        """Click cell on board to inspect or replay audio."""
        if num in self.called_numbers:
            # Replay track
            audio_file = song_bank.find_audio_file(num)
            if audio_file and Path(audio_file).is_file():
                self.audio_player.play_track(audio_file)
                self.btn_play_pause.setText("⏸ Pause")
                self.equalizer.set_active(True)
        else:
            # Option to manually call
            reply = QMessageBox.question(
                self, "Manual Call",
                f"Number #{num} is uncalled.\nWould you like to draw #{num} now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.call_number(num)

    def _toggle_play_pause(self):
        if self.audio_player.is_playing and not self.audio_player.is_paused:
            self.audio_player.pause()
            self.btn_play_pause.setText("▶ Resume")
            self.equalizer.set_active(False)
        elif self.audio_player.is_paused:
            self.audio_player.resume()
            self.btn_play_pause.setText("⏸ Pause")
            self.equalizer.set_active(True)
        elif self.current_number:
            audio_file = song_bank.find_audio_file(self.current_number)
            if audio_file:
                self.audio_player.play_track(audio_file)
                self.btn_play_pause.setText("⏸ Pause")
                self.equalizer.set_active(True)

    def _replay_current_track(self):
        if self.current_number:
            audio_file = song_bank.find_audio_file(self.current_number)
            if audio_file:
                self.audio_player.play_track(audio_file, start_pos=0.0)
                self.btn_play_pause.setText("⏸ Pause")
                self.equalizer.set_active(True)

    def _stop_playback(self):
        self.audio_player.stop()
        self.btn_play_pause.setText("▶ Play")
        self.equalizer.set_active(False)
        self.slider_seek.setValue(0)
        self.lbl_cur_time.setText("00:00")

    def _replay_last_call(self):
        if self.current_number:
            self._replay_current_track()

    def _on_volume_changed(self, val: int):
        self.audio_player.set_volume(val)
        self.lbl_vol_val.setText(f"{val}%")

    def _on_seek_moved(self, slider_val: int):
        dur = self.audio_player.total_duration
        if dur > 0:
            target = (slider_val / 1000.0) * dur
            self.audio_player.seek(target)

    def _update_playback_position(self):
        if self.audio_player.is_playing:
            cur = self.audio_player.get_current_position()
            tot = self.audio_player.total_duration
            if tot > 0:
                pct = int((cur / tot) * 1000)
                self.slider_seek.setValue(pct)
                self.lbl_cur_time.setText(f"{int(cur//60):02d}:{int(cur%60):02d}")
                self.lbl_tot_time.setText(f"{int(tot//60):02d}:{int(tot%60):02d}")
            self.equalizer.set_active(True)
        else:
            if not self.audio_player.is_paused:
                self.equalizer.set_active(False)

    def _toggle_auto_draw(self, enabled: bool):
        if enabled:
            interval_ms = self.spin_interval.value() * 1000
            self.auto_draw_timer.start(interval_ms)
        else:
            self.auto_draw_timer.stop()

    def confirm_reset_game(self):
        reply = QMessageBox.question(
            self, "Reset Game Session",
            "Are you sure you want to reset the current game session?\n"
            "This will clear all 90 calling board cells and draw history.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.reset_session()

    def reset_session(self):
        self.auto_draw_timer.stop()
        self.chk_auto.setChecked(False)
        self.audio_player.stop()
        self.equalizer.set_active(False)
        self.called_numbers.clear()
        self.current_number = None

        # Reset all cell styles
        for num, btn in self.cell_buttons.items():
            self._apply_cell_style(btn, "pending")

        self.hero_badge.reset()
        self.lbl_pillar_tag.setText("PILLAR: READY TO DRAW")
        self.lbl_song_title.setText("Press 'Draw Next Track' to Begin")
        self.lbl_song_sub.setText("Master 90 Evergreen Bollywood & Indian Hits")
        self.lbl_audio_status.setText("")
        self.call_counter_badge.setText("0 / 90")
        self.lbl_stats.setText("Called: 0 • Remaining: 90")
        self.progress_bar.setValue(0)
        self.btn_play_pause.setText("▶ Play")
        self.slider_seek.setValue(0)
        self.lbl_cur_time.setText("00:00")
        self.lbl_tot_time.setText("00:00")

        self.game_reset.emit()


# ---------------------------------------------------------------------------
# SCREEN 2: Lucky Draw & Raffle Module (PRD 2.4)
# ---------------------------------------------------------------------------
class LuckyDrawScreen(QWidget):
    """
    Dedicated tie-breaker & raffle module featuring animated rolling lottery slot effect,
    configurable simultaneous winners, category selection, and persistent session audit log.
    """
    def __init__(self, audio_player: AudioPlayer, parent=None):
        super().__init__(parent)
        self.audio_player = audio_player
        self.called_numbers_ref: List[int] = []
        self.registered_tickets_ref: List[Dict[str, Any]] = []

        # Slot animation state
        self.is_rolling = False
        self.anim_ticks = 0
        self.total_anim_ticks = 40
        self.winner_candidates: List[Dict[str, Any]] = []

        self.slot_timer = QTimer(self)
        self.slot_timer.timeout.connect(self._step_slot_animation)

        self._init_ui()

    def set_called_numbers(self, called: List[int]):
        self.called_numbers_ref = called

    def set_registered_tickets(self, tickets: List[Dict[str, Any]]):
        self.registered_tickets_ref = tickets

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Header Title Card
        header_box = QFrame()
        header_box.setProperty("class", "card-panel")
        header_layout = QHBoxLayout(header_box)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("🎰 LUCKY DRAW & TIE-BREAKER RAFFLE")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {PALETTE['indigo']};")
        header_layout.addWidget(title)
        header_layout.addStretch()

        lbl_desc = QLabel("Provably Fair Random Tie-Breakers & Lucky Draw Engine")
        lbl_desc.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(lbl_desc)
        layout.addWidget(header_box)

        # Main Split Content
        content_split = QHBoxLayout()
        content_split.setSpacing(14)

        # Left Column: Configuration & Controls
        left_cfg = QFrame()
        left_cfg.setProperty("class", "card-panel")
        left_cfg.setFixedWidth(380)
        cfg_layout = QVBoxLayout(left_cfg)
        cfg_layout.setContentsMargins(16, 16, 16, 16)
        cfg_layout.setSpacing(12)

        cfg_title = QLabel("1. Configure Draw Parameters")
        cfg_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        cfg_layout.addWidget(cfg_title)

        # Prize / Category Selector
        cfg_layout.addWidget(QLabel("Prize / Claim Category:"))
        self.combo_category = QComboBox()
        self.combo_category.setEditable(True)
        categories = [
            "Early 5 Tie-Breaker",
            "Top Line Tie-Breaker",
            "Middle Line Tie-Breaker",
            "Bottom Line Tie-Breaker",
            "Four Corners Tie-Breaker",
            "Full House Tie-Breaker",
            "Lucky Star Raffle",
            "Fastest Finger Bonus",
            "Surprise Gift Draw"
        ]
        self.combo_category.addItems(categories)
        cfg_layout.addWidget(self.combo_category)

        # Winner Count SpinBox
        cfg_layout.addWidget(QLabel("Simultaneous Winners (1 to 10):"))
        self.spin_winners = QSpinBox()
        self.spin_winners.setRange(1, 10)
        self.spin_winners.setValue(1)
        cfg_layout.addWidget(self.spin_winners)

        # Pool Source Selection
        cfg_layout.addWidget(QLabel("Participant Draw Pool Source:"))
        self.btn_group_pool = QButtonGroup(self)

        self.radio_called = QRadioButton("Already-Called Numbers (Screen 1)")
        self.radio_called.setChecked(True)
        self.btn_group_pool.addButton(self.radio_called, 1)
        cfg_layout.addWidget(self.radio_called)

        self.radio_tickets = QRadioButton("Registered Ticket IDs (Current Batch)")
        self.btn_group_pool.addButton(self.radio_tickets, 2)
        cfg_layout.addWidget(self.radio_tickets)

        self.radio_all_songs = QRadioButton("All Game Numbers (1–90)")
        self.btn_group_pool.addButton(self.radio_all_songs, 3)
        cfg_layout.addWidget(self.radio_all_songs)

        cfg_layout.addSpacing(10)

        # Trigger Button
        self.btn_roll = QPushButton("🎰 Roll & Draw Winners!")
        self.btn_roll.setProperty("class", "btn-primary")
        self.btn_roll.setMinimumHeight(46)
        self.btn_roll.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.btn_roll.clicked.connect(self.start_draw)
        cfg_layout.addWidget(self.btn_roll)
        cfg_layout.addStretch()

        content_split.addWidget(left_cfg)

        # Right Column: Animated Slot Screen & Winner Announcement
        right_slot_frame = QFrame()
        right_slot_frame.setProperty("class", "card-panel")
        right_layout = QVBoxLayout(right_slot_frame)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(16)

        # Big Animated Slot Drum Display
        self.slot_box = QFrame()
        self.slot_box.setProperty("class", "card-subtle")
        self.slot_box.setMinimumHeight(150)
        slot_box_layout = QVBoxLayout(self.slot_box)
        slot_box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_slot_display = QLabel("READY TO ROLL")
        self.lbl_slot_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_slot_display.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.lbl_slot_display.setStyleSheet(f"color: {PALETTE['indigo']}; letter-spacing: 2px;")
        slot_box_layout.addWidget(self.lbl_slot_display)

        self.lbl_slot_sub = QLabel("Select parameters and click 'Roll & Draw Winners'")
        self.lbl_slot_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_slot_sub.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 13px;")
        slot_box_layout.addWidget(self.lbl_slot_sub)
        right_layout.addWidget(self.slot_box)

        # Winner Cards Container
        lbl_winners_heading = QLabel("🏆 Drawn Winner(s):")
        lbl_winners_heading.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        right_layout.addWidget(lbl_winners_heading)

        self.winners_scroll = QScrollArea()
        self.winners_scroll.setWidgetResizable(True)
        self.winners_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.winners_scroll.setStyleSheet("background: transparent;")

        self.winners_widget = QWidget()
        self.winners_layout = QVBoxLayout(self.winners_widget)
        self.winners_layout.setContentsMargins(0, 0, 0, 0)
        self.winners_layout.setSpacing(8)
        self.winners_scroll.setWidget(self.winners_widget)
        right_layout.addWidget(self.winners_scroll, 1)

        content_split.addWidget(right_slot_frame, 1)
        layout.addLayout(content_split, 1)

        # Bottom Frame: Persistent Session Audit Log Table
        log_frame = QFrame()
        log_frame.setProperty("class", "card-panel")
        log_frame.setFixedHeight(210)
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(16, 12, 16, 12)
        log_layout.setSpacing(8)

        log_top = QHBoxLayout()
        lbl_log_title = QLabel("📋 Session Raffle Audit Log")
        lbl_log_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        log_top.addWidget(lbl_log_title)
        log_top.addStretch()

        btn_copy_log = QPushButton("Copy Log")
        btn_copy_log.setStyleSheet("font-size: 11px;")
        btn_copy_log.clicked.connect(self._copy_log)
        log_top.addWidget(btn_copy_log)

        btn_clear_log = QPushButton("Clear Log")
        btn_clear_log.setStyleSheet(f"font-size: 11px; color: {PALETTE['coral']};")
        btn_clear_log.clicked.connect(self._clear_log)
        log_top.addWidget(btn_clear_log)
        log_layout.addLayout(log_top)

        self.table_log = QTableWidget(0, 5)
        self.table_log.setHorizontalHeaderLabels(["Timestamp", "Prize Category", "Pool Source", "Winner ID/Number", "Details / Song Title"])
        self.table_log.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_log.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        log_layout.addWidget(self.table_log)

        layout.addWidget(log_frame)

    def start_draw(self):
        if self.is_rolling:
            return

        # Determine pool candidates
        pool_type = self.btn_group_pool.checkedId()
        candidates: List[Dict[str, Any]] = []

        if pool_type == 1: # Called numbers
            if not self.called_numbers_ref:
                QMessageBox.warning(self, "Empty Pool", "No numbers have been called yet in Screen 1!")
                return
            for n in self.called_numbers_ref:
                s = song_bank.get_song(n)
                title = s.get("title", f"Track #{n}") if s else f"Track #{n}"
                candidates.append({"id": f"#{n:02d}", "name": title, "source": "Called Numbers"})
        elif pool_type == 2: # Registered tickets
            if not self.registered_tickets_ref:
                QMessageBox.warning(self, "No Tickets Loaded", "No ticket batch registry loaded. Generate or select a batch first in Screen 3 or 4!")
                return
            for t in self.registered_tickets_ref:
                tid = t.get("ticket_id", "001")
                candidates.append({"id": f"Ticket #{tid}", "name": f"Registered Sheet {tid}", "source": "Ticket Registry"})
        else: # All numbers 1-90
            for n in range(1, 91):
                s = song_bank.get_song(n)
                title = s.get("title", f"Track #{n}") if s else f"Track #{n}"
                candidates.append({"id": f"#{n:02d}", "name": title, "source": "All Numbers (1-90)"})

        num_winners = min(self.spin_winners.value(), len(candidates))
        self.winner_candidates = random.sample(candidates, num_winners)

        # Start slot animation
        self.is_rolling = True
        self.anim_ticks = 0
        self.btn_roll.setEnabled(False)
        self.slot_timer.start(45)

    def _step_slot_animation(self):
        self.anim_ticks += 1
        self.audio_player.play_tick()

        # Generate rolling slot display string
        r_num = random.randint(1, 90)
        self.lbl_slot_display.setText(f"🎲 ROLLING... #{r_num:02d}")
        self.lbl_slot_sub.setText("Selecting lucky winner(s)...")

        # Slow down near the end
        if self.anim_ticks > 25:
            self.slot_timer.setInterval(self.slot_timer.interval() + 15)

        if self.anim_ticks >= self.total_anim_ticks:
            self.slot_timer.stop()
            self._reveal_winners()

    def _reveal_winners(self):
        self.is_rolling = False
        self.btn_roll.setEnabled(True)
        self.audio_player.play_fanfare()

        # Clear existing winner cards
        while self.winners_layout.count():
            item = self.winners_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        category = self.combo_category.currentText().strip()
        ts = datetime.now().strftime("%H:%M:%S")

        # Display winner cards
        summary_names = []
        for idx, w in enumerate(self.winner_candidates, start=1):
            summary_names.append(w["id"])

            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {PALETTE['amber_light']};
                    border: 1.5px solid {PALETTE['amber']};
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)

            lbl_rank = QLabel(f"🏆 WINNER #{idx}")
            lbl_rank.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            lbl_rank.setStyleSheet(f"color: {PALETTE['amber_dark']};")
            card_layout.addWidget(lbl_rank)

            lbl_id = QLabel(f"{w['id']}")
            lbl_id.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            lbl_id.setStyleSheet(f"color: {PALETTE['text_primary']};")
            card_layout.addWidget(lbl_id)

            lbl_name = QLabel(f"— {w['name']}")
            lbl_name.setFont(QFont("Segoe UI", 11, QFont.Weight.Normal))
            lbl_name.setStyleSheet(f"color: {PALETTE['text_secondary']};")
            card_layout.addWidget(lbl_name)
            card_layout.addStretch()

            self.winners_layout.addWidget(card)

            # Insert into audit log table
            row = self.table_log.rowCount()
            self.table_log.insertRow(row)
            self.table_log.setItem(row, 0, QTableWidgetItem(ts))
            self.table_log.setItem(row, 1, QTableWidgetItem(category))
            self.table_log.setItem(row, 2, QTableWidgetItem(w["source"]))
            self.table_log.setItem(row, 3, QTableWidgetItem(w["id"]))
            self.table_log.setItem(row, 4, QTableWidgetItem(w["name"]))

        self.lbl_slot_display.setText(f"🎉 {' & '.join(summary_names)} 🎉")
        self.lbl_slot_sub.setText(f"Awarded: {category} • Verified at {ts}")

    def _copy_log(self):
        rows = self.table_log.rowCount()
        if rows == 0:
            return
        lines = []
        for r in range(rows):
            line = " | ".join(self.table_log.item(r, c).text() for c in range(5))
            lines.append(line)
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copied", "Audit log copied to clipboard!")

    def _clear_log(self):
        self.table_log.setRowCount(0)


# ---------------------------------------------------------------------------
# SCREEN 3: Claim Verifier & Ticket Inspector (PRD 2.5)
# ---------------------------------------------------------------------------
class ClaimVerifierScreen(QWidget):
    """
    Automated cross-check engine with batch registry loader, 3x9 visual grid display,
    called vs. pending cell highlighting, and real-time auto-verdict evaluation.
    """
    def __init__(self, audio_player: AudioPlayer, parent=None):
        super().__init__(parent)
        self.audio_player = audio_player
        self.called_numbers_ref: List[int] = []
        self.current_registry_data: Optional[Dict[str, Any]] = None
        self.current_tickets: List[Dict[str, Any]] = []
        self.active_ticket_idx = 0

        self._init_ui()

    def set_called_numbers(self, called: List[int]):
        self.called_numbers_ref = called
        self._refresh_ticket_view()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Header Control Bar
        header_card = QFrame()
        header_card.setProperty("class", "card-panel")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)

        title = QLabel("🔍 CLAIM VERIFIER & INSPECTOR")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {PALETTE['indigo']};")
        header_layout.addWidget(title)

        # Batch Selector Dropdown
        header_layout.addWidget(QLabel("Batch Registry:"))
        self.combo_batch = QComboBox()
        self.combo_batch.setMinimumWidth(260)
        self.combo_batch.currentIndexChanged.connect(self._on_batch_selected)
        header_layout.addWidget(self.combo_batch)

        btn_refresh_batches = QPushButton("🔄 Refresh")
        btn_refresh_batches.clicked.connect(self.reload_batch_registries)
        header_layout.addWidget(btn_refresh_batches)

        header_layout.addSpacing(16)

        # Ticket ID Search Input
        header_layout.addWidget(QLabel("Ticket ID:"))
        self.txt_search_id = QLineEdit()
        self.txt_search_id.setPlaceholderText("e.g. 001")
        self.txt_search_id.setFixedWidth(90)
        self.txt_search_id.returnPressed.connect(self._on_search_ticket)
        header_layout.addWidget(self.txt_search_id)

        btn_search = QPushButton("Find")
        btn_search.clicked.connect(self._on_search_ticket)
        header_layout.addWidget(btn_search)

        self.btn_prev_ticket = QPushButton("◀ Prev")
        self.btn_prev_ticket.clicked.connect(self._prev_ticket)
        header_layout.addWidget(self.btn_prev_ticket)

        self.btn_next_ticket = QPushButton("Next ▶")
        self.btn_next_ticket.clicked.connect(self._next_ticket)
        header_layout.addWidget(self.btn_next_ticket)

        header_layout.addStretch()
        layout.addWidget(header_card)

        # Grand Auto-Verdict Banner Card
        self.verdict_banner = QFrame()
        self.verdict_banner.setProperty("class", "card-panel")
        self.verdict_layout = QVBoxLayout(self.verdict_banner)
        self.verdict_layout.setContentsMargins(16, 12, 16, 12)

        self.lbl_verdict_title = QLabel("NO TICKET LOADED")
        self.lbl_verdict_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_verdict_title.setStyleSheet(f"color: {PALETTE['text_secondary']};")
        self.verdict_layout.addWidget(self.lbl_verdict_title)

        self.lbl_verdict_details = QLabel("Select an archived batch registry to inspect tickets")
        self.lbl_verdict_details.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 12px;")
        self.verdict_layout.addWidget(self.lbl_verdict_details)
        layout.addWidget(self.verdict_banner)

        # Main Split: 3x9 Ticket Visualizer on Left, Claim Status Checklist on Right
        split_layout = QHBoxLayout()
        split_layout.setSpacing(14)

        # 3x9 Visual Ticket Container (Left)
        ticket_card = QFrame()
        ticket_card.setProperty("class", "card-panel")
        ticket_layout = QVBoxLayout(ticket_card)
        ticket_layout.setContentsMargins(16, 14, 16, 14)
        ticket_layout.setSpacing(10)

        # Ticket Strip Header
        strip_hdr = QHBoxLayout()
        self.lbl_ticket_strip_title = QLabel("TICKET STRIP OVERLAY (3x9)")
        self.lbl_ticket_strip_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        strip_hdr.addWidget(self.lbl_ticket_strip_title)
        strip_hdr.addStretch()

        self.lbl_strip_badge = QLabel("Strip 1 of 2")
        self.lbl_strip_badge.setStyleSheet(
            f"background: {PALETTE['indigo_light']}; color: {PALETTE['indigo']}; "
            f"padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"
        )
        strip_hdr.addWidget(self.lbl_strip_badge)
        ticket_layout.addLayout(strip_hdr)

        # 3x9 Visual Table Grid
        self.grid_ticket = QGridLayout()
        self.grid_ticket.setSpacing(6)
        ticket_layout.addLayout(self.grid_ticket, 1)

        split_layout.addWidget(ticket_card, 2)

        # Claim Condition Checklist Cards (Right)
        checklist_card = QFrame()
        checklist_card.setProperty("class", "card-panel")
        checklist_card.setFixedWidth(340)
        check_layout = QVBoxLayout(checklist_card)
        check_layout.setContentsMargins(16, 14, 16, 14)
        check_layout.setSpacing(10)

        check_hdr = QLabel("🏆 Claim Conditions Status")
        check_hdr.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        check_layout.addWidget(check_hdr)

        self.check_labels: Dict[str, QLabel] = {}
        conditions = [
            ("early_5", "Early 5 (Any 5 Numbers)"),
            ("top_line", "Top Line (Row 1)"),
            ("mid_line", "Middle Line (Row 2)"),
            ("bot_line", "Bottom Line (Row 3)"),
            ("four_corners", "Four Corners"),
            ("full_house", "Full House (All 15 Numbers)")
        ]

        for key, name in conditions:
            box = QFrame()
            box.setProperty("class", "card-subtle")
            b_layout = QVBoxLayout(box)
            b_layout.setContentsMargins(10, 8, 10, 8)
            b_layout.setSpacing(2)

            lbl_n = QLabel(name)
            lbl_n.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            b_layout.addWidget(lbl_n)

            lbl_v = QLabel("Pending evaluation")
            lbl_v.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 11px;")
            b_layout.addWidget(lbl_v)

            self.check_labels[key] = lbl_v
            check_layout.addWidget(box)

        check_layout.addStretch()
        split_layout.addWidget(checklist_card, 1)

        layout.addLayout(split_layout, 1)

        # Load registries initially
        self.reload_batch_registries()

    def reload_batch_registries(self):
        """Scan tickets_archive for *_registry.json files."""
        self.combo_batch.clear()
        if not TICKETS_ARCHIVE_DIR.exists():
            return

        registry_files = sorted(
            list(TICKETS_ARCHIVE_DIR.glob("*_registry.json")),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for p in registry_files:
            clean_name = p.stem.replace("_registry", "")
            self.combo_batch.addItem(clean_name, str(p))

    def _on_batch_selected(self, index: int):
        if index < 0:
            return
        file_path = self.combo_batch.itemData(index)
        if not file_path or not Path(file_path).is_file():
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.current_registry_data = data
            self.current_tickets = data.get("tickets", [])
            self.active_ticket_idx = 0
            self._refresh_ticket_view()
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Could not load batch registry: {e}")

    def _on_search_ticket(self):
        query = self.txt_search_id.text().strip()
        if not query or not self.current_tickets:
            return

        found_idx = -1
        for idx, t in enumerate(self.current_tickets):
            t_id = str(t.get("ticket_id", "")).strip()
            if t_id == query or t_id == query.zfill(3) or str(idx + 1) == query:
                found_idx = idx
                break

        if found_idx >= 0:
            self.active_ticket_idx = found_idx
            self._refresh_ticket_view()
        else:
            QMessageBox.information(self, "Not Found", f"Ticket ID '{query}' not found in active batch.")

    def _prev_ticket(self):
        if self.current_tickets and self.active_ticket_idx > 0:
            self.active_ticket_idx -= 1
            self._refresh_ticket_view()

    def _next_ticket(self):
        if self.current_tickets and self.active_ticket_idx < len(self.current_tickets) - 1:
            self.active_ticket_idx += 1
            self._refresh_ticket_view()

    def _refresh_ticket_view(self):
        """Re-render 3x9 grid and update auto-verdict banner."""
        # Clear grid layout
        while self.grid_ticket.count():
            item = self.grid_ticket.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.current_tickets or self.active_ticket_idx >= len(self.current_tickets):
            self.lbl_verdict_title.setText("NO TICKET SELECTED")
            self.lbl_verdict_details.setText("Choose a valid ticket batch registry")
            return

        ticket = self.current_tickets[self.active_ticket_idx]
        tid = ticket.get("ticket_id", "001")
        strips = ticket.get("strips", [])
        if not strips:
            return

        # Use strip 0 by default
        strip = strips[0]
        self.lbl_ticket_strip_title.setText(f"TICKET #{tid} • 3x9 TAMBOLA GRID")
        self.txt_search_id.setText(str(tid))

        # Flatten strip numbers for claim evaluation
        strip_numbers = []
        row_numbers: List[List[int]] = [[], [], []]
        corners = []

        for r_idx, row in enumerate(strip):
            for c_idx, cell in enumerate(row):
                # cell may be int or dict
                cell_id = cell["id"] if isinstance(cell, dict) else int(cell)

                cell_frame = QFrame()
                c_layout = QVBoxLayout(cell_frame)
                c_layout.setContentsMargins(4, 4, 4, 4)
                c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                if cell_id > 0:
                    strip_numbers.append(cell_id)
                    row_numbers[r_idx].append(cell_id)

                    is_called = cell_id in self.called_numbers_ref
                    s_meta = song_bank.get_song(cell_id)
                    title = s_meta.get("title", f"Track #{cell_id}") if s_meta else f"Track #{cell_id}"

                    lbl_num = QLabel(f"#{cell_id}")
                    lbl_num.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))

                    lbl_title = QLabel(title)
                    lbl_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Normal))
                    lbl_title.setWordWrap(True)
                    lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

                    lbl_badge = QLabel("CALLED ✓" if is_called else "PENDING ⏳")
                    lbl_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))

                    if is_called:
                        cell_frame.setStyleSheet(f"""
                            QFrame {{
                                background: {PALETTE['emerald_light']};
                                border: 1.5px solid {PALETTE['emerald']};
                                border-radius: 6px;
                            }}
                        """)
                        lbl_num.setStyleSheet(f"color: {PALETTE['emerald_dark']};")
                        lbl_title.setStyleSheet(f"color: {PALETTE['emerald_dark']};")
                        lbl_badge.setStyleSheet(f"color: {PALETTE['emerald_dark']}; font-weight: 800;")
                    else:
                        cell_frame.setStyleSheet(f"""
                            QFrame {{
                                background: {PALETTE['coral_light']};
                                border: 1px dashed {PALETTE['coral']};
                                border-radius: 6px;
                            }}
                        """)
                        lbl_num.setStyleSheet(f"color: {PALETTE['coral_dark']};")
                        lbl_title.setStyleSheet(f"color: {PALETTE['coral_dark']};")
                        lbl_badge.setStyleSheet(f"color: {PALETTE['coral_dark']};")

                    c_layout.addWidget(lbl_num)
                    c_layout.addWidget(lbl_title)
                    c_layout.addWidget(lbl_badge)
                else:
                    # Blank Tambola slot
                    cell_frame.setStyleSheet(f"""
                        QFrame {{
                            background: {PALETTE['cell_blank']};
                            border: 1px solid {PALETTE['cell_blank_border']};
                            border-radius: 6px;
                        }}
                    """)
                    lbl_blank = QLabel("—")
                    lbl_blank.setStyleSheet(f"color: {PALETTE['text_muted']}; font-weight: 700;")
                    c_layout.addWidget(lbl_blank)

                self.grid_ticket.addWidget(cell_frame, r_idx, c_idx)

        # Four Corners detection: first and last number in row 1 & row 3
        if row_numbers[0] and row_numbers[2]:
            corners = [row_numbers[0][0], row_numbers[0][-1], row_numbers[2][0], row_numbers[2][-1]]

        # Evaluate Claims
        called_set = set(self.called_numbers_ref)
        strip_called = [n for n in strip_numbers if n in called_set]

        # 1. Early 5
        early_5_valid = len(strip_called) >= 5
        self.check_labels["early_5"].setText(f"✅ VALID ({len(strip_called)}/5 Called)" if early_5_valid else f"⏳ {len(strip_called)}/5 Called")
        self.check_labels["early_5"].setStyleSheet(f"color: {PALETTE['emerald_dark'] if early_5_valid else PALETTE['text_secondary']}; font-weight: {'700' if early_5_valid else 'normal'};")

        # 2. Top Line
        top_called = [n for n in row_numbers[0] if n in called_set]
        top_valid = len(top_called) == len(row_numbers[0]) and len(row_numbers[0]) > 0
        self.check_labels["top_line"].setText("✅ FULL LINE CALLED!" if top_valid else f"⏳ {len(top_called)}/{len(row_numbers[0])} Called")
        self.check_labels["top_line"].setStyleSheet(f"color: {PALETTE['emerald_dark'] if top_valid else PALETTE['text_secondary']}; font-weight: {'700' if top_valid else 'normal'};")

        # 3. Middle Line
        mid_called = [n for n in row_numbers[1] if n in called_set]
        mid_valid = len(mid_called) == len(row_numbers[1]) and len(row_numbers[1]) > 0
        self.check_labels["mid_line"].setText("✅ FULL LINE CALLED!" if mid_valid else f"⏳ {len(mid_called)}/{len(row_numbers[1])} Called")
        self.check_labels["mid_line"].setStyleSheet(f"color: {PALETTE['emerald_dark'] if mid_valid else PALETTE['text_secondary']}; font-weight: {'700' if mid_valid else 'normal'};")

        # 4. Bottom Line
        bot_called = [n for n in row_numbers[2] if n in called_set]
        bot_valid = len(bot_called) == len(row_numbers[2]) and len(row_numbers[2]) > 0
        self.check_labels["bot_line"].setText("✅ FULL LINE CALLED!" if bot_valid else f"⏳ {len(bot_called)}/{len(row_numbers[2])} Called")
        self.check_labels["bot_line"].setStyleSheet(f"color: {PALETTE['emerald_dark'] if bot_valid else PALETTE['text_secondary']}; font-weight: {'700' if bot_valid else 'normal'};")

        # 5. Four Corners
        corners_called = [n for n in corners if n in called_set]
        corners_valid = len(corners_called) == 4 and len(corners) == 4
        self.check_labels["four_corners"].setText("✅ ALL 4 CORNERS CALLED!" if corners_valid else f"⏳ {len(corners_called)}/4 Corners Called")
        self.check_labels["four_corners"].setStyleSheet(f"color: {PALETTE['emerald_dark'] if corners_valid else PALETTE['text_secondary']}; font-weight: {'700' if corners_valid else 'normal'};")

        # 6. Full House
        full_house_valid = len(strip_called) == len(strip_numbers) and len(strip_numbers) > 0
        self.check_labels["full_house"].setText("🏆 FULL HOUSE BINGO WON!" if full_house_valid else f"⏳ {len(strip_called)}/15 Numbers Called")
        self.check_labels["full_house"].setStyleSheet(f"color: {PALETTE['amber_dark'] if full_house_valid else PALETTE['text_secondary']}; font-weight: {'700' if full_house_valid else 'normal'};")

        # Update Grand Banner
        valid_claims = []
        if full_house_valid:
            valid_claims.append("FULL HOUSE 🏆")
        if top_valid:
            valid_claims.append("TOP LINE")
        if mid_valid:
            valid_claims.append("MIDDLE LINE")
        if bot_valid:
            valid_claims.append("BOTTOM LINE")
        if corners_valid:
            valid_claims.append("FOUR CORNERS")
        if early_5_valid:
            valid_claims.append("EARLY 5")

        if valid_claims:
            self.lbl_verdict_title.setText(f"🎉 CLAIM VALID: {' & '.join(valid_claims)} 🎉")
            self.lbl_verdict_title.setStyleSheet(f"color: {PALETTE['emerald_dark']};")
            self.lbl_verdict_details.setText(f"Ticket #{tid} successfully cross-verified against active session ({len(strip_called)}/15 called numbers).")
            self.verdict_banner.setStyleSheet(f"""
                QFrame {{
                    background: {PALETTE['emerald_light']};
                    border: 2px solid {PALETTE['emerald']};
                    border-radius: 12px;
                }}
            """)
        else:
            rem = len(strip_numbers) - len(strip_called)
            self.lbl_verdict_title.setText(f"⏳ CLAIM PENDING: {len(strip_called)} of 15 Numbers Called")
            self.lbl_verdict_title.setStyleSheet(f"color: {PALETTE['text_primary']};")
            self.lbl_verdict_details.setText(f"Ticket #{tid} requires {rem} more calls to complete a full house.")
            self.verdict_banner.setStyleSheet(f"""
                QFrame {{
                    background: {PALETTE['bg_card']};
                    border: 1px solid {PALETTE['border']};
                    border-radius: 12px;
                }}
            """)


# ---------------------------------------------------------------------------
# SCREEN 4: Ticket Generator & Template Studio (PRD 2.1 & 2.2)
# ---------------------------------------------------------------------------
class TicketGeneratorScreen(QWidget):
    """
    Print-ahead batch generator enforcing non-destructive archival, template selection,
    algorithmic mathematical frequency balancing, and direct browser print opening.
    """
    batch_generated = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_template_path: Optional[str] = None
        self.last_generated_html: Optional[str] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Header Title Card
        header_box = QFrame()
        header_box.setProperty("class", "card-panel")
        header_layout = QHBoxLayout(header_box)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("🎫 TICKET GENERATOR & TEMPLATE STUDIO")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {PALETTE['indigo']};")
        header_layout.addWidget(title)
        header_layout.addStretch()

        lbl_safety = QLabel("🛡️ Strict Non-Destructive Archival Guaranteed")
        lbl_safety.setStyleSheet(f"color: {PALETTE['emerald_dark']}; font-size: 11px; font-weight: 700;")
        header_layout.addWidget(lbl_safety)
        layout.addWidget(header_box)

        # Main 2-Column Split
        split_layout = QHBoxLayout()
        split_layout.setSpacing(14)

        # Left Column: Configuration Controls
        form_frame = QFrame()
        form_frame.setProperty("class", "card-panel")
        form_frame.setFixedWidth(460)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(18, 16, 18, 16)
        form_layout.setSpacing(10)

        # 1. Custom Batch Name Input with Live Collision Guard
        form_layout.addWidget(QLabel("Batch / Event Name (e.g. Diwali_Gala_2026):"))
        self.txt_batch_name = QLineEdit()
        self.txt_batch_name.setText(datetime.now().strftime("Musical_Housie_%Y%m%d"))
        self.txt_batch_name.textChanged.connect(self._check_batch_collision)
        form_layout.addWidget(self.txt_batch_name)

        # Live Collision Guard Badge
        self.lbl_collision_status = QLabel("✓ Available batch name")
        self.lbl_collision_status.setStyleSheet(f"color: {PALETTE['emerald_dark']}; font-size: 11px; font-weight: 700;")
        form_layout.addWidget(self.lbl_collision_status)

        # 2. Template Picker
        form_layout.addWidget(QLabel("Background Template Image:"))
        template_row = QHBoxLayout()
        self.combo_templates = QComboBox()
        self._populate_standard_templates()
        self.combo_templates.currentIndexChanged.connect(self._on_template_selected)
        template_row.addWidget(self.combo_templates, 1)

        btn_browse_tpl = QPushButton("Browse...")
        btn_browse_tpl.clicked.connect(self._browse_custom_template)
        template_row.addWidget(btn_browse_tpl)
        form_layout.addLayout(template_row)

        # 3. Sheet Count
        form_layout.addWidget(QLabel("Number of Sheets to Generate:"))
        sheet_row = QHBoxLayout()
        self.spin_sheets = QSpinBox()
        self.spin_sheets.setRange(1, 500)
        self.spin_sheets.setValue(50)
        self.spin_sheets.valueChanged.connect(self._on_sheet_count_changed)
        sheet_row.addWidget(self.spin_sheets, 1)

        self.lbl_ticket_equiv = QLabel("(= 100 Tickets in 2-Strip)")
        self.lbl_ticket_equiv.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 12px; font-weight: 600;")
        sheet_row.addWidget(self.lbl_ticket_equiv)
        form_layout.addLayout(sheet_row)

        # 4. Format & Options
        form_layout.addWidget(QLabel("Format Mode:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["2-strip (Landscape A4)", "1-strip (Portrait A4)"])
        form_layout.addWidget(self.combo_format)

        self.chk_show_song_numbers = QCheckBox("Show Song Index Numbers (#1–90) on Tickets")
        self.chk_show_song_numbers.setChecked(False)
        form_layout.addWidget(self.chk_show_song_numbers)

        self.chk_participant_slots = QCheckBox("Include Participant Name & Mobile Fill Slots")
        self.chk_participant_slots.setChecked(True)
        form_layout.addWidget(self.chk_participant_slots)

        form_layout.addSpacing(6)

        # Action Button: Generate Batch
        self.btn_generate = QPushButton("⚡ Generate Housie Tickets Batch")
        self.btn_generate.setProperty("class", "btn-primary")
        self.btn_generate.setMinimumHeight(44)
        self.btn_generate.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.btn_generate.clicked.connect(self.generate_batch)
        form_layout.addWidget(self.btn_generate)

        # Post-Generation Action Buttons
        post_row = QHBoxLayout()
        self.btn_open_browser = QPushButton("🌐 Open in Browser")
        self.btn_open_browser.setEnabled(False)
        self.btn_open_browser.clicked.connect(self._open_in_browser)
        post_row.addWidget(self.btn_open_browser)

        self.btn_open_folder = QPushButton("📁 Open Archive")
        self.btn_open_folder.clicked.connect(self._open_archive_folder)
        post_row.addWidget(self.btn_open_folder)
        form_layout.addLayout(post_row)

        form_layout.addStretch()
        split_layout.addWidget(form_frame)

        # Right Column: Template Preview & Archived Batches Table
        right_frame = QFrame()
        right_frame.setProperty("class", "card-panel")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(18, 16, 18, 16)
        right_layout.setSpacing(12)

        # Template Preview Thumbnail
        lbl_preview_title = QLabel("Template Preview")
        lbl_preview_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        right_layout.addWidget(lbl_preview_title)

        self.lbl_preview_img = QLabel()
        self.lbl_preview_img.setFixedSize(380, 150)
        self.lbl_preview_img.setStyleSheet(f"background: {PALETTE['bg_card_alt']}; border: 1px dashed {PALETTE['border']}; border-radius: 8px;")
        self.lbl_preview_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.lbl_preview_img)

        # Archived Batches History
        lbl_archive_title = QLabel("Permanently Archived Batches (tickets_archive/):")
        lbl_archive_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        right_layout.addWidget(lbl_archive_title)

        self.table_archive = QTableWidget(0, 4)
        self.table_archive.setHorizontalHeaderLabels(["Batch Name", "HTML File", "Registry JSON", "Action"])
        self.table_archive.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_archive.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.table_archive, 1)

        split_layout.addWidget(right_frame, 1)
        layout.addLayout(split_layout, 1)

        # Initial populate
        self._check_batch_collision()
        self._refresh_archive_table()
        self._update_template_preview()

    def _populate_standard_templates(self):
        self.combo_templates.clear()
        if BRANDING_DIR.exists():
            for f in BRANDING_DIR.glob("*.*"):
                if f.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                    self.combo_templates.addItem(f.name, str(f))

    def _on_template_selected(self, index: int):
        if index >= 0:
            self.selected_template_path = self.combo_templates.itemData(index)
            self._update_template_preview()

    def _browse_custom_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Template Image",
            str(BRANDING_DIR if BRANDING_DIR.exists() else BASE_DIR),
            "Images (*.png *.jpg *.jpeg)"
        )
        if path:
            self.selected_template_path = path
            self.combo_templates.addItem(f"[Custom] {Path(path).name}", path)
            self.combo_templates.setCurrentIndex(self.combo_templates.count() - 1)
            self._update_template_preview()

    def _update_template_preview(self):
        if self.selected_template_path and Path(self.selected_template_path).is_file():
            pix = QPixmap(self.selected_template_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    self.lbl_preview_img.width(), self.lbl_preview_img.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.lbl_preview_img.setPixmap(scaled)
                return
        self.lbl_preview_img.setText("No Template Selected")

    def _on_sheet_count_changed(self, count: int):
        self.lbl_ticket_equiv.setText(f"(= {count * 2} Tickets in 2-Strip)")

    def _check_batch_collision(self):
        """Live validation of batch name against tickets_archive/."""
        raw = self.txt_batch_name.text().strip()
        clean = sanitize_batch_name(raw)
        html_exists = (TICKETS_ARCHIVE_DIR / f"{clean}.html").exists()
        json_exists = (TICKETS_ARCHIVE_DIR / f"{clean}_registry.json").exists()

        if html_exists or json_exists:
            unique_name = resolve_unique_batch_name(clean)
            self.lbl_collision_status.setText(
                f"⚠️ Batch exists! Non-destructive guard will save as '{unique_name}'"
            )
            self.lbl_collision_status.setStyleSheet(f"color: {PALETTE['amber_dark']}; font-size: 11px; font-weight: 700;")
        else:
            self.lbl_collision_status.setText("✓ Unique batch name available")
            self.lbl_collision_status.setStyleSheet(f"color: {PALETTE['emerald_dark']}; font-size: 11px; font-weight: 700;")

    def generate_batch(self):
        raw_name = self.txt_batch_name.text().strip()
        sheets = self.spin_sheets.value()
        format_mode = "2-strip" if self.combo_format.currentIndex() == 0 else "1-strip"
        show_numbers = self.chk_show_song_numbers.isChecked()
        show_slots = self.chk_participant_slots.isChecked()

        # Non-destructive check & prompt
        clean = sanitize_batch_name(raw_name)
        target_html = TICKETS_ARCHIVE_DIR / f"{clean}.html"
        if target_html.exists():
            resolved = resolve_unique_batch_name(clean)
            reply = QMessageBox.question(
                self, "Non-Destructive Batch Archival",
                f"A batch named '{clean}' already exists in tickets_archive/.\n\n"
                f"To protect previously printed tickets from being overwritten or lost,\n"
                f"this batch will be saved as: '{resolved}'.\n\nProceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            batch_to_use = resolved
        else:
            batch_to_use = clean

        try:
            out_file = generate_housie_tickets(
                num_sheets=sheets,
                format_mode=format_mode,
                template_path=self.selected_template_path,
                show_participant_slots=show_slots,
                batch_name=batch_to_use,
                show_song_number=show_numbers,
                save_to_database=True
            )

            self.last_generated_html = out_file
            self.btn_open_browser.setEnabled(True)
            self._refresh_archive_table()
            self._check_batch_collision()

            QMessageBox.information(
                self, "Batch Generation Success",
                f"Successfully generated {sheets} sheets ({sheets * 2 if format_mode == '2-strip' else sheets} tickets)!\n\n"
                f"Saved to: {Path(out_file).name}\nRegistry: {Path(out_file).stem}_registry.json"
            )

            self.batch_generated.emit(str(out_file))

        except Exception as e:
            QMessageBox.critical(self, "Generation Error", f"Failed to generate tickets: {e}")

    def _open_in_browser(self):
        if self.last_generated_html and Path(self.last_generated_html).is_file():
            webbrowser.open(Path(self.last_generated_html).resolve().as_uri())

    def _open_archive_folder(self):
        if TICKETS_ARCHIVE_DIR.exists():
            os.startfile(str(TICKETS_ARCHIVE_DIR.resolve()))

    def _refresh_archive_table(self):
        self.table_archive.setRowCount(0)
        if not TICKETS_ARCHIVE_DIR.exists():
            return

        html_files = sorted(
            list(TICKETS_ARCHIVE_DIR.glob("*.html")),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for p in html_files:
            clean_name = p.stem
            reg_p = TICKETS_ARCHIVE_DIR / f"{clean_name}_registry.json"

            row = self.table_archive.rowCount()
            self.table_archive.insertRow(row)

            self.table_archive.setItem(row, 0, QTableWidgetItem(clean_name))
            self.table_archive.setItem(row, 1, QTableWidgetItem(f"{p.stat().st_size // 1024} KB"))
            self.table_archive.setItem(row, 2, QTableWidgetItem("✓ Present" if reg_p.exists() else "Missing"))

            btn_open = QPushButton("Open HTML")
            btn_open.setStyleSheet("font-size: 11px; padding: 2px 8px;")
            btn_open.clicked.connect(lambda _, fp=p: webbrowser.open(fp.resolve().as_uri()))
            self.table_archive.setCellWidget(row, 3, btn_open)


# ---------------------------------------------------------------------------
# MAIN APPLICATION CONTAINER & NAVIGATION HUB
# ---------------------------------------------------------------------------
class MusicalHousieApp(QMainWindow):
    """
    Primary desktop window for Musical Housie (Tambola).
    Ties together Live Caller Stage, Lucky Draw Raffle, Claim Verifier,
    and Ticket Generator into a cohesive pastel-themed master application.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Musical Housie (Tambola) — Offline Master Studio & Caller")
        self.resize(1340, 860)
        self.setMinimumSize(1100, 740)

        # Shared Pygame Audio Controller
        self.audio_player = AudioPlayer()

        self._apply_theme()
        self._init_ui()
        self._connect_signals()

    def _apply_theme(self):
        self.setStyleSheet(GLOBAL_STYLESHEET)

    def _init_ui(self):
        root = QWidget()
        root.setObjectName("root_container")
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(10)

        # Top App Branding & System Bar
        nav_header = QHBoxLayout()
        nav_header.setSpacing(12)

        logo_title = QLabel("🎵 MUSICAL HOUSIE")
        logo_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        logo_title.setStyleSheet(f"color: {PALETTE['indigo']}; letter-spacing: 0.5px;")
        nav_header.addWidget(logo_title)

        badge_offline = QLabel("🟢 OFFLINE MASTER STUDIO")
        badge_offline.setStyleSheet(
            f"background: {PALETTE['emerald_light']}; color: {PALETTE['emerald_dark']}; "
            f"font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px;"
        )
        nav_header.addWidget(badge_offline)

        nav_header.addStretch()

        # Global Session Summary Pill
        self.lbl_global_summary = QLabel("Active Session: 0 / 90 Numbers Called")
        self.lbl_global_summary.setStyleSheet(
            f"background: {PALETTE['bg_card']}; border: 1px solid {PALETTE['border']}; "
            f"color: {PALETTE['text_secondary']}; font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 8px;"
        )
        nav_header.addWidget(self.lbl_global_summary)

        # Header Quick Actions
        btn_quick_reset = QPushButton("Reset Game")
        btn_quick_reset.setStyleSheet(f"font-size: 11px; color: {PALETTE['coral']}; border: 1px solid {PALETTE['coral']};")
        btn_quick_reset.clicked.connect(self._on_header_reset)
        nav_header.addWidget(btn_quick_reset)

        root_layout.addLayout(nav_header)

        # Tab Navigation Container
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # 4 Core Screens
        self.screen_caller = LiveCallerStageScreen(self.audio_player, self)
        self.screen_raffle = LuckyDrawScreen(self.audio_player, self)
        self.screen_verifier = ClaimVerifierScreen(self.audio_player, self)
        self.screen_generator = TicketGeneratorScreen(self)

        self.tabs.addTab(self.screen_caller, "🎙️ Live Caller & Master Stage")
        self.tabs.addTab(self.screen_raffle, "🎰 Lucky Draw & Raffle")
        self.tabs.addTab(self.screen_verifier, "🔍 Claim Verifier & Inspector")
        self.tabs.addTab(self.screen_generator, "🎫 Ticket Generator Studio")

        root_layout.addWidget(self.tabs, 1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"background: {PALETTE['bg_card']}; color: {PALETTE['text_muted']}; font-size: 11px; border-top: 1px solid {PALETTE['border']};")
        self.status_bar.showMessage("Musical Housie Offline Studio • Zero Cloud Dependencies • Non-Destructive Storage Engine Ready")
        self.setStatusBar(self.status_bar)

    def _connect_signals(self):
        # Sync game state across screens
        self.screen_caller.number_called.connect(self._sync_state_on_number_called)
        self.screen_caller.game_reset.connect(self._sync_state_on_reset)
        self.screen_generator.batch_generated.connect(self._on_batch_generated)

    def _sync_state_on_number_called(self, num: int):
        called = self.screen_caller.called_numbers
        count = len(called)
        self.lbl_global_summary.setText(f"Active Session: {count} / 90 Numbers Called (Last: #{num:02d})")
        self.screen_raffle.set_called_numbers(called)
        self.screen_verifier.set_called_numbers(called)

    def _sync_state_on_reset(self):
        self.lbl_global_summary.setText("Active Session: 0 / 90 Numbers Called")
        self.screen_raffle.set_called_numbers([])
        self.screen_verifier.set_called_numbers([])

    def _on_header_reset(self):
        self.screen_caller.confirm_reset_game()

    def _on_batch_generated(self, html_path: str):
        # Auto refresh verifier dropdown
        self.screen_verifier.reload_batch_registries()
        self.status_bar.showMessage(f"Archived new batch: {Path(html_path).name}", 5000)

    def keyPressEvent(self, event):
        # Spacebar shortcut to draw next track when caller screen is active
        if event.key() == Qt.Key.Key_Space:
            if self.tabs.currentWidget() == self.screen_caller:
                self.screen_caller.draw_next_track()
                event.accept()
                return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.audio_player.stop()
        event.accept()


# ---------------------------------------------------------------------------
# APPLICATION ENTRY POINT
# ---------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Musical Housie")
    app.setStyle("Fusion")

    window = MusicalHousieApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
