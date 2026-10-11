"""
Musical Tambola - Main Desktop Application Entry Point & Navigation Hub
Integrates Song & Asset Management, Ticket Engine, Live Gameplay Master Caller,
Lucky Draw Raffle, and Automated Claim Verification.
"""
import sys
import logging
from pathlib import Path

from qt_compat import (
    Qt,
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QStatusBar, QFrame,
    QIcon, QFont
)

from config import THEME
import database
from modules.audio_player import AudioPlayer
from modules.game_host import GameHostWidget
from modules.claim_verifier import ClaimVerifierWidget
from modules.ticket_generator_widget import TicketGeneratorWidget
from modules.lucky_draw import LuckyDrawWidget
from modules.asset_manager_widget import AssetManagerWidget

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("tambola.main")


class MusicalTambolaApp(QMainWindow):
    """Primary Window and Hub for Musical Tambola Desktop Application."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Musical Tambola — Offline Host Studio")
        self.resize(1300, 850)
        self.setMinimumSize(1080, 720)

        # Initialize shared audio controller
        self.audio_player = AudioPlayer()

        self._apply_global_stylesheet()
        self._init_ui()
        self._wire_inter_module_events()

    def _apply_global_stylesheet(self):
        """Rich Dark Slate, Crimson & Gold Luxury Theme."""
        qss = f"""
            QMainWindow, QWidget {{
                background-color: {THEME['bg_dark']};
                color: {THEME['text_primary']};
                font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', Arial, sans-serif;
            }}

            QTabWidget::pane {{
                border: 1px solid {THEME['border']};
                background: {THEME['bg_dark']};
                border-top: none;
            }}

            QTabBar::tab {{
                background: {THEME['bg_card']};
                color: {THEME['text_secondary']};
                padding: 12px 24px;
                font-size: 13px;
                font-weight: bold;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                border: 1px solid {THEME['border']};
                border-bottom: none;
            }}

            QTabBar::tab:selected {{
                background: {THEME['crimson']};
                color: white;
                border-color: {THEME['crimson']};
            }}

            QTabBar::tab:hover:!selected {{
                background: {THEME['bg_card_hover']};
                color: {THEME['text_primary']};
            }}

            QScrollBar:vertical {{
                border: none;
                background: {THEME['bg_subtle']};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {THEME['border']};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {THEME['gold']};
            }}

            QScrollBar:horizontal {{
                border: none;
                background: {THEME['bg_subtle']};
                height: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background: {THEME['border']};
                min-width: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {THEME['gold']};
            }}

            QMessageBox {{
                background-color: {THEME['bg_card']};
                color: {THEME['text_primary']};
            }}
            QMessageBox QLabel {{
                color: {THEME['text_primary']};
            }}
            QMessageBox QPushButton {{
                background-color: {THEME['crimson']};
                color: white;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
            }}
        """
        self.setStyleSheet(qss)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top App Title Bar
        title_bar = QFrame()
        title_bar.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E1B4B, stop:0.5 #881337, stop:1 #0F172A);
                border-bottom: 2px solid {THEME['gold']};
                padding: 8px 16px;
            }}
        """)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(12, 6, 12, 6)

        lbl_logo = QLabel("🎶 MUSICAL TAMBOLA")
        lbl_logo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        lbl_logo.setStyleSheet(f"color: {THEME['gold']}; letter-spacing: 1.5px;")

        lbl_sub = QLabel("Professional Offline Host Studio & Verification System")
        lbl_sub.setFont(QFont("Arial", 10))
        lbl_sub.setStyleSheet("color: #E2E8F0; margin-left: 10px;")

        tb_layout.addWidget(lbl_logo)
        tb_layout.addWidget(lbl_sub)
        tb_layout.addStretch()

        lbl_badge = QLabel("OFFLINE-FIRST • 100% SECURE")
        lbl_badge.setStyleSheet(f"""
            background-color: {THEME['bg_dark']};
            color: {THEME['emerald']};
            border: 1px solid {THEME['emerald']};
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: bold;
        """)
        tb_layout.addWidget(lbl_badge)

        main_layout.addWidget(title_bar)

        # Tab Navigation
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # Tab 1: Ticket Generator & Template Studio (PRD Module 2.2)
        self.tab_ticket_engine = TicketGeneratorWidget()
        self.tabs.addTab(self.tab_ticket_engine, "🎫 Ticket Generator & Template Studio")

        # Tab 2: Game Host & Caller Dashboard (PRD Module 2.3 & 2.4)
        self.tab_game_host = GameHostWidget(audio_player=self.audio_player)
        self.tabs.addTab(self.tab_game_host, "🎲 Game Host & Caller Dashboard")

        # Tab 3: Claim Verifier (PRD Module 2.5)
        self.tab_claim_verifier = ClaimVerifierWidget()
        self.tabs.addTab(self.tab_claim_verifier, "🔍 Claim Verifier")

        # Tab 4: Lucky Draw
        self.tab_lucky_draw = LuckyDrawWidget()
        self.tabs.addTab(self.tab_lucky_draw, "🎁 Lucky Draw Raffle")

        # Tab 5: Asset & Song Manager
        self.tab_asset_manager = AssetManagerWidget(audio_player=self.audio_player)
        self.tabs.addTab(self.tab_asset_manager, "🎵 Song & Audio Catalog")

        main_layout.addWidget(self.tabs, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {THEME['bg_card']};
                color: {THEME['text_secondary']};
                border-top: 1px solid {THEME['border']};
                padding: 4px;
            }}
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready • SQLite Database Active • Audio Engine Online")

    def _wire_inter_module_events(self):
        """Synchronize tabs when changes happen in other modules."""
        # When a call is made in Game Host, refresh Claim Verifier if open
        self.tab_game_host.call_made_signal.connect(self._on_call_made)
        
        # When tab changes, refresh state
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_call_made(self, song_id: int):
        self.status_bar.showMessage(f"Song #{song_id} called. Claim Verification & Lucky Draw pools updated.")
        # If user is currently looking at claim verification, update it
        if self.tabs.currentWidget() == self.tab_claim_verifier:
            self.tab_claim_verifier.verify_ticket()

    def _on_tab_changed(self, index: int):
        current_widget = self.tabs.widget(index)
        if current_widget == self.tab_claim_verifier:
            self.tab_claim_verifier.refresh_ticket_list()
            if self.tab_claim_verifier.active_ticket:
                self.tab_claim_verifier.verify_ticket()
        elif current_widget == self.tab_ticket_engine:
            self.tab_ticket_engine.refresh_tickets_table()
        elif current_widget == self.tab_lucky_draw:
            self.tab_lucky_draw.refresh_audit_table()
        elif current_widget == self.tab_asset_manager:
            self.tab_asset_manager.refresh_catalog_table()

    def closeEvent(self, event):
        """Clean shutdown of audio."""
        try:
            self.audio_player.stop()
        except Exception:
            pass
        event.accept()


def main():
    # 1. Initialize SQLite Database
    database.init_db()
    database.seed_default_songs()

    # 2. Start Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Musical Tambola")
    app.setOrganizationName("TambolaStudio")

    window = MusicalTambolaApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
