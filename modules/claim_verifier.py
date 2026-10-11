"""
Module 2.5: Claim Verification System
Instant Ticket Layout Lookup, Visual 3x9 Cross-Checking Grid,
and Auto-Verdict Engine for Early 5, Lines 1-3, Four Corners, and Full House.
"""
import logging
from typing import Dict, List, Tuple, Optional, Any, Set

from qt_compat import (
    Qt, pyqtSignal,
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QFrame, QMessageBox,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QFont, QColor
)

from config import THEME
import database

logger = logging.getLogger("tambola.claim_verifier")


class ClaimVerifierWidget(QWidget):
    """Claim verification interface with interactive visual grid and automated validation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_ticket: Optional[Dict[str, Any]] = None
        self.called_numbers: Set[int] = set()
        self.song_catalog: Dict[int, Dict[str, Any]] = {}
        self.archived_tickets: Dict[str, Dict[str, Any]] = {}
        self.archived_batch_name: Optional[str] = None
        
        self._init_ui()
        self.refresh_batch_archives()
        self.refresh_ticket_list()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Left Column: Lookup, Visual Ticket Grid
        left_panel = QVBoxLayout()
        left_panel.setSpacing(12)

        # 0. Batch Archive Selector Card (Game Day Load)
        batch_card = QFrame()
        batch_card.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 10px 14px;
            }}
        """)
        batch_layout = QHBoxLayout(batch_card)
        batch_layout.setSpacing(10)

        lbl_batch = QLabel("📁 Game Day Batch Archive:")
        lbl_batch.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl_batch.setStyleSheet(f"color: {THEME['gold']};")

        self.combo_batch_archive = QComboBox()
        self.combo_batch_archive.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: bold;
            }}
        """)
        self.combo_batch_archive.currentIndexChanged.connect(self._on_batch_archive_changed)

        btn_refresh_batches = QPushButton("🔄 Refresh")
        btn_refresh_batches.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh_batches.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {THEME['bg_card_hover']};
            }}
        """)
        btn_refresh_batches.clicked.connect(self.refresh_batch_archives)

        self.lbl_batch_status = QLabel("Source: Active SQLite Database")
        self.lbl_batch_status.setStyleSheet(f"color: {THEME['emerald']}; font-size: 11px; font-weight: bold;")

        batch_layout.addWidget(lbl_batch)
        batch_layout.addWidget(self.combo_batch_archive, stretch=1)
        batch_layout.addWidget(btn_refresh_batches)
        batch_layout.addWidget(self.lbl_batch_status)
        left_panel.addWidget(batch_card)

        # 1. Lookup Header Card
        lookup_card = QFrame()
        lookup_card.setObjectName("LookupCard")
        lookup_card.setStyleSheet(f"""
            #LookupCard {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 12px;
            }}
        """)
        lookup_layout = QHBoxLayout(lookup_card)
        lookup_layout.setSpacing(10)

        lbl_lookup = QLabel("🎫 Enter Ticket ID:")
        lbl_lookup.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lbl_lookup.setStyleSheet(f"color: {THEME['gold']};")

        self.txt_ticket_id = QLineEdit()
        self.txt_ticket_id.setPlaceholderText("e.g. 001, 15, or select from list")
        self.txt_ticket_id.setStyleSheet(f"""
            QLineEdit {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 13px;
                font-weight: bold;
            }}
        """)
        self.txt_ticket_id.returnPressed.connect(self.verify_ticket)

        self.combo_registered = QComboBox()
        self.combo_registered.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        self.combo_registered.currentIndexChanged.connect(self._on_combo_selected)

        btn_verify = QPushButton("🔍 VERIFY TICKET")
        btn_verify.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_verify.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        btn_verify.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['crimson']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
            }}
            QPushButton:hover {{
                background-color: {THEME['crimson_hover']};
            }}
        """)
        btn_verify.clicked.connect(self.verify_ticket)

        lookup_layout.addWidget(lbl_lookup)
        lookup_layout.addWidget(self.txt_ticket_id, stretch=1)
        lookup_layout.addWidget(self.combo_registered)
        lookup_layout.addWidget(btn_verify)
        left_panel.addWidget(lookup_card)

        # 2. Visual Ticket Display Container (Scrollable)
        self.scroll_ticket = QScrollArea()
        self.scroll_ticket.setWidgetResizable(True)
        self.scroll_ticket.setStyleSheet("background: transparent; border: none;")

        self.ticket_display_container = QWidget()
        self.ticket_vbox = QVBoxLayout(self.ticket_display_container)
        self.ticket_vbox.setSpacing(14)
        self.ticket_vbox.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_empty_state = QLabel("Enter a Ticket ID above to load and cross-check its layout.")
        self.lbl_empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_state.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 14px; padding: 40px;")
        self.ticket_vbox.addWidget(self.lbl_empty_state)

        self.scroll_ticket.setWidget(self.ticket_display_container)
        left_panel.addWidget(self.scroll_ticket, stretch=1)

        main_layout.addLayout(left_panel, stretch=7)

        # Right Column: Auto-Verdict Engine & Prize Award Panel
        verdict_panel = QVBoxLayout()
        verdict_panel.setSpacing(12)

        verdict_card = QFrame()
        verdict_card.setObjectName("VerdictCard")
        verdict_card.setStyleSheet(f"""
            #VerdictCard {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        self.verdict_layout = QVBoxLayout(verdict_card)
        self.verdict_layout.setSpacing(10)

        lbl_verdict_title = QLabel("⚖️ AUTOMATED VERDICT")
        lbl_verdict_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        lbl_verdict_title.setStyleSheet(f"color: {THEME['gold']};")
        self.verdict_layout.addWidget(lbl_verdict_title)

        # Big Status Badge
        self.lbl_main_status = QLabel("NO TICKET LOADED")
        self.lbl_main_status.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.lbl_main_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_main_status.setStyleSheet(f"""
            background-color: {THEME['bg_subtle']};
            color: {THEME['text_muted']};
            border-radius: 8px;
            padding: 12px;
        """)
        self.verdict_layout.addWidget(self.lbl_main_status)

        # Pattern Checklist Container
        self.patterns_container = QWidget()
        self.patterns_vbox = QVBoxLayout(self.patterns_container)
        self.patterns_vbox.setSpacing(6)
        self.patterns_vbox.setContentsMargins(0, 0, 0, 0)
        self.verdict_layout.addWidget(self.patterns_container)

        self.verdict_layout.addStretch()

        # Award Claim Action
        award_box = QVBoxLayout()
        self.txt_winner_name = QLineEdit()
        self.txt_winner_name.setPlaceholderText("Enter Winner / Player Name")
        self.txt_winner_name.setStyleSheet(f"""
            QLineEdit {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        
        self.btn_award = QPushButton("🏆 Confirm & Record Winning Claim")
        self.btn_award.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_award.setEnabled(False)
        self.btn_award.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.btn_award.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['emerald']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {THEME['emerald_hover']};
            }}
            QPushButton:disabled {{
                background-color: {THEME['bg_card_hover']};
                color: {THEME['text_muted']};
            }}
        """)
        self.btn_award.clicked.connect(self.record_claim)

        award_box.addWidget(self.txt_winner_name)
        award_box.addWidget(self.btn_award)
        self.verdict_layout.addLayout(award_box)

        verdict_panel.addWidget(verdict_card)
        main_layout.addLayout(verdict_panel, stretch=4)

    def refresh_batch_archives(self):
        """Scan tickets_archive/ for *_registry.json files."""
        import os
        from config import TICKETS_ARCHIVE_DIR
        TICKETS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        json_files = sorted(TICKETS_ARCHIVE_DIR.glob("*_registry.json"), key=os.path.getmtime, reverse=True)
        
        self.combo_batch_archive.blockSignals(True)
        self.combo_batch_archive.clear()
        self.combo_batch_archive.addItem("-- Active SQLite Database (Default) --", None)
        for jf in json_files:
            self.combo_batch_archive.addItem(jf.name, str(jf))
        self.combo_batch_archive.blockSignals(False)

    def _on_batch_archive_changed(self, index: int):
        """Load selected batch JSON registry into verifier memory."""
        import json
        file_path = self.combo_batch_archive.currentData()
        if not file_path:
            self.archived_tickets = {}
            self.archived_batch_name = None
            self.lbl_batch_status.setText("Source: Active SQLite Database")
            self.lbl_batch_status.setStyleSheet(f"color: {THEME['emerald']}; font-size: 11px; font-weight: bold;")
            self.refresh_ticket_list()
            return

        try:
            with open(file_path, "r", encoding="utf-8") as rf:
                reg_data = json.load(rf)

            raw_tickets = reg_data.get("tickets", [])
            self.archived_tickets = {str(t["ticket_id"]): t for t in raw_tickets}
            self.archived_batch_name = reg_data.get("batch_name", Path(file_path).stem.replace("_registry", ""))
            count = len(self.archived_tickets)

            self.lbl_batch_status.setText(f"Batch: {self.archived_batch_name} ({count} tickets)")
            self.lbl_batch_status.setStyleSheet(f"color: {THEME['gold']}; font-size: 11px; font-weight: bold;")
            self.refresh_ticket_list()
        except Exception as e:
            QMessageBox.critical(self, "Registry Error", f"Failed to load archive registry:\n{e}")

    def refresh_ticket_list(self):
        """Populate the dropdown with tickets from active database or loaded archive."""
        self.combo_registered.blockSignals(True)
        self.combo_registered.clear()
        self.combo_registered.addItem("-- Select from Registry --", None)

        if self.archived_tickets:
            for tid in sorted(self.archived_tickets.keys()):
                t = self.archived_tickets[tid]
                mode = t.get("mode", "2-strip")
                self.combo_registered.addItem(f"Ticket #{tid} ({mode})", tid)
        else:
            tickets = database.get_all_tickets()
            for t in tickets:
                tid = t["ticket_id"]
                mode = t.get("mode", "1-strip")
                self.combo_registered.addItem(f"Ticket #{tid} ({mode})", tid)
        self.combo_registered.blockSignals(False)

    def _on_combo_selected(self, index: int):
        data = self.combo_registered.currentData()
        if data:
            self.txt_ticket_id.setText(str(data))
            self.verify_ticket()

    def verify_ticket(self):
        """Fetch ticket from archive or active DB, cross-check against called numbers, and evaluate."""
        tid = self.txt_ticket_id.text().strip()
        if not tid:
            return

        ticket = None
        # 1. Check loaded archive first
        if self.archived_tickets:
            ticket = self.archived_tickets.get(tid)
            if not ticket and tid.isdigit():
                ticket = self.archived_tickets.get(f"{int(tid):03d}")

        # 2. Fallback to active SQLite database
        if not ticket:
            ticket = database.get_ticket(tid)

        if not ticket:
            src = f"batch '{self.archived_batch_name}'" if self.archived_batch_name else "active database"
            QMessageBox.warning(self, "Ticket Not Found", f"No registered ticket found with ID '{tid}' in {src}.")
            return

        self.active_ticket = ticket
        session_id = database.get_or_create_active_session()
        self.called_numbers = set(database.get_called_numbers(session_id))
        self.song_catalog = {s["id"]: s for s in database.get_all_songs()}

        self._render_visual_ticket()
        self._evaluate_patterns()

    def _render_visual_ticket(self):
        """Build the visual 3x9 grid cells with green (called) or dark red (uncalled) styling."""
        # Clear previous widgets
        while self.ticket_vbox.count() > 0:
            child = self.ticket_vbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        header_strip = QFrame()
        header_strip.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 8px;
                padding: 6px 12px;
            }}
        """)
        h_layout = QHBoxLayout(header_strip)
        h_layout.addWidget(QLabel(f"<b>Ticket #{self.active_ticket['ticket_id']}</b> ({self.active_ticket.get('mode', '1-strip')})"))
        self.ticket_vbox.addWidget(header_strip)

        for s_idx, strip in enumerate(self.active_ticket["strips"], start=1):
            strip_card = QFrame()
            strip_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {THEME['bg_card']};
                    border: 2px solid {THEME['border']};
                    border-radius: 10px;
                    padding: 8px;
                }}
            """)
            strip_layout = QVBoxLayout(strip_card)
            
            lbl_strip = QLabel(f"STRIP {s_idx}")
            lbl_strip.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            lbl_strip.setStyleSheet(f"color: {THEME['gold']};")
            strip_layout.addWidget(lbl_strip)

            grid_layout = QGridLayout()
            grid_layout.setSpacing(4)

            for r_idx, row in enumerate(strip):
                for c_idx, sid in enumerate(row):
                    cell_widget = QFrame()
                    cell_widget.setFixedSize(62, 54)
                    c_box = QVBoxLayout(cell_widget)
                    c_box.setContentsMargins(2, 2, 2, 2)
                    c_box.setSpacing(1)

                    if sid > 0:
                        is_called = sid in self.called_numbers
                        bg_color = THEME['emerald'] if is_called else THEME['bg_subtle']
                        border_color = THEME['emerald_hover'] if is_called else THEME['border']
                        text_color = "#FFFFFF" if is_called else THEME['text_secondary']
                        status_icon = "✓ " if is_called else ""

                        cell_widget.setStyleSheet(f"""
                            QFrame {{
                                background-color: {bg_color};
                                border: 1.5px solid {border_color};
                                border-radius: 6px;
                            }}
                        """)

                        lbl_sid = QLabel(f"{status_icon}{sid}")
                        lbl_sid.setFont(QFont("Arial", 11, QFont.Weight.Bold))
                        lbl_sid.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        lbl_sid.setStyleSheet(f"color: {text_color};")

                        song = self.song_catalog.get(sid, {})
                        title = song.get("title", f"Song {sid}")
                        lbl_stitle = QLabel(title)
                        lbl_stitle.setFont(QFont("Arial", 7))
                        lbl_stitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        lbl_stitle.setStyleSheet(f"color: {text_color};")
                        lbl_stitle.setWordWrap(True)

                        c_box.addWidget(lbl_sid)
                        c_box.addWidget(lbl_stitle)
                    else:
                        # Blank cell
                        cell_widget.setStyleSheet(f"""
                            QFrame {{
                                background-color: {THEME['bg_dark']};
                                border: 1px dashed {THEME['border']};
                                border-radius: 6px;
                            }}
                        """)

                    grid_layout.addWidget(cell_widget, r_idx, c_idx)

            strip_layout.addLayout(grid_layout)
            self.ticket_vbox.addWidget(strip_card)

    def _evaluate_patterns(self):
        """Run auto-verdict on all patterns and display breakdown."""
        # Clear pattern list
        while self.patterns_vbox.count() > 0:
            child = self.patterns_vbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.active_ticket:
            return

        strips = self.active_ticket["strips"]
        
        # Check overall ticket songs
        all_ticket_songs = [sid for strip in strips for row in strip for sid in row if sid > 0]
        called_ticket_songs = [sid for sid in all_ticket_songs if sid in self.called_numbers]
        
        # Early 5 (Jaldi 5)
        early5_complete = len(called_ticket_songs) >= 5
        self._add_pattern_badge(
            "Early 5 (Jaldi 5)",
            early5_complete,
            f"{min(5, len(called_ticket_songs))}/5 numbers called"
        )

        has_any_full_house = False

        for s_idx, strip in enumerate(strips, start=1):
            strip_prefix = f"Strip {s_idx} - " if len(strips) > 1 else ""
            
            # Row 0: Top Line
            row0 = [sid for sid in strip[0] if sid > 0]
            r0_called = [sid for sid in row0 if sid in self.called_numbers]
            r0_complete = len(r0_called) == len(row0)
            self._add_pattern_badge(
                f"{strip_prefix}Top Line",
                r0_complete,
                f"{len(r0_called)}/5 called" + ("" if r0_complete else f" (Missing: {set(row0) - set(r0_called)})")
            )

            # Row 1: Middle Line
            row1 = [sid for sid in strip[1] if sid > 0]
            r1_called = [sid for sid in row1 if sid in self.called_numbers]
            r1_complete = len(r1_called) == len(row1)
            self._add_pattern_badge(
                f"{strip_prefix}Middle Line",
                r1_complete,
                f"{len(r1_called)}/5 called" + ("" if r1_complete else f" (Missing: {set(row1) - set(r1_called)})")
            )

            # Row 2: Bottom Line
            row2 = [sid for sid in strip[2] if sid > 0]
            r2_called = [sid for sid in row2 if sid in self.called_numbers]
            r2_complete = len(r2_called) == len(row2)
            self._add_pattern_badge(
                f"{strip_prefix}Bottom Line",
                r2_complete,
                f"{len(r2_called)}/5 called" + ("" if r2_complete else f" (Missing: {set(row2) - set(r2_called)})")
            )

            # Four Corners
            # First & last in row 0, first & last in row 2
            corners = [row0[0], row0[-1], row2[0], row2[-1]]
            c_called = [sid for sid in corners if sid in self.called_numbers]
            c_complete = len(c_called) == 4
            self._add_pattern_badge(
                f"{strip_prefix}Four Corners",
                c_complete,
                f"{len(c_called)}/4 called" + ("" if c_complete else f" (Missing: {set(corners) - set(c_called)})")
            )

            # Full House
            strip_songs = [sid for row in strip for sid in row if sid > 0]
            s_called = [sid for sid in strip_songs if sid in self.called_numbers]
            fh_complete = len(s_called) == 15
            if fh_complete:
                has_any_full_house = True
            self._add_pattern_badge(
                f"{strip_prefix}Full House",
                fh_complete,
                f"{len(s_called)}/15 called" + ("" if fh_complete else f" (Missing {15 - len(s_called)})")
            )

        # Dual Full House for 2-strip
        if len(strips) == 2:
            dual_fh = len(called_ticket_songs) == 30
            self._add_pattern_badge(
                "Dual Full House (30 Songs)",
                dual_fh,
                f"{len(called_ticket_songs)}/30 called"
            )

        # Main verdict banner
        any_valid = early5_complete or has_any_full_house or any(
            len([sid for sid in strip[r] if sid > 0 and sid in self.called_numbers]) == 5
            for strip in strips for r in range(3)
        )

        if any_valid:
            self.lbl_main_status.setText("✅ AT LEAST 1 PRIZE CLAIM VALID!")
            self.lbl_main_status.setStyleSheet(f"""
                background-color: {THEME['emerald']};
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
            """)
            self.btn_award.setEnabled(True)
        else:
            self.lbl_main_status.setText("❌ BOGEY / NO CLAIM VALID YET")
            self.lbl_main_status.setStyleSheet(f"""
                background-color: {THEME['crimson']};
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
            """)
            self.btn_award.setEnabled(False)

    def _add_pattern_badge(self, name: str, is_complete: bool, detail: str):
        badge = QFrame()
        bg_col = THEME['bg_subtle']
        border_col = THEME['emerald'] if is_complete else THEME['border']
        badge.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        b_layout = QHBoxLayout(badge)
        b_layout.setContentsMargins(6, 4, 6, 4)

        icon = "✅" if is_complete else "⏳"
        lbl_n = QLabel(f"{icon} <b>{name}</b>")
        lbl_n.setFont(QFont("Arial", 10))
        lbl_n.setStyleSheet(f"color: {THEME['emerald'] if is_complete else THEME['text_primary']};")

        lbl_d = QLabel(detail)
        lbl_d.setFont(QFont("Arial", 9))
        lbl_d.setStyleSheet(f"color: {THEME['text_muted']};")

        b_layout.addWidget(lbl_n)
        b_layout.addStretch()
        b_layout.addWidget(lbl_d)

        self.patterns_vbox.addWidget(badge)

    def record_claim(self):
        """Save confirmed claim to claim_records in SQLite."""
        if not self.active_ticket:
            return

        winner_name = self.txt_winner_name.text().strip() or "Anonymous Winner"
        tid = self.active_ticket["ticket_id"]
        session_id = database.get_or_create_active_session()

        with database.get_connection() as conn:
            conn.execute("""
                INSERT INTO claim_records (session_id, ticket_id, pattern_name, verdict, claimed_by)
                VALUES (?, ?, ?, 'VALID', ?)
            """, (session_id, tid, "Winning Claim", winner_name))
            conn.commit()

        QMessageBox.information(
            self,
            "Claim Recorded",
            f"Winning claim successfully recorded for Ticket #{tid} ({winner_name})!"
        )
        self.txt_winner_name.clear()
