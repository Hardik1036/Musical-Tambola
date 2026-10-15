"""
Musical Housie (Tambola) - Master Desktop Application & Host Studio
===================================================================
A complete, production-grade, multi-screen offline desktop application
featuring a solid off-white/light theme (#F4F7FC), solid white cards (#FFFFFF),
crisp borders (#E2E8F4), and rich micro-interactions:
  - Screen 1: Live Ball Roller & Caller Stage (Physics-based lotto ball chute & roll,
              Hero calling deck, Pygame audio engine, master 10x9 calling matrix)
  - Screen 2: 3D Particle Audio Sphere of Dots (Fibonacci lattice distribution,
              continuous 3D rotation, real-time audio beat modulation & breathing)
  - Screen 3: Lucky Draw & Slot Machine Roller (Mechanical rotating digit drums with
              motion blur, configurable winners, tie-breaker categories, persistent audit log)
  - Screen 4: Claim Verifier & Ticket Inspector (Batch registry auto-loader,
              interactive 3x9 visual grid overlay, real-time auto-verdict engine)
  - Screen 5: Ticket Generator & Template Studio (Print-ahead batch generator,
              STRICT non-destructive collision protection, template picker & browser)

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
    QFont, QColor, QIcon, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient,
    QPainterPath, QPixmap, QRect, QRectF, QPolygon,
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
# Design System & Color Palette Tokens (Off-White Solid Theme)
# ---------------------------------------------------------------------------
PALETTE = {
    "bg_main": "#F4F7FC",          # Solid off-white main background
    "bg_card": "#FFFFFF",          # Pure white container cards
    "bg_card_alt": "#F8FAFD",      # Light tinted card
    "border": "#E2E8F4",           # Crisp border
    "border_light": "#EDF2F7",     # Ultra-subtle border
    "border_focus": "#4F46E5",     # Soft indigo border highlight

    "indigo": "#4F46E5",           # Soft Indigo (Primary action)
    "indigo_hover": "#4338CA",
    "indigo_light": "#EEF2FF",
    "indigo_dark": "#3730A3",

    "emerald": "#059669",          # Emerald (Called / Verified / Success)
    "emerald_hover": "#047857",
    "emerald_light": "#ECFDF5",
    "emerald_dark": "#065F46",

    "coral": "#F43F5E",            # Light Coral (Pending / Warning / Alert)
    "coral_hover": "#E11D48",
    "coral_light": "#FFF1F2",
    "coral_dark": "#9F1239",

    "amber": "#D97706",            # Amber / Gold (Active Track / Highlight)
    "amber_hover": "#B45309",
    "amber_light": "#FFFBEB",
    "amber_dark": "#78350F",

    "text_primary": "#0F172A",     # Dark Slate primary text
    "text_secondary": "#475569",   # Medium Slate secondary text
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
    padding: 11px 20px;
    margin-right: 6px;
    margin-top: 6px;
    border: 1px solid {PALETTE['border']};
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    min-width: 140px;
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
    font-weight: 600;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {PALETTE['bg_card_alt']};
    border-color: {PALETTE['indigo']};
    color: {PALETTE['indigo']};
}}

QPushButton:pressed {{
    background-color: {PALETTE['indigo_light']};
}}

QPushButton.btn-primary {{
    background-color: {PALETTE['indigo']};
    color: {PALETTE['text_white']};
    border: 1px solid {PALETTE['indigo']};
}}

QPushButton.btn-primary:hover {{
    background-color: {PALETTE['indigo_hover']};
    border-color: {PALETTE['indigo_hover']};
    color: {PALETTE['text_white']};
}}

QPushButton.btn-emerald {{
    background-color: {PALETTE['emerald']};
    color: {PALETTE['text_white']};
    border: 1px solid {PALETTE['emerald']};
}}

QPushButton.btn-emerald:hover {{
    background-color: {PALETTE['emerald_hover']};
    border-color: {PALETTE['emerald_hover']};
    color: {PALETTE['text_white']};
}}

QPushButton.btn-amber {{
    background-color: {PALETTE['amber']};
    color: {PALETTE['text_white']};
    border: 1px solid {PALETTE['amber']};
}}

QPushButton.btn-amber:hover {{
    background-color: {PALETTE['amber_hover']};
    border-color: {PALETTE['amber_hover']};
    color: {PALETTE['text_white']};
}}

QPushButton.btn-coral {{
    background-color: {PALETTE['coral']};
    color: {PALETTE['text_white']};
    border: 1px solid {PALETTE['coral']};
}}

QPushButton.btn-coral:hover {{
    background-color: {PALETTE['coral_hover']};
    border-color: {PALETTE['coral_hover']};
    color: {PALETTE['text_white']};
}}

/* Inputs & Combos */
QLineEdit, QSpinBox, QComboBox {{
    background-color: {PALETTE['bg_card']};
    color: {PALETTE['text_primary']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1.5px solid {PALETTE['indigo']};
    background-color: #FFFFFF;
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
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
    border: 2px solid #FFFFFF;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: {PALETTE['indigo_hover']};
}}

/* Tables */
QTableWidget {{
    background-color: {PALETTE['bg_card']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    gridline-color: {PALETTE['border_light']};
    font-size: 12px;
}}

QHeaderView::section {{
    background-color: {PALETTE['bg_card_alt']};
    color: {PALETTE['text_secondary']};
    font-weight: 700;
    border: none;
    border-bottom: 1px solid {PALETTE['border']};
    padding: 6px 10px;
}}

QScrollBar:vertical {{
    border: none;
    background: {PALETTE['bg_main']};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {PALETTE['border']};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {PALETTE['text_muted']};
}}
"""


# ---------------------------------------------------------------------------
# WIDGET 1: Interactive Physics-Based Lotto Ball Drop & Chute Roller
# ---------------------------------------------------------------------------
class LottoBallChuteWidget(QWidget):
    """
    Simulates a high-fidelity lotto ball dropping through an acrylic chute,
    bouncing with physical damping, and rolling 360° across a deceleration track
    into the hero cradle socket before revealing the drawn number.
    """
    ball_settled = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(230)

        # Simulation state
        self.current_number: Optional[int] = None
        self.is_animating = False
        self.phase = "idle"  # "idle", "drop", "bounce", "roll", "settled"

        # Ball physics coordinates
        self.ball_radius = 38.0
        self.ball_x = 0.0
        self.ball_y = 0.0
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.ball_angle = 0.0
        self.bounce_count = 0

        # Visual pop & pulse on settle
        self.settle_scale = 1.0
        self.settle_anim_tick = 0
        self.pulse_ring = 0.0

        # Animation timer (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step_physics)

    def trigger_drop(self, number: int):
        """Initiate physical lotto ball drop and roll for the drawn number."""
        self.current_number = number
        self.is_animating = True
        self.phase = "drop"
        self.bounce_count = 0
        self.settle_scale = 1.0
        self.settle_anim_tick = 0
        self.pulse_ring = 0.0

        w = max(280, self.width())
        # Chute entry point: top-left area
        self.ball_x = 55.0
        self.ball_y = -self.ball_radius
        self.vel_x = 1.2
        self.vel_y = 3.5
        self.ball_angle = 0.0

        self.timer.start(16)
        self.update()

    def reset(self):
        """Clear current ball and return to idle ready state."""
        self.timer.stop()
        self.is_animating = False
        self.phase = "idle"
        self.current_number = None
        self.ball_angle = 0.0
        self.update()

    def _step_physics(self):
        w = float(self.width())
        h = float(self.height())
        ground_y = h - 55.0
        cradle_x = w / 2.0

        if self.phase == "drop":
            # Gravity acceleration down chute
            self.vel_y += 0.85
            self.ball_y += self.vel_y
            self.ball_x += self.vel_x
            self.ball_angle += 0.08

            # Hit the curved chute bottom / bounce plate
            if self.ball_y >= ground_y - self.ball_radius:
                self.ball_y = ground_y - self.ball_radius
                self.vel_y = -self.vel_y * 0.42
                self.bounce_count += 1
                self.phase = "bounce"
                # Impart strong forward roll velocity
                self.vel_x = 7.5

        elif self.phase == "bounce":
            self.vel_y += 0.85
            self.ball_y += self.vel_y
            self.ball_x += self.vel_x
            self.ball_angle += (self.vel_x / self.ball_radius) * 1.5

            if self.ball_y >= ground_y - self.ball_radius:
                self.ball_y = ground_y - self.ball_radius
                if abs(self.vel_y) < 1.5 or self.bounce_count >= 2:
                    self.vel_y = 0.0
                    self.phase = "roll"
                else:
                    self.vel_y = -self.vel_y * 0.35
                    self.bounce_count += 1

        elif self.phase == "roll":
            # Rolling across horizontal tray with deceleration
            self.ball_x += self.vel_x
            self.ball_angle += (self.vel_x / self.ball_radius)
            self.vel_x *= 0.955

            # Transition toward center cradle
            dist_to_cradle = cradle_x - self.ball_x
            if self.ball_x < cradle_x and dist_to_cradle > 0:
                # Keep rolling toward cradle
                if self.vel_x < 1.0:
                    self.vel_x = 1.0
            else:
                # Settling into cradle
                if abs(self.vel_x) < 0.6:
                    self.ball_x = cradle_x
                    self.vel_x = 0.0
                    self.phase = "settled"
                    self.settle_scale = 1.25
                    if self.current_number is not None:
                        self.ball_settled.emit(self.current_number)

        elif self.phase == "settled":
            # Scale pop and radial aura breathing
            self.settle_anim_tick += 1
            if self.settle_scale > 1.0:
                self.settle_scale = max(1.0, self.settle_scale - 0.02)
            self.pulse_ring = (self.pulse_ring + 0.08) % (math.pi * 2)
            if self.settle_anim_tick > 45:
                # Stop physics timer once fully settled
                self.is_animating = False
                self.timer.stop()

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = float(self.width())
        h = float(self.height())
        ground_y = h - 55.0
        cradle_x = w / 2.0

        # 1. Background Track & Acrylic Chute Infrastructure
        # Chute Tube (Top Left)
        chute_path = QPainterPath()
        chute_path.moveTo(35.0, 10.0)
        chute_path.lineTo(75.0, 10.0)
        chute_path.lineTo(75.0, ground_y - 30.0)
        chute_path.quadTo(75.0, ground_y, 115.0, ground_y)
        chute_path.lineTo(w - 30.0, ground_y)
        chute_path.lineTo(w - 30.0, ground_y + 12.0)
        chute_path.lineTo(110.0, ground_y + 12.0)
        chute_path.quadTo(55.0, ground_y + 12.0, 55.0, ground_y - 25.0)
        chute_path.lineTo(35.0, 10.0)

        # Draw acrylic chute styling
        chute_grad = QLinearGradient(35.0, 10.0, 95.0, ground_y)
        chute_grad.setColorAt(0.0, QColor(255, 255, 255, 180))
        chute_grad.setColorAt(0.5, QColor(226, 232, 244, 140))
        chute_grad.setColorAt(1.0, QColor(241, 245, 249, 100))
        painter.setBrush(QBrush(chute_grad))
        painter.setPen(QPen(QColor(PALETTE["border"]), 1.8))
        painter.drawPath(chute_path)

        # Chute funnel mouth at top
        painter.setBrush(QBrush(QColor(PALETTE["indigo_light"])))
        painter.setPen(QPen(QColor(PALETTE["indigo"]), 1.5))
        painter.drawRoundedRect(QRectF(30.0, 6.0, 50.0, 12.0), 4.0, 4.0)

        # Horizontal Rolling Runway Rails
        painter.setPen(QPen(QColor(PALETTE["border"]), 3.0))
        painter.drawLine(int(85.0), int(ground_y + 4.0), int(w - 35.0), int(ground_y + 4.0))

        # Center Hero Cradle Pedestal
        cradle_w = 90.0
        cradle_rect = QRectF(cradle_x - cradle_w / 2.0, ground_y - 4.0, cradle_w, 24.0)
        cradle_grad = QLinearGradient(0, ground_y, 0, ground_y + 24.0)
        cradle_grad.setColorAt(0.0, QColor(PALETTE["bg_card"]))
        cradle_grad.setColorAt(1.0, QColor(PALETTE["bg_card_alt"]))
        painter.setBrush(QBrush(cradle_grad))
        painter.setPen(QPen(QColor(PALETTE["border"]), 1.5))
        painter.drawRoundedRect(cradle_rect, 8.0, 8.0)

        # Cradle Notch
        painter.setBrush(QBrush(QColor(PALETTE["border_light"])))
        painter.drawEllipse(QRectF(cradle_x - 30.0, ground_y - 2.0, 60.0, 10.0))

        # 2. Render Lotto Ball (Animated or Ready State)
        ball_r = self.ball_radius * self.settle_scale
        bx = self.ball_x if self.is_animating or self.phase == "settled" else cradle_x
        by = self.ball_y if self.is_animating or self.phase == "settled" else (ground_y - self.ball_radius)

        # Cast Shadow beneath ball
        shadow_w = ball_r * 1.6
        shadow_h = 10.0 * (self.settle_scale if self.phase == "settled" else 0.8)
        shadow_y = ground_y - 2.0
        shadow_grad = QRadialGradient(bx, shadow_y, shadow_w / 2.0)
        shadow_grad.setColorAt(0.0, QColor(15, 23, 42, 70))
        shadow_grad.setColorAt(1.0, QColor(15, 23, 42, 0))
        painter.setBrush(QBrush(shadow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(bx - shadow_w / 2.0, shadow_y - shadow_h / 2.0, shadow_w, shadow_h))

        # Pulsing Ring around ball when settled
        if self.phase == "settled" and self.current_number is not None:
            ring_extra = 8.0 + math.sin(self.pulse_ring) * 4.0
            ring_r = ball_r + ring_extra
            ring_pen = QPen(QColor(PALETTE["amber"]), 2.2)
            ring_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(bx - ring_r, by - ring_r, ring_r * 2.0, ring_r * 2.0))

        # 3D Shaded Lotto Ball Sphere
        ball_grad = QRadialGradient(bx - ball_r * 0.35, by - ball_r * 0.35, ball_r * 1.4)
        if self.current_number is not None:
            # Vibrant 3D Amber / Gold Lotto Ball
            ball_grad.setColorAt(0.0, QColor("#FFFBEB"))
            ball_grad.setColorAt(0.25, QColor("#FDE68A"))
            ball_grad.setColorAt(0.65, QColor(PALETTE["amber"]))
            ball_grad.setColorAt(1.0, QColor(PALETTE["amber_dark"]))
            border_col = QColor(PALETTE["amber_dark"])
        else:
            # Idle Clean White / Silver Ball
            ball_grad.setColorAt(0.0, QColor("#FFFFFF"))
            ball_grad.setColorAt(0.5, QColor("#F1F5F9"))
            ball_grad.setColorAt(1.0, QColor(PALETTE["border"]))
            border_col = QColor(PALETTE["border"])

        painter.setBrush(QBrush(ball_grad))
        painter.setPen(QPen(border_col, 2.0))
        painter.drawEllipse(QRectF(bx - ball_r, by - ball_r, ball_r * 2.0, ball_r * 2.0))

        # Inner Decorative Lotto Ring & Specular Highlight
        painter.save()
        painter.translate(bx, by)
        if self.is_animating and self.phase in ("drop", "bounce", "roll"):
            painter.rotate(math.degrees(self.ball_angle))

        # Inner circular number disc
        disc_r = ball_r * 0.65
        painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
        painter.setPen(QPen(QColor(border_col), 1.2))
        painter.drawEllipse(QRectF(-disc_r, -disc_r, disc_r * 2.0, disc_r * 2.0))

        # Number or Ready Label
        if self.current_number is not None and (self.phase == "settled" or not self.is_animating):
            painter.setPen(QColor(PALETTE["amber_dark"]))
            painter.setFont(QFont("Segoe UI", int(24 * self.settle_scale), QFont.Weight.Bold))
            num_text = f"#{self.current_number:02d}"
            painter.drawText(QRectF(-disc_r, -disc_r, disc_r * 2.0, disc_r * 2.0),
                             Qt.AlignmentFlag.AlignCenter, num_text)
        elif self.current_number is not None and self.is_animating:
            # Motion spinning lines while rolling
            painter.setPen(QPen(QColor(PALETTE["amber_dark"]), 3.0))
            painter.drawLine(int(-disc_r * 0.7), 0, int(disc_r * 0.7), 0)
            painter.drawLine(0, int(-disc_r * 0.7), 0, int(disc_r * 0.7))
        else:
            painter.setPen(QColor(PALETTE["text_muted"]))
            painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            painter.drawText(QRectF(-disc_r, -disc_r, disc_r * 2.0, disc_r * 2.0),
                             Qt.AlignmentFlag.AlignCenter, "READY")

        painter.restore()

        # Specular light gleam on ball crown
        gleam_w = ball_r * 0.5
        gleam_h = ball_r * 0.25
        painter.setBrush(QBrush(QColor(255, 255, 255, 160)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(bx - ball_r * 0.45, by - ball_r * 0.65, gleam_w, gleam_h))


# ---------------------------------------------------------------------------
# WIDGET 2: 3D Particle Audio Sphere Visualizer Canvas (Fibonacci Lattice)
# ---------------------------------------------------------------------------
class ParticleAudioSphereWidget(QWidget):
    """
    Renders a continuous 3D rotating particle sphere using a Fibonacci lattice
    distribution (~360 points) with depth shading, perspective projection,
    and real-time audio beat modulation that expands and breathes with sound.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # 3D Lattice Constants
        self.num_points = 360
        self.base_points: List[Tuple[float, float, float]] = []
        self._generate_fibonacci_sphere()

        # Dynamic Visualizer Parameters
        self.base_radius = 160.0
        self.dynamic_radius = 160.0
        self.yaw = 0.0
        self.pitch = 0.0
        self.yaw_speed = 0.012
        self.pitch_speed = 0.007

        # Beat Modulation State
        self.modulate_beat = True
        self.is_audio_playing = False
        self.beat_phase = 0.0
        self.beat_energy = 0.0
        self.harmonic_time = 0.0

        # Animation Loop (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step_frame)
        self.timer.start(16)

    def _generate_fibonacci_sphere(self):
        """Precalculate spherical coordinates using the golden ratio spiral."""
        self.base_points.clear()
        phi_golden = math.pi * (3.0 - math.sqrt(5.0))  # ~2.39996 rad

        for i in range(self.num_points):
            y = 1.0 - (float(i) / float(self.num_points - 1)) * 2.0  # +1 to -1
            r = math.sqrt(max(0.0, 1.0 - y * y))
            theta = phi_golden * float(i)
            x = math.cos(theta) * r
            z = math.sin(theta) * r
            self.base_points.append((x, y, z))

    def set_audio_playing(self, playing: bool):
        """Link sphere breathing rhythm to audio playback engine state."""
        self.is_audio_playing = playing

    def set_beat_modulation(self, enabled: bool):
        self.modulate_beat = enabled

    def set_rotation_speed(self, speed_factor: float):
        self.yaw_speed = 0.012 * speed_factor
        self.pitch_speed = 0.007 * speed_factor

    def set_sphere_scale(self, scale_px: float):
        self.base_radius = scale_px

    def _step_frame(self):
        # Update 3D rotation angles
        self.yaw = (self.yaw + self.yaw_speed) % (math.pi * 2)
        self.pitch = (self.pitch + self.pitch_speed) % (math.pi * 2)
        self.harmonic_time += 0.04

        # Beat modulation physics
        if self.modulate_beat:
            # If audio is playing, pulse with bass-driven breathing
            if self.is_audio_playing:
                self.beat_phase = (self.beat_phase + 0.12) % (math.pi * 2)
                bass_pulse = math.sin(self.beat_phase) ** 4
                harmonic = math.sin(self.harmonic_time * 2.5) * 0.15
                self.beat_energy = bass_pulse * 0.28 + harmonic
            else:
                # Gentle ambient breathing when idle
                self.beat_energy = math.sin(self.harmonic_time * 1.2) * 0.08

            self.dynamic_radius = self.base_radius * (1.0 + self.beat_energy)
        else:
            self.dynamic_radius = self.base_radius

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = float(self.width()) / 2.0
        cy = float(self.height()) / 2.0
        camera_dist = 420.0
        fov = 380.0

        # Precompute rotation trigonometry
        cos_y, sin_y = math.cos(self.yaw), math.sin(self.yaw)
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)

        # Transform and project 3D points
        projected = []
        for idx, (bx, by, bz) in enumerate(self.base_points):
            # Dynamic ripple per point
            ripple = 0.0
            if self.modulate_beat and self.is_audio_playing:
                ripple = math.sin(self.harmonic_time * 3.0 + float(idx) * 0.1) * 6.0

            r_point = self.dynamic_radius + ripple

            # 1. Yaw rotation (around Y axis)
            x1 = bx * cos_y + bz * sin_y
            y1 = by
            z1 = -bx * sin_y + bz * cos_y

            # 2. Pitch rotation (around X axis)
            x2 = x1
            y2 = y1 * cos_p - z1 * sin_p
            z2 = y1 * sin_p + z1 * cos_p

            # 3. Perspective projection
            world_z = z2 * r_point
            proj_scale = fov / (camera_dist + world_z)
            screen_x = cx + (x2 * r_point) * proj_scale
            screen_y = cy + (y2 * r_point) * proj_scale

            # Depth normalized: -1.0 (furthest) to +1.0 (closest)
            depth_norm = z2
            projected.append((depth_norm, screen_x, screen_y, idx))

        # Sort points back-to-front for proper depth buffering
        projected.sort(key=lambda p: p[0])

        # Draw subtle foreground constellation web between close front particles
        painter.setPen(QPen(QColor(79, 70, 229, 35), 0.8))
        front_points = [p for p in projected if p[0] > 0.35]
        for i in range(0, len(front_points), 3):
            p1 = front_points[i]
            for j in range(i + 1, min(i + 4, len(front_points))):
                p2 = front_points[j]
                dx = p1[1] - p2[1]
                dy = p1[2] - p2[2]
                if dx * dx + dy * dy < 1600.0:  # Distance < 40px
                    painter.drawLine(int(p1[1]), int(p1[2]), int(p2[1]), int(p2[2]))

        # Render 3D Dots with depth-scaled size and alpha shading
        for depth_norm, sx, sy, idx in projected:
            # Map depth (-1 to 1) to radius (1.4px to 5.2px) and opacity (0.2 to 1.0)
            t = (depth_norm + 1.0) / 2.0  # 0.0 to 1.0
            dot_r = 1.4 + t * 3.8
            alpha = int(50 + t * 205)

            # Chromatic distribution across latitude and depth
            if t > 0.75:
                # Golden / Amber highlight for closest particles
                col = QColor(PALETTE["amber"])
                col.setAlpha(alpha)
            elif t > 0.4:
                # Soft Indigo primary body
                col = QColor(PALETTE["indigo"])
                col.setAlpha(alpha)
            else:
                # Emerald / Teal background particles
                col = QColor(PALETTE["emerald"])
                col.setAlpha(alpha)

            painter.setBrush(QBrush(col))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(sx - dot_r, sy - dot_r, dot_r * 2.0, dot_r * 2.0))


# ---------------------------------------------------------------------------
# WIDGET 3: Mechanical Slot Machine Drum Reel (Lucky Draw)
# ---------------------------------------------------------------------------
class SlotMachineDrumWidget(QWidget):
    """
    Renders animated mechanical slot-machine digit drums with 3D cylindrical
    bevels, motion blur during rapid spinning, and sequential locked clicks.
    """
    draw_finished = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 150)
        self.setFixedHeight(160)

        self.num_drums = 3
        self.drum_values = [0, 0, 0]
        self.drum_offsets = [0.0, 0.0, 0.0]
        self.drum_speeds = [0.0, 0.0, 0.0]
        self.drum_targets = [0, 0, 0]
        self.drum_locked = [True, True, True]

        self.is_spinning = False
        self.spin_ticks = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step_spin)

    def spin_to_number(self, target_num: int):
        """Spin mechanical drums and sequentially stop on target number (0-999)."""
        self.target_num = target_num
        digits = [
            (target_num // 100) % 10,
            (target_num // 10) % 10,
            target_num % 10
        ]
        self.drum_targets = digits
        self.drum_locked = [False, False, False]
        self.drum_speeds = [18.0, 22.0, 26.0]
        self.is_spinning = True
        self.spin_ticks = 0

        self.timer.start(16)
        self.update()

    def _step_spin(self):
        self.spin_ticks += 1
        all_locked = True

        for i in range(self.num_drums):
            if not self.drum_locked[i]:
                all_locked = False
                self.drum_offsets[i] = (self.drum_offsets[i] + self.drum_speeds[i]) % 100.0

                # Sequential stopping milestones (Drum 1 at ~45 ticks, Drum 2 at ~75, Drum 3 at ~105)
                stop_tick = 45 + i * 30
                if self.spin_ticks >= stop_tick:
                    # Decelerate smoothly
                    self.drum_speeds[i] *= 0.88
                    if self.drum_speeds[i] < 1.0:
                        self.drum_offsets[i] = float(self.drum_targets[i] * 10.0)
                        self.drum_values[i] = self.drum_targets[i]
                        self.drum_locked[i] = True

        self.update()

        if all_locked and self.is_spinning:
            self.is_spinning = False
            self.timer.stop()
            self.draw_finished.emit(self.drum_values)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        # Outer Metallic Chrome Chassis
        chassis_rect = QRectF(10.0, 10.0, w - 20.0, h - 20.0)
        chassis_grad = QLinearGradient(0, 10.0, 0, h - 10.0)
        chassis_grad.setColorAt(0.0, QColor("#E2E8F0"))
        chassis_grad.setColorAt(0.5, QColor("#FFFFFF"))
        chassis_grad.setColorAt(1.0, QColor("#CBD5E1"))
        painter.setBrush(QBrush(chassis_grad))
        painter.setPen(QPen(QColor(PALETTE["border"]), 2.0))
        painter.drawRoundedRect(chassis_rect, 14.0, 14.0)

        # Inner Drum Display Window
        window_rect = QRectF(24.0, 24.0, w - 48.0, h - 48.0)
        painter.setBrush(QBrush(QColor(PALETTE["bg_main"])))
        painter.setPen(QPen(QColor(PALETTE["border"]), 1.5))
        painter.drawRoundedRect(window_rect, 8.0, 8.0)

        drum_spacing = 16.0
        total_drum_w = window_rect.width() - (drum_spacing * (self.num_drums + 1))
        drum_w = total_drum_w / float(self.num_drums)
        drum_h = window_rect.height() - 16.0
        drum_top = window_rect.top() + 8.0

        for i in range(self.num_drums):
            dx = window_rect.left() + drum_spacing + i * (drum_w + drum_spacing)
            drect = QRectF(dx, drum_top, drum_w, drum_h)

            # Drum Background Card
            painter.setBrush(QBrush(QColor(PALETTE["bg_card"])))
            painter.setPen(QPen(QColor(PALETTE["border"]), 1.5))
            painter.drawRoundedRect(drect, 8.0, 8.0)

            # Top & Bottom Cylindrical Curvature Shadows
            top_shadow = QLinearGradient(0, drect.top(), 0, drect.top() + 24.0)
            top_shadow.setColorAt(0.0, QColor(15, 23, 42, 45))
            top_shadow.setColorAt(1.0, QColor(15, 23, 42, 0))
            painter.fillRect(QRectF(dx, drect.top(), drum_w, 24.0), QBrush(top_shadow))

            bot_shadow = QLinearGradient(0, drect.bottom() - 24.0, 0, drect.bottom())
            bot_shadow.setColorAt(0.0, QColor(15, 23, 42, 0))
            bot_shadow.setColorAt(1.0, QColor(15, 23, 42, 45))
            painter.fillRect(QRectF(dx, drect.bottom() - 24.0, drum_w, 24.0), QBrush(bot_shadow))

            # Digit Rendering
            center_y = drect.center().y()
            if self.drum_locked[i]:
                # Locked Clean Digit
                painter.setPen(QColor(PALETTE["indigo"] if not self.is_spinning else PALETTE["text_primary"]))
                painter.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
                painter.drawText(drect, Qt.AlignmentFlag.AlignCenter, str(self.drum_values[i]))
            else:
                # Rapid Motion Blur Scrolling Digits
                offset = self.drum_offsets[i]
                current_digit = int(offset / 10.0) % 10
                next_digit = (current_digit + 1) % 10
                fraction = (offset % 10.0) / 10.0

                painter.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
                painter.setPen(QColor(PALETTE["text_secondary"]))

                # Draw current rolling digit
                y1 = center_y - (fraction * drum_h * 0.7)
                painter.drawText(QRectF(dx, y1 - 25.0, drum_w, 50.0),
                                 Qt.AlignmentFlag.AlignCenter, str(current_digit))

                # Draw incoming rolling digit
                y2 = y1 + (drum_h * 0.7)
                painter.drawText(QRectF(dx, y2 - 25.0, drum_w, 50.0),
                                 Qt.AlignmentFlag.AlignCenter, str(next_digit))

                # Motion blur speed streaks
                painter.setPen(QPen(QColor(PALETTE["border"]), 1.0))
                painter.drawLine(int(dx + 6.0), int(center_y - 12.0), int(dx + drum_w - 6.0), int(center_y - 12.0))
                painter.drawLine(int(dx + 6.0), int(center_y + 12.0), int(dx + drum_w - 6.0), int(center_y + 12.0))

            # Center Alignment Glass Reticle Indicator
            reticle_pen = QPen(QColor(PALETTE["amber"]), 1.5)
            reticle_pen.setStyle(Qt.PenStyle.DotLine)
            painter.setPen(reticle_pen)
            painter.drawLine(int(dx), int(center_y), int(dx + drum_w), int(center_y))


# ---------------------------------------------------------------------------
# SCREEN 1: Live Ball Roller & Caller Stage
# ---------------------------------------------------------------------------
class LiveCallerStageScreen(QWidget):
    """
    Master interactive calling stage featuring:
      - Left Deck: LottoBallChuteWidget physics drop, dynamic hero track details,
        audio player controller with volume slider, session tracking counter,
        and quick jump button to the 3D particle sphere visualizer.
      - Right Matrix: Master 10x9 Calling Board categorized across Satyam,
        Shivam, and Sundaram pillars with reactive color badges.
    """
    number_called = pyqtSignal(int)
    game_reset = pyqtSignal()
    open_dot_sphere_requested = pyqtSignal()

    def __init__(self, audio_player: AudioPlayer, parent=None):
        super().__init__(parent)
        self.audio_player = audio_player

        # Session calling state (persists until explicit confirmation reset)
        self.called_numbers: List[int] = []
        self.current_number: Optional[int] = None

        # Matrix button lookup {1: QPushButton}
        self.matrix_buttons: Dict[int, QPushButton] = {}

        self._init_ui()
        self._setup_player_timer()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(16)

        # ===================================================================
        # LEFT PANEL: Hero Deck & Audio Engine
        # ===================================================================
        left_panel = QFrame()
        left_panel.setProperty("class", "card-panel")
        left_panel.setFixedWidth(460)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(18, 16, 18, 16)
        left_layout.setSpacing(12)

        # 1. Physics Lotto Ball Chute Widget
        self.chute_widget = LottoBallChuteWidget(self)
        self.chute_widget.ball_settled.connect(self._on_ball_settled)
        left_layout.addWidget(self.chute_widget)

        # 2. Main Call Action Button (Primary CTA)
        self.btn_draw = QPushButton("🎲 ROLL & DROP NEXT NUMBER")
        self.btn_draw.setProperty("class", "btn-primary")
        self.btn_draw.setFixedHeight(48)
        self.btn_draw.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.btn_draw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_draw.clicked.connect(self.draw_next_track)
        left_layout.addWidget(self.btn_draw)

        # 3. Dynamic Hero Track Details Card
        hero_card = QFrame()
        hero_card.setProperty("class", "card-subtle")
        hero_card_layout = QVBoxLayout(hero_card)
        hero_card_layout.setContentsMargins(14, 12, 14, 12)
        hero_card_layout.setSpacing(4)

        self.lbl_hero_pillar = QLabel("READY TO COMMENCE GAME")
        self.lbl_hero_pillar.setStyleSheet(f"color: {PALETTE['indigo']}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        hero_card_layout.addWidget(self.lbl_hero_pillar)

        self.lbl_hero_title = QLabel("Press 'Roll & Drop' or Spacebar")
        self.lbl_hero_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_hero_title.setStyleSheet(f"color: {PALETTE['text_primary']};")
        self.lbl_hero_title.setWordWrap(True)
        hero_card_layout.addWidget(self.lbl_hero_title)

        self.lbl_hero_subtitle = QLabel("90 Evergreen Indian Songs • Full Decade Mapping")
        self.lbl_hero_subtitle.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 12px;")
        self.lbl_hero_subtitle.setWordWrap(True)
        hero_card_layout.addWidget(self.lbl_hero_subtitle)
        left_layout.addWidget(hero_card)

        # 4. Pygame Audio Player Deck
        audio_box = QFrame()
        audio_box.setProperty("class", "card-subtle")
        audio_layout = QVBoxLayout(audio_box)
        audio_layout.setContentsMargins(14, 10, 14, 10)
        audio_layout.setSpacing(8)

        # Audio status row
        audio_top = QHBoxLayout()
        self.lbl_audio_status = QLabel("Audio: Ready")
        self.lbl_audio_status.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 11px; font-weight: 600;")
        audio_top.addWidget(self.lbl_audio_status)
        audio_top.addStretch()

        self.lbl_audio_time = QLabel("0:00 / 0:00")
        self.lbl_audio_time.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 11px;")
        audio_top.addWidget(self.lbl_audio_time)
        audio_layout.addLayout(audio_top)

        # Seek position scrubber
        self.slider_seek = QSlider(Qt.Orientation.Horizontal)
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.setValue(0)
        self.slider_seek.sliderMoved.connect(self._on_seek_moved)
        audio_layout.addWidget(self.slider_seek)

        # Controls & Volume Row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self.btn_play_pause = QPushButton("⏸ Pause")
        self.btn_play_pause.setFixedHeight(32)
        self.btn_play_pause.clicked.connect(self._toggle_play_pause)
        ctrl_row.addWidget(self.btn_play_pause)

        self.btn_replay = QPushButton("↺ Replay")
        self.btn_replay.setFixedHeight(32)
        self.btn_replay.clicked.connect(self._replay_current_song)
        ctrl_row.addWidget(self.btn_replay)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setFixedHeight(32)
        self.btn_stop.clicked.connect(self._stop_audio)
        ctrl_row.addWidget(self.btn_stop)

        ctrl_row.addSpacing(10)
        ctrl_row.addWidget(QLabel("Vol:"))
        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(80)
        self.slider_vol.setFixedWidth(80)
        self.slider_vol.valueChanged.connect(self._on_volume_changed)
        ctrl_row.addWidget(self.slider_vol)

        audio_layout.addLayout(ctrl_row)
        left_layout.addWidget(audio_box)

        # 5. Session Counter & Last 5 Drawn Chips
        session_box = QFrame()
        session_box.setProperty("class", "card-subtle")
        session_layout = QVBoxLayout(session_box)
        session_layout.setContentsMargins(12, 8, 12, 8)
        session_layout.setSpacing(6)

        self.lbl_session_count = QLabel("Drawn: 0 / 90  •  Remaining: 90")
        self.lbl_session_count.setStyleSheet(f"color: {PALETTE['text_primary']}; font-weight: 700; font-size: 12px;")
        session_layout.addWidget(self.lbl_session_count)

        self.chips_row = QHBoxLayout()
        self.chips_row.setSpacing(6)
        self.chip_labels: List[QLabel] = []
        for i in range(5):
            lbl_chip = QLabel("—")
            lbl_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_chip.setStyleSheet(f"background: {PALETTE['bg_card']}; border: 1px solid {PALETTE['border']}; border-radius: 6px; font-weight: 700; color: {PALETTE['text_muted']}; padding: 3px 6px; font-size: 11px;")
            self.chip_labels.append(lbl_chip)
            self.chips_row.addWidget(lbl_chip)
        session_layout.addLayout(self.chips_row)
        left_layout.addWidget(session_box)

        # 6. Quick Action Button -> Screen 2 Visualizer
        btn_view_sphere = QPushButton("🔮 View Live Audio Dot-Sphere →")
        btn_view_sphere.setFixedHeight(36)
        btn_view_sphere.setStyleSheet(f"background: {PALETTE['indigo_light']}; color: {PALETTE['indigo']}; border: 1.5px solid {PALETTE['indigo']}; font-weight: 700;")
        btn_view_sphere.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view_sphere.clicked.connect(self.open_dot_sphere_requested.emit)
        left_layout.addWidget(btn_view_sphere)

        main_layout.addWidget(left_panel)

        # ===================================================================
        # RIGHT PANEL: Master 10x9 Calling Board (3 Pillars)
        # ===================================================================
        right_panel = QFrame()
        right_panel.setProperty("class", "card-panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(18, 16, 18, 16)
        right_layout.setSpacing(10)

        # Header with Pillar Labels
        top_matrix_bar = QHBoxLayout()
        lbl_matrix_title = QLabel("MASTER CALLING BOARD (1–90)")
        lbl_matrix_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_matrix_title.setStyleSheet(f"color: {PALETTE['text_primary']};")
        top_matrix_bar.addWidget(lbl_matrix_title)
        top_matrix_bar.addStretch()

        # Pillar Legend Pills
        pillar_satyam = QLabel("Satyam (1–29)")
        pillar_satyam.setStyleSheet(f"background: {PALETTE['indigo_light']}; color: {PALETTE['indigo']}; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;")
        top_matrix_bar.addWidget(pillar_satyam)

        pillar_shivam = QLabel("Shivam (30–59)")
        pillar_shivam.setStyleSheet(f"background: {PALETTE['amber_light']}; color: {PALETTE['amber_dark']}; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;")
        top_matrix_bar.addWidget(pillar_shivam)

        pillar_sundaram = QLabel("Sundaram (60–90)")
        pillar_sundaram.setStyleSheet(f"background: {PALETTE['emerald_light']}; color: {PALETTE['emerald_dark']}; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;")
        top_matrix_bar.addWidget(pillar_sundaram)

        right_layout.addLayout(top_matrix_bar)

        # 10x9 Interactive Matrix Grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")

        matrix_widget = QWidget()
        matrix_grid = QGridLayout(matrix_widget)
        matrix_grid.setContentsMargins(0, 0, 0, 0)
        matrix_grid.setSpacing(6)

        # Column Header Labels (0-8)
        col_headers = ["1–9", "10–19", "20–29", "30–39", "40–49", "50–59", "60–69", "70–79", "80–90"]
        for c_idx, head_text in enumerate(col_headers):
            lbl_head = QLabel(head_text)
            lbl_head.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_head.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl_head.setStyleSheet(f"color: {PALETTE['text_secondary']}; background: {PALETTE['bg_card_alt']}; border-radius: 4px; padding: 4px 0;")
            matrix_grid.addWidget(lbl_head, 0, c_idx)

        # 90 Cells mapped across columns
        # Col 0 has 9 numbers (1-9), Col 8 has 11 numbers (80-90), others have 10 numbers
        for c_idx, (start_n, end_n) in enumerate(song_bank.COLUMN_RANGES):
            r_idx = 1
            for n in range(start_n, end_n + 1):
                btn = QPushButton(f"{n:02d}")
                btn.setFixedSize(54, 42)
                btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setToolTip(f"Track #{n}: {song_bank.get_song_title(n)}")
                btn.clicked.connect(lambda checked, num=n: self.manual_call_number(num))

                # Default Uncalled Style
                self._apply_cell_style(btn, "uncalled")
                self.matrix_buttons[n] = btn
                matrix_grid.addWidget(btn, r_idx, c_idx)
                r_idx += 1

        scroll_area.setWidget(matrix_widget)
        right_layout.addWidget(scroll_area, 1)

        main_layout.addWidget(right_panel, 1)

    def _setup_player_timer(self):
        """Timer to update seek position and time display smoothly."""
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._sync_player_status)
        self.poll_timer.start(250)

    def draw_next_track(self):
        """Draw next random uncalled number from 1 to 90 with physics roll."""
        if self.chute_widget.is_animating:
            return

        available = [n for n in range(1, 91) if n not in self.called_numbers]
        if not available:
            QMessageBox.information(self, "Game Finished", "All 90 numbers have been called!")
            return

        next_num = random.choice(available)
        self.current_number = next_num

        # Trigger physics drop & roll in chute widget
        self.chute_widget.trigger_drop(next_num)

    def _on_ball_settled(self, number: int):
        """Called once the lotto ball has rolled and settled in the hero cradle."""
        if number not in self.called_numbers:
            self.called_numbers.append(number)

        self._update_hero_details(number)
        self._update_matrix_cell(number, is_active=True)
        self._update_session_chips()

        # Play audio clip
        self._play_song_for_number(number)

        # Notify parent app and child screens
        self.number_called.emit(number)

    def manual_call_number(self, number: int):
        """Allow host to click an uncalled cell to manually call it."""
        if number in self.called_numbers:
            # Already called, replay song
            self._play_song_for_number(number)
            self._update_hero_details(number)
            return

        reply = QMessageBox.question(
            self, "Manual Call Confirmation",
            f"Are you sure you want to call Track #{number:02d} ({song_bank.get_song_title(number)})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.current_number = number
            self.chute_widget.trigger_drop(number)

    def _update_hero_details(self, number: int):
        song = song_bank.get_song(number)
        title = song.get("title", f"Track #{number}") if song else f"Track #{number}"
        artist = song.get("artist", "Evergreen Hit") if song else ""
        year = song.get("year", "") if song else ""

        pillar_name = "Satyam" if number <= 29 else ("Shivam" if number <= 59 else "Sundaram")
        col_idx = song.get("column", 0) + 1 if song else 1

        self.lbl_hero_pillar.setText(f"✦ NOW CALLING: {pillar_name.upper()} • COLUMN {col_idx}")
        self.lbl_hero_title.setText(f"#{number:02d} • {title}")
        sub = f"Album/Artist: {artist}"
        if year:
            sub += f" ({year})"
        self.lbl_hero_subtitle.setText(sub)

    def _play_song_for_number(self, number: int):
        audio_path = song_bank.find_audio_file(number)
        if audio_path and os.path.exists(audio_path):
            self.audio_player.play_track(audio_path)
            self.lbl_audio_status.setText(f"Playing: Track #{number:02d}")
            self.btn_play_pause.setText("⏸ Pause")
        else:
            self.lbl_audio_status.setText(f"Audio for #{number:02d} missing (Silent Mode)")

    def _toggle_play_pause(self):
        if self.audio_player.is_playing:
            if self.audio_player.is_paused:
                self.audio_player.unpause()
                self.btn_play_pause.setText("⏸ Pause")
                self.lbl_audio_status.setText("Playing")
            else:
                self.audio_player.pause()
                self.btn_play_pause.setText("▶ Resume")
                self.lbl_audio_status.setText("Paused")
        elif self.current_number:
            self._play_song_for_number(self.current_number)

    def _replay_current_song(self):
        if self.current_number:
            self._play_song_for_number(self.current_number)

    def _stop_audio(self):
        self.audio_player.stop()
        self.btn_play_pause.setText("▶ Play")
        self.lbl_audio_status.setText("Stopped")

    def _on_seek_moved(self, val: int):
        if self.audio_player.total_duration > 0:
            target_time = (val / 1000.0) * self.audio_player.total_duration
            self.audio_player.seek(target_time)

    def _on_volume_changed(self, val: int):
        self.audio_player.set_volume(val / 100.0)

    def _sync_player_status(self):
        if self.audio_player.is_playing and not self.audio_player.is_paused:
            pos = self.audio_player.get_current_position()
            total = self.audio_player.total_duration
            if total > 0:
                frac = min(1000, int((pos / total) * 1000))
                self.slider_seek.blockSignals(True)
                self.slider_seek.setValue(frac)
                self.slider_seek.blockSignals(False)

                pos_m, pos_s = divmod(int(pos), 60)
                tot_m, tot_s = divmod(int(total), 60)
                self.lbl_audio_time.setText(f"{pos_m}:{pos_s:02d} / {tot_m}:{tot_s:02d}")

    def _update_matrix_cell(self, number: int, is_active: bool = True):
        # Update past active button to called
        for n, btn in self.matrix_buttons.items():
            if n in self.called_numbers:
                if n == number and is_active:
                    self._apply_cell_style(btn, "active")
                else:
                    self._apply_cell_style(btn, "called")
            else:
                self._apply_cell_style(btn, "uncalled")

    def _apply_cell_style(self, btn: QPushButton, state: str):
        if state == "active":
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETTE['amber_light']};
                    color: {PALETTE['amber_dark']};
                    border: 2px solid {PALETTE['amber']};
                    border-radius: 6px;
                    font-weight: 800;
                }}
            """)
        elif state == "called":
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETTE['emerald_light']};
                    color: {PALETTE['emerald_dark']};
                    border: 1.5px solid {PALETTE['emerald']};
                    border-radius: 6px;
                    font-weight: 700;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETTE['bg_card']};
                    color: {PALETTE['text_secondary']};
                    border: 1px solid {PALETTE['border']};
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    border-color: {PALETTE['indigo']};
                    color: {PALETTE['indigo']};
                }}
            """)

    def _update_session_chips(self):
        drawn = len(self.called_numbers)
        remaining = 90 - drawn
        self.lbl_session_count.setText(f"Drawn: {drawn} / 90  •  Remaining: {remaining}")

        # Show last 5 calls in chips
        last_five = self.called_numbers[-5:] if len(self.called_numbers) >= 5 else self.called_numbers
        for i in range(5):
            idx = len(last_five) - 1 - i
            if idx >= 0:
                n = last_five[idx]
                self.chip_labels[i].setText(f"#{n:02d}")
                if i == 0:
                    self.chip_labels[i].setStyleSheet(f"background: {PALETTE['amber_light']}; border: 1px solid {PALETTE['amber']}; border-radius: 6px; font-weight: 800; color: {PALETTE['amber_dark']}; padding: 3px 6px; font-size: 11px;")
                else:
                    self.chip_labels[i].setStyleSheet(f"background: {PALETTE['emerald_light']}; border: 1px solid {PALETTE['emerald']}; border-radius: 6px; font-weight: 700; color: {PALETTE['emerald_dark']}; padding: 3px 6px; font-size: 11px;")
            else:
                self.chip_labels[i].setText("—")
                self.chip_labels[i].setStyleSheet(f"background: {PALETTE['bg_card']}; border: 1px solid {PALETTE['border']}; border-radius: 6px; font-weight: 700; color: {PALETTE['text_muted']}; padding: 3px 6px; font-size: 11px;")

    def confirm_reset_game(self):
        """Prompt user with explicit confirmation dialog before resetting board state."""
        reply = QMessageBox.question(
            self, "Reset Game Session",
            "Are you sure you want to reset the current game?\nAll called numbers and board highlights will be cleared.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.called_numbers.clear()
            self.current_number = None
            self.chute_widget.reset()
            self.audio_player.stop()

            self.lbl_hero_pillar.setText("READY TO COMMENCE GAME")
            self.lbl_hero_title.setText("Press 'Roll & Drop' or Spacebar")
            self.lbl_hero_subtitle.setText("90 Evergreen Indian Songs • Full Decade Mapping")
            self.lbl_audio_status.setText("Audio: Ready")

            for btn in self.matrix_buttons.values():
                self._apply_cell_style(btn, "uncalled")

            self._update_session_chips()
            self.game_reset.emit()


# ---------------------------------------------------------------------------
# SCREEN 2: 3D Particle Audio Sphere Visualizer Screen
# ---------------------------------------------------------------------------
class ParticleSphereScreen(QWidget):
    """
    Dedicated immersive visualizer screen hosting the rotating 3D particle sphere.
    Provides beat modulation toggle, speed controls, now playing track card,
    and a quick return button to the live caller stage.
    """
    return_to_caller_requested = pyqtSignal()

    def __init__(self, audio_player: AudioPlayer, parent=None):
        super().__init__(parent)
        self.audio_player = audio_player
        self.current_song_name = "Ready for Calling"

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        # Header Control Bar
        header = QFrame()
        header.setProperty("class", "card-panel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)

        title = QLabel("🔮 3D PARTICLE AUDIO SPHERE • LIVE RESONATOR")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {PALETTE['indigo']};")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Quick Return Button
        btn_return = QPushButton("← Return to Live Caller Stage")
        btn_return.setFixedHeight(34)
        btn_return.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_return.clicked.connect(self.return_to_caller_requested.emit)
        header_layout.addWidget(btn_return)

        layout.addWidget(header)

        # Main 3D Canvas
        self.sphere_widget = ParticleAudioSphereWidget(self)
        layout.addWidget(self.sphere_widget, 1)

        # Bottom Floating Control Deck
        deck = QFrame()
        deck.setProperty("class", "card-panel")
        deck_layout = QHBoxLayout(deck)
        deck_layout.setContentsMargins(16, 10, 16, 10)
        deck_layout.setSpacing(16)

        # Beat Modulation Toggle
        self.btn_beat_mod = QPushButton("✨ Beat Modulation: ACTIVE")
        self.btn_beat_mod.setCheckable(True)
        self.btn_beat_mod.setChecked(True)
        self.btn_beat_mod.setFixedHeight(34)
        self.btn_beat_mod.setStyleSheet(f"background: {PALETTE['emerald_light']}; color: {PALETTE['emerald_dark']}; border: 1.5px solid {PALETTE['emerald']}; font-weight: 700;")
        self.btn_beat_mod.clicked.connect(self._toggle_beat_modulation)
        deck_layout.addWidget(self.btn_beat_mod)

        # Rotation Speed Slider
        deck_layout.addWidget(QLabel("Rotation Speed:"))
        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(2, 30)
        self.slider_speed.setValue(10)
        self.slider_speed.setFixedWidth(100)
        self.slider_speed.valueChanged.connect(lambda v: self.sphere_widget.set_rotation_speed(v / 10.0))
        deck_layout.addWidget(self.slider_speed)

        # Sphere Scale Slider
        deck_layout.addWidget(QLabel("Sphere Size:"))
        self.slider_scale = QSlider(Qt.Orientation.Horizontal)
        self.slider_scale.setRange(100, 240)
        self.slider_scale.setValue(160)
        self.slider_scale.setFixedWidth(100)
        self.slider_scale.valueChanged.connect(lambda v: self.sphere_widget.set_sphere_scale(float(v)))
        deck_layout.addWidget(self.slider_scale)

        deck_layout.addStretch()

        # Now Playing Track Indicator
        self.lbl_now_playing = QLabel("Now Playing: —")
        self.lbl_now_playing.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-weight: 600; font-size: 12px;")
        deck_layout.addWidget(self.lbl_now_playing)

        layout.addWidget(deck)

    def _toggle_beat_modulation(self):
        active = self.btn_beat_mod.isChecked()
        self.sphere_widget.set_beat_modulation(active)
        if active:
            self.btn_beat_mod.setText("✨ Beat Modulation: ACTIVE")
            self.btn_beat_mod.setStyleSheet(f"background: {PALETTE['emerald_light']}; color: {PALETTE['emerald_dark']}; border: 1.5px solid {PALETTE['emerald']}; font-weight: 700;")
        else:
            self.btn_beat_mod.setText("⏸ Beat Modulation: OFF")
            self.btn_beat_mod.setStyleSheet(f"background: {PALETTE['bg_card_alt']}; color: {PALETTE['text_muted']}; border: 1px solid {PALETTE['border']}; font-weight: 600;")

    def sync_track_info(self, number: int):
        song = song_bank.get_song(number)
        title = song.get("title", f"Track #{number}") if song else f"Track #{number}"
        self.current_song_name = f"#{number:02d} • {title}"
        self.lbl_now_playing.setText(f"Now Playing: {self.current_song_name}")
        self.sphere_widget.set_audio_playing(True)


# ---------------------------------------------------------------------------
# SCREEN 3: Lucky Draw & Slot Machine Roller (Tie-Breaker & Raffle)
# ---------------------------------------------------------------------------
class LuckyDrawScreen(QWidget):
    """
    Dedicated tie-breaker and raffle module featuring animated mechanical
    slot-machine drums, configurable winners, category presets, and a persistent
    session audit log table.
    """
    def __init__(self, audio_player: AudioPlayer, parent=None):
        super().__init__(parent)
        self.audio_player = audio_player
        self.called_numbers_ref: List[int] = []
        self.registered_tickets_ref: List[Dict[str, Any]] = []

        self._init_ui()

    def set_called_numbers(self, called: List[int]):
        self.called_numbers_ref = called
        self._update_pool_labels()

    def set_registered_tickets(self, tickets: List[Dict[str, Any]]):
        self.registered_tickets_ref = tickets
        self._update_pool_labels()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        # Header Title Card
        header = QFrame()
        header.setProperty("class", "card-panel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)

        title = QLabel("🎰 LUCKY DRAW & TIE-BREAKER RAFFLE")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {PALETTE['indigo']};")
        header_layout.addWidget(title)
        header_layout.addStretch()

        desc = QLabel("Provably Fair Random Tie-Breakers & Mechanical Slot Drum Engine")
        desc.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(desc)
        layout.addWidget(header)

        # Main Split Content
        split_layout = QHBoxLayout()
        split_layout.setSpacing(14)

        # Left Config Panel
        cfg_frame = QFrame()
        cfg_frame.setProperty("class", "card-panel")
        cfg_frame.setFixedWidth(380)
        cfg_layout = QVBoxLayout(cfg_frame)
        cfg_layout.setContentsMargins(16, 16, 16, 16)
        cfg_layout.setSpacing(12)

        cfg_title = QLabel("1. Configure Draw Parameters")
        cfg_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        cfg_layout.addWidget(cfg_title)

        # Prize / Category Preset Dropdown
        cfg_layout.addWidget(QLabel("Prize / Claim Category:"))
        self.combo_category = QComboBox()
        self.combo_category.addItems([
            "Early 5 Tie-Breaker",
            "Top Line Tie-Breaker",
            "Middle Line Tie-Breaker",
            "Bottom Line Tie-Breaker",
            "Four Corners Tie-Breaker",
            "Full House Tie-Breaker",
            "Lucky Participant Raffle",
            "Bumper Jackpot Draw",
            "Consolation Gift",
            "Custom Claim..."
        ])
        self.combo_category.currentIndexChanged.connect(self._on_category_changed)
        cfg_layout.addWidget(self.combo_category)

        # Custom Category Text Input
        self.txt_custom_cat = QLineEdit()
        self.txt_custom_cat.setPlaceholderText("Enter custom prize name...")
        self.txt_custom_cat.setVisible(False)
        cfg_layout.addWidget(self.txt_custom_cat)

        # Winner Count Spinbox
        cfg_layout.addWidget(QLabel("Simultaneous Winner(s) to Draw (1–10):"))
        self.spin_winners = QSpinBox()
        self.spin_winners.setRange(1, 10)
        self.spin_winners.setValue(1)
        cfg_layout.addWidget(self.spin_winners)

        # Selection Pool Radio Group
        cfg_layout.addWidget(QLabel("Draw Selection Pool:"))
        self.btn_group_pool = QButtonGroup(self)

        self.radio_called_songs = QRadioButton("Already Called Numbers (Screen 1)")
        self.radio_called_songs.setChecked(True)
        self.btn_group_pool.addButton(self.radio_called_songs, 1)
        cfg_layout.addWidget(self.radio_called_songs)

        self.lbl_called_pool_count = QLabel("Available called numbers: 0")
        self.lbl_called_pool_count.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 11px; margin-left: 20px;")
        cfg_layout.addWidget(self.lbl_called_pool_count)

        self.radio_ticket_ids = QRadioButton("Registered Ticket IDs (Screen 4)")
        self.btn_group_pool.addButton(self.radio_ticket_ids, 2)
        cfg_layout.addWidget(self.radio_ticket_ids)

        self.lbl_ticket_pool_count = QLabel("Available registered tickets: 0")
        self.lbl_ticket_pool_count.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 11px; margin-left: 20px;")
        cfg_layout.addWidget(self.lbl_ticket_pool_count)

        cfg_layout.addStretch()

        # Primary Action Button
        self.btn_start_draw = QPushButton("🎰 ROLL & DRAW WINNERS")
        self.btn_start_draw.setProperty("class", "btn-primary")
        self.btn_start_draw.setFixedHeight(46)
        self.btn_start_draw.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.btn_start_draw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start_draw.clicked.connect(self.start_draw)
        cfg_layout.addWidget(self.btn_start_draw)

        split_layout.addWidget(cfg_frame)

        # Right Slot Drum & Winner Reveal Deck
        right_deck = QFrame()
        right_deck.setProperty("class", "card-panel")
        right_layout = QVBoxLayout(right_deck)
        right_layout.setContentsMargins(18, 16, 18, 16)
        right_layout.setSpacing(12)

        # Mechanical Slot Machine Drums
        self.drum_widget = SlotMachineDrumWidget(self)
        self.drum_widget.draw_finished.connect(self._on_draw_animation_finished)
        right_layout.addWidget(self.drum_widget)

        # Winner Cards Area
        lbl_winner_header = QLabel("🏆 Drawn Winner(s):")
        lbl_winner_header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        right_layout.addWidget(lbl_winner_header)

        self.scroll_winners = QScrollArea()
        self.scroll_winners.setWidgetResizable(True)
        self.scroll_winners.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_winners.setStyleSheet("background: transparent;")

        self.winners_container = QWidget()
        self.winners_layout = QVBoxLayout(self.winners_container)
        self.winners_layout.setContentsMargins(0, 0, 0, 0)
        self.winners_layout.setSpacing(8)
        self.scroll_winners.setWidget(self.winners_container)
        right_layout.addWidget(self.scroll_winners, 1)

        split_layout.addWidget(right_deck, 1)
        layout.addLayout(split_layout, 1)

        # Bottom Frame: Persistent Session Audit Log Table
        log_frame = QFrame()
        log_frame.setProperty("class", "card-panel")
        log_frame.setFixedHeight(200)
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(16, 10, 16, 10)
        log_layout.setSpacing(8)

        log_top = QHBoxLayout()
        lbl_log = QLabel("📋 Session Raffle Audit Log")
        lbl_log.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        log_top.addWidget(lbl_log)
        log_top.addStretch()

        btn_copy = QPushButton("Copy Log")
        btn_copy.setStyleSheet("font-size: 11px;")
        btn_copy.clicked.connect(self._copy_log)
        log_top.addWidget(btn_copy)

        btn_clear = QPushButton("Clear Log")
        btn_clear.setStyleSheet(f"font-size: 11px; color: {PALETTE['coral']};")
        btn_clear.clicked.connect(self._clear_log)
        log_top.addWidget(btn_clear)

        log_layout.addLayout(log_top)

        self.table_log = QTableWidget(0, 5)
        self.table_log.setHorizontalHeaderLabels(["Timestamp", "Prize Category", "Pool Source", "Winner ID/Number", "Details / Song Title"])
        self.table_log.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_log.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        log_layout.addWidget(self.table_log)

        layout.addWidget(log_frame)

    def _on_category_changed(self, idx: int):
        is_custom = self.combo_category.currentText() == "Custom Claim..."
        self.txt_custom_cat.setVisible(is_custom)

    def _update_pool_labels(self):
        self.lbl_called_pool_count.setText(f"Available called numbers: {len(self.called_numbers_ref)}")
        self.lbl_ticket_pool_count.setText(f"Available registered tickets: {len(self.registered_tickets_ref)}")

    def start_draw(self):
        pool_type = self.btn_group_pool.checkedId()
        candidates: List[Dict[str, Any]] = []

        if pool_type == 1:
            if not self.called_numbers_ref:
                QMessageBox.warning(self, "Empty Pool", "No numbers have been called yet in Screen 1!")
                return
            for n in self.called_numbers_ref:
                title = song_bank.get_song_title(n)
                candidates.append({"id": n, "label": f"#{n:02d}", "details": title, "source": "Called Songs"})
        else:
            if not self.registered_tickets_ref:
                QMessageBox.warning(self, "No Tickets Loaded", "No ticket registry loaded. Select a batch in Screen 4 first!")
                return
            for t in self.registered_tickets_ref:
                tid = t.get("ticket_id", "001")
                num_id = int(str(tid).lstrip("#")) if str(tid).isdigit() else 1
                candidates.append({"id": num_id, "label": f"Ticket #{tid}", "details": "Verified Participant", "source": "Ticket Registry"})

        k = min(self.spin_winners.value(), len(candidates))
        drawn_winners = random.sample(candidates, k)
        self.pending_winners = drawn_winners

        # Animate slot machine drum to the 1st winner's number
        first_num = drawn_winners[0]["id"]
        self.drum_widget.spin_to_number(first_num)

    def _on_draw_animation_finished(self, drum_values: list):
        # Clear existing winner cards
        while self.winners_layout.count():
            item = self.winners_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cat = self.txt_custom_cat.text().strip() if self.combo_category.currentText() == "Custom Claim..." else self.combo_category.currentText()
        now_str = datetime.now().strftime("%H:%M:%S")

        for rank, w in enumerate(self.pending_winners, 1):
            card = QFrame()
            card.setProperty("class", "card-subtle")
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(12, 8, 12, 8)

            lbl_rank = QLabel(f"#{rank}")
            lbl_rank.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            lbl_rank.setStyleSheet(f"color: {PALETTE['amber_dark']};")
            c_layout.addWidget(lbl_rank)

            lbl_name = QLabel(f"<b>{w['label']}</b> • {w['details']}")
            lbl_name.setFont(QFont("Segoe UI", 12))
            c_layout.addWidget(lbl_name)

            c_layout.addStretch()

            lbl_source = QLabel(w["source"])
            lbl_source.setStyleSheet(f"background: {PALETTE['indigo_light']}; color: {PALETTE['indigo']}; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 700;")
            c_layout.addWidget(lbl_source)

            self.winners_layout.addWidget(card)

            # Append to persistent audit log
            r_idx = self.table_log.rowCount()
            self.table_log.insertRow(r_idx)
            self.table_log.setItem(r_idx, 0, QTableWidgetItem(now_str))
            self.table_log.setItem(r_idx, 1, QTableWidgetItem(cat))
            self.table_log.setItem(r_idx, 2, QTableWidgetItem(w["source"]))
            self.table_log.setItem(r_idx, 3, QTableWidgetItem(str(w["label"])))
            self.table_log.setItem(r_idx, 4, QTableWidgetItem(str(w["details"])))

    def _copy_log(self):
        rows = []
        for r in range(self.table_log.rowCount()):
            cols = [self.table_log.item(r, c).text() if self.table_log.item(r, c) else "" for c in range(5)]
            rows.append("\t".join(cols))
        text = "\n".join(rows)
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Raffle audit log copied to clipboard!")

    def _clear_log(self):
        reply = QMessageBox.question(self, "Clear Log", "Clear session raffle audit log?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.table_log.setRowCount(0)


# ---------------------------------------------------------------------------
# SCREEN 4: Claim Verifier & Ticket Inspector
# ---------------------------------------------------------------------------
class ClaimVerifierScreen(QWidget):
    """
    Automated cross-check engine with batch registry auto-loader,
    ticket ID search, 3x9 visual grid overlay with CALLED/PENDING status badges,
    and a real-time automated verdict evaluation engine.
    """
    tickets_loaded = pyqtSignal(list)

    def __init__(self, audio_player: AudioPlayer, parent=None):
        super().__init__(parent)
        self.audio_player = audio_player
        self.called_numbers_ref: List[int] = []
        self.current_registry_data: Optional[Dict[str, Any]] = None
        self.current_tickets: List[Dict[str, Any]] = []
        self.active_ticket_idx = 0

        self._init_ui()
        self.reload_batch_registries()

    def set_called_numbers(self, called: List[int]):
        self.called_numbers_ref = called
        self._refresh_ticket_view()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        # Header Control Bar
        header = QFrame()
        header.setProperty("class", "card-panel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(12)

        title = QLabel("🔍 CLAIM VERIFIER & INSPECTOR")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {PALETTE['indigo']};")
        header_layout.addWidget(title)

        header_layout.addWidget(QLabel("Batch Registry:"))
        self.combo_batch = QComboBox()
        self.combo_batch.setMinimumWidth(260)
        self.combo_batch.currentIndexChanged.connect(self._on_batch_selected)
        header_layout.addWidget(self.combo_batch)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.reload_batch_registries)
        header_layout.addWidget(btn_refresh)

        header_layout.addSpacing(16)

        header_layout.addWidget(QLabel("Ticket ID:"))
        self.txt_search_id = QLineEdit()
        self.txt_search_id.setPlaceholderText("e.g. 001")
        self.txt_search_id.setFixedWidth(90)
        self.txt_search_id.returnPressed.connect(self._search_ticket)
        header_layout.addWidget(self.txt_search_id)

        btn_search = QPushButton("Find")
        btn_search.clicked.connect(self._search_ticket)
        header_layout.addWidget(btn_search)

        btn_prev = QPushButton("◀ Prev")
        btn_prev.clicked.connect(self._prev_ticket)
        header_layout.addWidget(btn_prev)

        btn_next = QPushButton("Next ▶")
        btn_next.clicked.connect(self._next_ticket)
        header_layout.addWidget(btn_next)

        header_layout.addStretch()
        layout.addWidget(header)

        # Real-Time Verdict Banner
        self.verdict_frame = QFrame()
        self.verdict_frame.setProperty("class", "card-panel")
        self.verdict_layout = QVBoxLayout(self.verdict_frame)
        self.verdict_layout.setContentsMargins(16, 12, 16, 12)
        self.verdict_layout.setSpacing(6)

        self.lbl_verdict_title = QLabel("WAITING FOR TICKET SELECTION")
        self.lbl_verdict_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.verdict_layout.addWidget(self.lbl_verdict_title)

        self.lbl_verdict_details = QLabel("Select a batch registry above to inspect claims in real time.")
        self.lbl_verdict_details.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 12px;")
        self.verdict_layout.addWidget(self.lbl_verdict_details)

        # Claim qualification badges row
        self.claim_badges_row = QHBoxLayout()
        self.claim_badges_row.setSpacing(8)
        self.claim_labels: Dict[str, QLabel] = {}
        for cname in ["Early 5", "Top Line", "Middle Line", "Bottom Line", "Four Corners", "Full House"]:
            lbl = QLabel(f"{cname}: —")
            lbl.setStyleSheet(f"background: {PALETTE['bg_card_alt']}; color: {PALETTE['text_muted']}; border: 1px solid {PALETTE['border']}; border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 700;")
            self.claim_labels[cname] = lbl
            self.claim_badges_row.addWidget(lbl)
        self.claim_badges_row.addStretch()
        self.verdict_layout.addLayout(self.claim_badges_row)

        layout.addWidget(self.verdict_frame)

        # 3x9 Visual Ticket Grid Overlay
        ticket_box = QFrame()
        ticket_box.setProperty("class", "card-panel")
        t_layout = QVBoxLayout(ticket_box)
        t_layout.setContentsMargins(18, 14, 18, 14)
        t_layout.setSpacing(10)

        self.lbl_ticket_heading = QLabel("TICKET #001 • 3×9 TAMBOLA MATRIX")
        self.lbl_ticket_heading.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        t_layout.addWidget(self.lbl_ticket_heading)

        self.grid_ticket = QGridLayout()
        self.grid_ticket.setSpacing(8)
        t_layout.addLayout(self.grid_ticket, 1)

        layout.addWidget(ticket_box, 1)

    def reload_batch_registries(self):
        self.combo_batch.blockSignals(True)
        self.combo_batch.clear()

        archive_dir = TICKETS_ARCHIVE_DIR
        if archive_dir.exists():
            reg_files = sorted(list(archive_dir.glob("*_registry.json")), key=lambda p: p.stat().st_mtime, reverse=True)
            for rf in reg_files:
                display_name = rf.name.replace("_registry.json", "")
                self.combo_batch.addItem(f"📁 {display_name}", str(rf))

        self.combo_batch.blockSignals(False)
        if self.combo_batch.count() > 0:
            self._on_batch_selected(0)

    def _on_batch_selected(self, idx: int):
        if idx < 0 or idx >= self.combo_batch.count():
            return
        rf_path = self.combo_batch.itemData(idx)
        try:
            with open(rf_path, "r", encoding="utf-8") as f:
                self.current_registry_data = json.load(f)
            self.current_tickets = self.current_registry_data.get("tickets", [])
            self.active_ticket_idx = 0
            self.tickets_loaded.emit(self.current_tickets)
            self._refresh_ticket_view()
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load registry: {e}")

    def _search_ticket(self):
        query = self.txt_search_id.text().strip().lstrip("#")
        if not query:
            return
        for idx, t in enumerate(self.current_tickets):
            tid = str(t.get("ticket_id", "")).lstrip("#")
            if tid == query or tid.endswith(query):
                self.active_ticket_idx = idx
                self._refresh_ticket_view()
                return
        QMessageBox.warning(self, "Not Found", f"Ticket ID '{query}' not found in this batch!")

    def _prev_ticket(self):
        if self.current_tickets and self.active_ticket_idx > 0:
            self.active_ticket_idx -= 1
            self._refresh_ticket_view()

    def _next_ticket(self):
        if self.current_tickets and self.active_ticket_idx < len(self.current_tickets) - 1:
            self.active_ticket_idx += 1
            self._refresh_ticket_view()

    def _refresh_ticket_view(self):
        # Clear grid
        while self.grid_ticket.count():
            item = self.grid_ticket.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.current_tickets or self.active_ticket_idx >= len(self.current_tickets):
            self.lbl_verdict_title.setText("NO TICKET LOADED")
            return

        ticket = self.current_tickets[self.active_ticket_idx]
        tid = ticket.get("ticket_id", "001")
        strips = ticket.get("strips", [])
        if not strips:
            return

        strip = strips[0]
        self.lbl_ticket_heading.setText(f"TICKET #{tid} • 3×9 TAMBOLA MATRIX")
        self.txt_search_id.setText(str(tid))

        # Collect numbers per row and overall
        strip_numbers = []
        row_numbers: List[List[int]] = [[], [], []]

        for r_idx, row in enumerate(strip):
            for c_idx, cell in enumerate(row):
                cell_id = cell["id"] if isinstance(cell, dict) else int(cell)

                cell_frame = QFrame()
                c_layout = QVBoxLayout(cell_frame)
                c_layout.setContentsMargins(6, 6, 6, 6)
                c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                if cell_id > 0:
                    strip_numbers.append(cell_id)
                    row_numbers[r_idx].append(cell_id)

                    is_called = cell_id in self.called_numbers_ref
                    song = song_bank.get_song(cell_id)
                    title = song.get("title", f"Track #{cell_id}") if song else f"Track #{cell_id}"

                    lbl_num = QLabel(f"#{cell_id:02d}")
                    lbl_num.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))

                    lbl_title = QLabel(title)
                    lbl_title.setFont(QFont("Segoe UI", 9))
                    lbl_title.setWordWrap(True)
                    lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

                    lbl_badge = QLabel("CALLED ✓" if is_called else "PENDING ⏳")
                    lbl_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))

                    if is_called:
                        cell_frame.setStyleSheet(f"background: {PALETTE['emerald_light']}; border: 1.5px solid {PALETTE['emerald']}; border-radius: 6px;")
                        lbl_num.setStyleSheet(f"color: {PALETTE['emerald_dark']};")
                        lbl_title.setStyleSheet(f"color: {PALETTE['emerald_dark']};")
                        lbl_badge.setStyleSheet(f"color: {PALETTE['emerald_dark']}; font-weight: 800;")
                    else:
                        cell_frame.setStyleSheet(f"background: {PALETTE['coral_light']}; border: 1px dashed {PALETTE['coral']}; border-radius: 6px;")
                        lbl_num.setStyleSheet(f"color: {PALETTE['coral_dark']};")
                        lbl_title.setStyleSheet(f"color: {PALETTE['coral_dark']};")
                        lbl_badge.setStyleSheet(f"color: {PALETTE['coral_dark']};")

                    c_layout.addWidget(lbl_num)
                    c_layout.addWidget(lbl_title)
                    c_layout.addWidget(lbl_badge)
                else:
                    # Blank slot
                    cell_frame.setStyleSheet(f"background: {PALETTE['cell_blank']}; border: 1px solid {PALETTE['cell_blank_border']}; border-radius: 6px;")
                    lbl_blank = QLabel("—")
                    lbl_blank.setStyleSheet(f"color: {PALETTE['text_muted']}; font-weight: 700;")
                    c_layout.addWidget(lbl_blank)

                self.grid_ticket.addWidget(cell_frame, r_idx, c_idx)

        # Evaluate Claims
        self._evaluate_verdicts(strip_numbers, row_numbers)

    def _evaluate_verdicts(self, all_nums: List[int], row_nums: List[List[int]]):
        called_set = set(self.called_numbers_ref)
        total_called = sum(1 for n in all_nums if n in called_set)

        # 1. Early 5
        early5_ok = total_called >= 5
        self._update_claim_label("Early 5", f"{min(5, total_called)}/5", early5_ok)

        # 2. Top Line
        r1_called = sum(1 for n in row_nums[0] if n in called_set)
        r1_ok = (r1_called == len(row_nums[0]) and len(row_nums[0]) > 0)
        self._update_claim_label("Top Line", f"{r1_called}/{len(row_nums[0])}", r1_ok)

        # 3. Middle Line
        r2_called = sum(1 for n in row_nums[1] if n in called_set)
        r2_ok = (r2_called == len(row_nums[1]) and len(row_nums[1]) > 0)
        self._update_claim_label("Middle Line", f"{r2_called}/{len(row_nums[1])}", r2_ok)

        # 4. Bottom Line
        r3_called = sum(1 for n in row_nums[2] if n in called_set)
        r3_ok = (r3_called == len(row_nums[2]) and len(row_nums[2]) > 0)
        self._update_claim_label("Bottom Line", f"{r3_called}/{len(row_nums[2])}", r3_ok)

        # 5. Four Corners
        corners = []
        if len(row_nums[0]) >= 2 and len(row_nums[2]) >= 2:
            corners = [row_nums[0][0], row_nums[0][-1], row_nums[2][0], row_nums[2][-1]]
        corn_called = sum(1 for n in corners if n in called_set)
        corn_ok = (corn_called == 4)
        self._update_claim_label("Four Corners", f"{corn_called}/4", corn_ok)

        # 6. Full House
        fh_ok = (total_called == len(all_nums) and len(all_nums) > 0)
        self._update_claim_label("Full House", f"{total_called}/{len(all_nums)}", fh_ok)

        # Overall Status Banner
        valid_claims = []
        if fh_ok: valid_claims.append("FULL HOUSE")
        if r1_ok: valid_claims.append("TOP LINE")
        if r2_ok: valid_claims.append("MIDDLE LINE")
        if r3_ok: valid_claims.append("BOTTOM LINE")
        if corn_ok: valid_claims.append("FOUR CORNERS")
        if early5_ok: valid_claims.append("EARLY 5")

        if valid_claims:
            self.lbl_verdict_title.setText(f"🎉 BOGEY VALIDATED: {', '.join(valid_claims)} QUALIFIED!")
            self.lbl_verdict_title.setStyleSheet(f"color: {PALETTE['emerald_dark']}; font-size: 14px; font-weight: 800;")
            self.lbl_verdict_details.setText(f"Ticket #{self.txt_search_id.text()} satisfies the claim criteria. {total_called} of 15 numbers called.")
            self.verdict_frame.setStyleSheet(f"QFrame {{ background: {PALETTE['emerald_light']}; border: 2px solid {PALETTE['emerald']}; border-radius: 12px; }}")
        else:
            rem = len(all_nums) - total_called
            self.lbl_verdict_title.setText(f"⏳ CLAIM PENDING • {rem} Numbers Remaining for Full House")
            self.lbl_verdict_title.setStyleSheet(f"color: {PALETTE['coral_dark']}; font-size: 13px; font-weight: 800;")
            self.lbl_verdict_details.setText(f"{total_called}/15 called. Check individual line progress badges below.")
            self.verdict_frame.setStyleSheet(f"QFrame {{ background: {PALETTE['bg_card']}; border: 1px solid {PALETTE['border']}; border-radius: 12px; }}")

    def _update_claim_label(self, name: str, progress: str, is_ok: bool):
        lbl = self.claim_labels.get(name)
        if lbl:
            if is_ok:
                lbl.setText(f"{name}: {progress} ✓")
                lbl.setStyleSheet(f"background: {PALETTE['emerald_light']}; color: {PALETTE['emerald_dark']}; border: 1.5px solid {PALETTE['emerald']}; border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 800;")
            else:
                lbl.setText(f"{name}: {progress}")
                lbl.setStyleSheet(f"background: {PALETTE['bg_card_alt']}; color: {PALETTE['text_secondary']}; border: 1px solid {PALETTE['border']}; border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 600;")


# ---------------------------------------------------------------------------
# SCREEN 5: Ticket Generator & Template Studio (Non-Destructive Archival)
# ---------------------------------------------------------------------------
class TicketGeneratorScreen(QWidget):
    """
    Print-ahead batch generator enforcing STRICT non-destructive archival,
    collision protection, template selection, mathematical constraint balancing,
    and direct browser/folder opening.
    """
    batch_generated = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_template_path: Optional[str] = None
        self.last_generated_html: Optional[str] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        # Header Title Card
        header = QFrame()
        header.setProperty("class", "card-panel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)

        title = QLabel("🎫 TICKET GENERATOR & TEMPLATE STUDIO")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {PALETTE['indigo']};")
        header_layout.addWidget(title)
        header_layout.addStretch()

        safety_badge = QLabel("🛡️ Strict Non-Destructive Archival Guaranteed")
        safety_badge.setStyleSheet(f"color: {PALETTE['emerald_dark']}; font-size: 11px; font-weight: 700; background: {PALETTE['emerald_light']}; padding: 3px 8px; border-radius: 6px;")
        header_layout.addWidget(safety_badge)
        layout.addWidget(header)

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

        # 1. Custom Batch Name with Live Collision Guard
        form_layout.addWidget(QLabel("Batch / Event Name (e.g. Garba_Night_2026):"))
        self.txt_batch_name = QLineEdit()
        self.txt_batch_name.setText(datetime.now().strftime("Musical_Housie_%Y%m%d"))
        self.txt_batch_name.textChanged.connect(self._check_batch_collision)
        form_layout.addWidget(self.txt_batch_name)

        # Collision Guard Status Badge
        self.lbl_collision_status = QLabel("✓ Available batch name")
        self.lbl_collision_status.setStyleSheet(f"color: {PALETTE['emerald_dark']}; font-size: 11px; font-weight: 700;")
        form_layout.addWidget(self.lbl_collision_status)

        # 2. Template Picker
        form_layout.addWidget(QLabel("Background Template Image:"))
        tpl_row = QHBoxLayout()
        self.combo_templates = QComboBox()
        self._populate_standard_templates()
        self.combo_templates.currentIndexChanged.connect(self._on_template_selected)
        tpl_row.addWidget(self.combo_templates, 1)

        btn_browse_tpl = QPushButton("Browse...")
        btn_browse_tpl.clicked.connect(self._browse_custom_template)
        tpl_row.addWidget(btn_browse_tpl)
        form_layout.addLayout(tpl_row)

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
        self.combo_format.addItems(["2-Strip Landscape (2 tickets per A4 page)", "1-Strip Landscape (1 ticket per page)"])
        self.combo_format.currentIndexChanged.connect(self._on_sheet_count_changed)
        form_layout.addWidget(self.combo_format)

        self.chk_participant_slots = QCheckBox("Include Participant Name & Mobile Slots")
        self.chk_participant_slots.setChecked(True)
        form_layout.addWidget(self.chk_participant_slots)

        form_layout.addStretch()

        # Generate Action Button
        self.btn_generate = QPushButton("🚀 GENERATE & ARCHIVE HOUSIE TICKETS")
        self.btn_generate.setProperty("class", "btn-primary")
        self.btn_generate.setFixedHeight(48)
        self.btn_generate.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate.clicked.connect(self.generate_tickets)
        form_layout.addWidget(self.btn_generate)

        split_layout.addWidget(form_frame)

        # Right Column: Live Template Preview & Output Actions
        preview_frame = QFrame()
        preview_frame.setProperty("class", "card-panel")
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(18, 16, 18, 16)
        preview_layout.setSpacing(12)

        lbl_prev_title = QLabel("Template Preview & Generation Console")
        lbl_prev_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        preview_layout.addWidget(lbl_prev_title)

        # Template Thumbnail Image Box
        self.lbl_img_preview = QLabel("No template preview available")
        self.lbl_img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_img_preview.setFixedHeight(240)
        self.lbl_img_preview.setStyleSheet(f"background: {PALETTE['bg_card_alt']}; border: 1px dashed {PALETTE['border']}; border-radius: 8px;")
        preview_layout.addWidget(self.lbl_img_preview)

        # Generation Summary Box
        self.summary_box = QFrame()
        self.summary_box.setProperty("class", "card-subtle")
        s_layout = QVBoxLayout(self.summary_box)
        s_layout.setContentsMargins(14, 10, 14, 10)
        s_layout.setSpacing(4)

        self.lbl_gen_status = QLabel("Ready to generate new immutable ticket batch.")
        self.lbl_gen_status.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        s_layout.addWidget(self.lbl_gen_status)

        self.lbl_gen_path = QLabel("Output will be stored in tickets_archive/<Batch_Name>.html")
        self.lbl_gen_path.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 11px;")
        self.lbl_gen_path.setWordWrap(True)
        s_layout.addWidget(self.lbl_gen_path)
        preview_layout.addWidget(self.summary_box)

        # Post-Generation Action Buttons
        act_row = QHBoxLayout()
        self.btn_open_browser = QPushButton("🌐 Open in Web Browser")
        self.btn_open_browser.setEnabled(False)
        self.btn_open_browser.setFixedHeight(40)
        self.btn_open_browser.clicked.connect(self._open_in_browser)
        act_row.addWidget(self.btn_open_browser)

        self.btn_open_folder = QPushButton("📁 Open Archive Folder")
        self.btn_open_folder.setFixedHeight(40)
        self.btn_open_folder.clicked.connect(self._open_archive_folder)
        act_row.addWidget(self.btn_open_folder)

        preview_layout.addLayout(act_row)
        split_layout.addWidget(preview_frame, 1)

        layout.addLayout(split_layout, 1)

        # Trigger initial checks
        self._check_batch_collision()
        self._update_template_preview()

    def _populate_standard_templates(self):
        self.combo_templates.clear()
        self.combo_templates.addItem("None (Clean Off-White Minimalist)", "")

        brand_dir = BRANDING_DIR
        if brand_dir.exists():
            for p in sorted(brand_dir.glob("*.png")) + sorted(brand_dir.glob("*.jpg")):
                self.combo_templates.addItem(f"🎨 {p.name}", str(p))

    def _on_template_selected(self, idx: int):
        self.selected_template_path = self.combo_templates.itemData(idx)
        self._update_template_preview()

    def _browse_custom_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Template Image",
            str(BRANDING_DIR if BRANDING_DIR.exists() else BASE_DIR),
            "Images (*.png *.jpg *.jpeg)"
        )
        if path:
            self.combo_templates.addItem(f"📁 {Path(path).name}", path)
            self.combo_templates.setCurrentIndex(self.combo_templates.count() - 1)

    def _update_template_preview(self):
        if self.selected_template_path and os.path.exists(self.selected_template_path):
            pix = QPixmap(self.selected_template_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    self.lbl_img_preview.width() - 20, 220,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.lbl_img_preview.setPixmap(scaled)
                return
        self.lbl_img_preview.setText("Minimalist Clean Layout (No Background Image)")

    def _on_sheet_count_changed(self):
        sheets = self.spin_sheets.value()
        is_2strip = "2-Strip" in self.combo_format.currentText()
        factor = 2 if is_2strip else 1
        total_tickets = sheets * factor
        self.lbl_ticket_equiv.setText(f"(= {total_tickets} Tickets in {'2-Strip' if is_2strip else '1-Strip'})")

    def _check_batch_collision(self):
        raw_name = self.txt_batch_name.text().strip()
        clean = sanitize_batch_name(raw_name)
        archive_dir = TICKETS_ARCHIVE_DIR

        html_exists = (archive_dir / f"{clean}.html").exists()
        reg_exists = (archive_dir / f"{clean}_registry.json").exists()

        if html_exists or reg_exists:
            self.lbl_collision_status.setText(f"⚠️ Batch exists! Will auto-increment to {clean}_02 to protect previous tickets.")
            self.lbl_collision_status.setStyleSheet(f"color: {PALETTE['amber_dark']}; font-size: 11px; font-weight: 700;")
        else:
            self.lbl_collision_status.setText(f"✓ Available batch name ({clean}.html)")
            self.lbl_collision_status.setStyleSheet(f"color: {PALETTE['emerald_dark']}; font-size: 11px; font-weight: 700;")

    def generate_tickets(self):
        raw_name = self.txt_batch_name.text().strip()
        if not raw_name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a batch or event name.")
            return

        clean = sanitize_batch_name(raw_name)
        unique_name = resolve_unique_batch_name(clean, TICKETS_ARCHIVE_DIR)

        if unique_name != clean:
            reply = QMessageBox.question(
                self, "Non-Destructive Archival Notice",
                f"Batch '{clean}' already exists in tickets_archive/.\n\n"
                f"To protect all previously printed tickets, this new run will be saved as:\n"
                f"👉 {unique_name}\n\nProceed with generation?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        sheets = self.spin_sheets.value()
        format_mode = "2-strip" if "2-Strip" in self.combo_format.currentText() else "1-strip"
        show_slots = self.chk_participant_slots.isChecked()

        try:
            self.btn_generate.setEnabled(False)
            self.lbl_gen_status.setText("Generating mathematical ticket matrix...")
            QApplication.processEvents()

            out_html = generate_housie_tickets(
                num_sheets=sheets,
                format_mode=format_mode,
                template_path=self.selected_template_path,
                show_participant_slots=show_slots,
                batch_name=unique_name
            )

            self.last_generated_html = out_html
            self.btn_open_browser.setEnabled(True)
            self.lbl_gen_status.setText(f"✓ Successfully generated {sheets} sheets ({unique_name})!")
            self.lbl_gen_path.setText(f"Archived to: {out_html}")

            self.batch_generated.emit(out_html)

            QMessageBox.information(
                self, "Generation Complete",
                f"Tickets generated successfully!\n\n"
                f"Archived: {unique_name}.html\n"
                f"Registry: {unique_name}_registry.json\n\n"
                f"Click 'Open in Web Browser' to inspect or print."
            )
        except Exception as e:
            QMessageBox.critical(self, "Generation Error", f"Failed to generate tickets: {e}")
            self.lbl_gen_status.setText("Error occurred during generation.")
        finally:
            self.btn_generate.setEnabled(True)
            self._check_batch_collision()

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
# MAIN APPLICATION HUB CONTAINER
# ---------------------------------------------------------------------------
class MusicalHousieApp(QMainWindow):
    """
    Primary desktop window for Musical Housie (Tambola).
    Ties together all 5 screens in an elegant off-white light theme with rich
    animations, zero cloud dependencies, and strict data safety.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Musical Housie (Tambola) — Offline Master Studio & Caller")
        self.resize(1380, 880)
        self.setMinimumSize(1120, 760)

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

        # Top System Navigation Bar
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

        # Header Quick Reset
        btn_quick_reset = QPushButton("Reset Game")
        btn_quick_reset.setStyleSheet(f"font-size: 11px; color: {PALETTE['coral']}; border: 1px solid {PALETTE['coral']};")
        btn_quick_reset.clicked.connect(self._on_header_reset)
        nav_header.addWidget(btn_quick_reset)

        root_layout.addLayout(nav_header)

        # 5 Tab Screens Container
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.screen_caller = LiveCallerStageScreen(self.audio_player, self)
        self.screen_sphere = ParticleSphereScreen(self.audio_player, self)
        self.screen_raffle = LuckyDrawScreen(self.audio_player, self)
        self.screen_verifier = ClaimVerifierScreen(self.audio_player, self)
        self.screen_generator = TicketGeneratorScreen(self)

        self.tabs.addTab(self.screen_caller, "🎙️ Live Caller Stage")
        self.tabs.addTab(self.screen_sphere, "🔮 3D Audio Dot-Sphere")
        self.tabs.addTab(self.screen_raffle, "🎰 Lucky Draw & Raffle")
        self.tabs.addTab(self.screen_verifier, "🔍 Claim Verifier & Inspector")
        self.tabs.addTab(self.screen_generator, "🎫 Ticket Generator Studio")

        root_layout.addWidget(self.tabs, 1)

        # Bottom Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            f"background: {PALETTE['bg_card']}; color: {PALETTE['text_muted']}; "
            f"font-size: 11px; border-top: 1px solid {PALETTE['border']};"
        )
        self.status_bar.showMessage("Musical Housie Offline Studio • Strict Non-Destructive Archival Engine Ready")
        self.setStatusBar(self.status_bar)

    def _connect_signals(self):
        # Cross-screen synchronization
        self.screen_caller.number_called.connect(self._sync_state_on_number_called)
        self.screen_caller.game_reset.connect(self._sync_state_on_reset)
        self.screen_caller.open_dot_sphere_requested.connect(lambda: self.tabs.setCurrentIndex(1))

        self.screen_sphere.return_to_caller_requested.connect(lambda: self.tabs.setCurrentIndex(0))

        self.screen_generator.batch_generated.connect(self._on_batch_generated)
        self.screen_verifier.tickets_loaded.connect(self.screen_raffle.set_registered_tickets)

    def _sync_state_on_number_called(self, num: int):
        called = self.screen_caller.called_numbers
        count = len(called)
        self.lbl_global_summary.setText(f"Active Session: {count} / 90 Numbers Called (Last: #{num:02d})")

        # Sync with Screen 2, 3, 4
        self.screen_sphere.sync_track_info(num)
        self.screen_raffle.set_called_numbers(called)
        self.screen_verifier.set_called_numbers(called)

    def _sync_state_on_reset(self):
        self.lbl_global_summary.setText("Active Session: 0 / 90 Numbers Called")
        self.screen_raffle.set_called_numbers([])
        self.screen_verifier.set_called_numbers([])

    def _on_header_reset(self):
        self.screen_caller.confirm_reset_game()

    def _on_batch_generated(self, html_path: str):
        self.screen_verifier.reload_batch_registries()
        self.status_bar.showMessage(f"Archived new batch: {Path(html_path).name}", 6000)

    def keyPressEvent(self, event):
        # Spacebar shortcut to draw next track on Screen 1
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
