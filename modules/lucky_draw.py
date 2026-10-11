"""
Module 2.4: Lucky Draw & Tie-Breaker Raffle
Supports pool filtering (active called numbers, registered tickets, custom range),
multi-winner selection (1-10 winners), suspenseful rolling animation, and persistent audit logging.
"""
import csv
import json
import random
import logging
from typing import List, Dict, Any, Optional

from qt_compat import (
    Qt, QTimer,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QMessageBox, QFileDialog,
    QFont, QColor
)

from config import THEME
import database

logger = logging.getLogger("tambola.lucky_draw")


class LuckyDrawWidget(QWidget):
    """Raffle drawer with suspenseful rolling animation and audit history."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._on_animation_step)
        
        self.animation_ticks = 0
        self.max_ticks = 25
        self.current_pool: List[Any] = []
        self.pending_winners: List[Any] = []
        self.animating_display_items: List[QLabel] = []

        self._init_ui()
        self.refresh_audit_table()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Left Column: Raffle Controls & Suspense Stage
        stage_panel = QVBoxLayout()
        stage_panel.setSpacing(14)

        # Control Configuration Card
        config_frame = QFrame()
        config_frame.setObjectName("ConfigFrame")
        config_frame.setStyleSheet(f"""
            #ConfigFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 14px;
            }}
        """)
        config_layout = QVBoxLayout(config_frame)
        config_layout.setSpacing(10)

        lbl_header = QLabel("🎁 LUCKY DRAW & TIE-BREAKER")
        lbl_header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl_header.setStyleSheet(f"color: {THEME['gold']};")
        config_layout.addWidget(lbl_header)

        # Prize Label Input
        row1 = QHBoxLayout()
        lbl_prize = QLabel("Prize / Reason:")
        lbl_prize.setStyleSheet(f"color: {THEME['text_primary']}; font-weight: bold;")
        self.txt_prize = QLineEdit("Tie-Breaker Prize")
        self.txt_prize.setStyleSheet(f"""
            QLineEdit {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        row1.addWidget(lbl_prize)
        row1.addWidget(self.txt_prize)
        config_layout.addLayout(row1)

        # Pool Source Selector & Winner Count
        row2 = QHBoxLayout()
        lbl_pool = QLabel("Draw Pool:")
        lbl_pool.setStyleSheet(f"color: {THEME['text_primary']}; font-weight: bold;")
        self.combo_pool = QComboBox()
        self.combo_pool.addItems([
            "Active Called Songs/Numbers",
            "Registered Ticket IDs",
            "Custom Numeric Range"
        ])
        self.combo_pool.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        self.combo_pool.currentIndexChanged.connect(self._on_pool_changed)

        lbl_count = QLabel("Winners:")
        lbl_count.setStyleSheet(f"color: {THEME['text_primary']}; font-weight: bold;")
        self.spin_count = QSpinBox()
        self.spin_count.setRange(1, 10)
        self.spin_count.setValue(1)
        self.spin_count.setStyleSheet(f"""
            QSpinBox {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px;
            }}
        """)

        row2.addWidget(lbl_pool)
        row2.addWidget(self.combo_pool, stretch=1)
        row2.addWidget(lbl_count)
        row2.addWidget(self.spin_count)
        config_layout.addLayout(row2)

        # Custom Range Inputs (hidden by default)
        self.custom_range_row = QHBoxLayout()
        self.lbl_range = QLabel("Range (Min - Max):")
        self.lbl_range.setStyleSheet(f"color: {THEME['text_primary']};")
        self.spin_min = QSpinBox()
        self.spin_min.setRange(1, 10000)
        self.spin_min.setValue(1)
        self.spin_max = QSpinBox()
        self.spin_max.setRange(1, 10000)
        self.spin_max.setValue(100)
        self.custom_range_row.addWidget(self.lbl_range)
        self.custom_range_row.addWidget(self.spin_min)
        self.custom_range_row.addWidget(QLabel("-"))
        self.custom_range_row.addWidget(self.spin_max)
        self.custom_range_row.addStretch()
        config_layout.addLayout(self.custom_range_row)
        self._toggle_custom_range(False)

        # Big Draw Button
        self.btn_draw = QPushButton("🎰 SPIN & DRAW WINNER(S)")
        self.btn_draw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_draw.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.btn_draw.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['crimson']}, stop:1 {THEME['gold']});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['crimson_hover']}, stop:1 {THEME['gold_hover']});
            }}
            QPushButton:disabled {{
                background: {THEME['bg_card_hover']};
                color: {THEME['text_muted']};
            }}
        """)
        self.btn_draw.clicked.connect(self.start_draw_animation)
        config_layout.addWidget(self.btn_draw)

        stage_panel.addWidget(config_frame)

        # Rolling Suspense Stage Display
        stage_frame = QFrame()
        stage_frame.setObjectName("StageFrame")
        stage_frame.setStyleSheet(f"""
            #StageFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {THEME['bg_card']}, stop:1 {THEME['bg_subtle']});
                border: 2px solid {THEME['gold']};
                border-radius: 12px;
                padding: 24px;
            }}
        """)
        self.stage_layout = QVBoxLayout(stage_frame)
        self.stage_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_stage_status = QLabel("Ready for the Draw!")
        self.lbl_stage_status.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.lbl_stage_status.setStyleSheet(f"color: {THEME['text_secondary']};")
        self.lbl_stage_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stage_layout.addWidget(self.lbl_stage_status)

        # Dynamic Winner cards container
        self.winners_container = QWidget()
        self.winners_layout = QHBoxLayout(self.winners_container)
        self.winners_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stage_layout.addWidget(self.winners_container)

        stage_panel.addWidget(stage_frame, stretch=1)
        main_layout.addLayout(stage_panel, stretch=6)

        # Right Column: Persistent Audit Log Table
        audit_frame = QFrame()
        audit_frame.setObjectName("AuditFrame")
        audit_frame.setStyleSheet(f"""
            #AuditFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 14px;
            }}
        """)
        audit_layout = QVBoxLayout(audit_frame)
        audit_layout.setSpacing(10)

        audit_header = QHBoxLayout()
        lbl_audit = QLabel("📋 ROUND AUDIT LOG")
        lbl_audit.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        lbl_audit.setStyleSheet(f"color: {THEME['gold']};")

        btn_export_csv = QPushButton("📥 Export CSV")
        btn_export_csv.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export_csv.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
            }}
        """)
        btn_export_csv.clicked.connect(self.export_audit_csv)

        btn_clear_log = QPushButton("🗑️ Clear")
        btn_clear_log.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_log.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME['crimson']};
                border: 1px solid {THEME['crimson']};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
            }}
        """)
        btn_clear_log.clicked.connect(self.clear_audit_log)

        audit_header.addWidget(lbl_audit)
        audit_header.addStretch()
        audit_header.addWidget(btn_export_csv)
        audit_header.addWidget(btn_clear_log)
        audit_layout.addLayout(audit_header)

        # Audit Table
        self.table_audit = QTableWidget()
        self.table_audit.setColumnCount(4)
        self.table_audit.setHorizontalHeaderLabels(["Round", "Prize", "Winners", "Timestamp"])
        self.table_audit.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_audit.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_audit.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                gridline-color: {THEME['border']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
            QHeaderView::section {{
                background-color: {THEME['bg_card']};
                color: {THEME['text_secondary']};
                padding: 6px;
                font-weight: bold;
                border: 1px solid {THEME['border']};
            }}
        """)
        audit_layout.addWidget(self.table_audit)

        main_layout.addWidget(audit_frame, stretch=5)

    def _on_pool_changed(self, idx: int):
        self._toggle_custom_range(idx == 2)

    def _toggle_custom_range(self, visible: bool):
        self.lbl_range.setVisible(visible)
        self.spin_min.setVisible(visible)
        self.spin_max.setVisible(visible)

    def refresh_audit_table(self):
        records = database.get_lucky_draw_records()
        self.table_audit.setRowCount(len(records))
        for row, rec in enumerate(records):
            winners_str = ", ".join(str(w) for w in rec.get("winner_ids", []))
            self.table_audit.setItem(row, 0, QTableWidgetItem(f"#{rec['round_id']}"))
            self.table_audit.setItem(row, 1, QTableWidgetItem(rec['prize_name']))
            self.table_audit.setItem(row, 2, QTableWidgetItem(winners_str))
            self.table_audit.setItem(row, 3, QTableWidgetItem(rec.get('drawn_at', '')))

    def _resolve_pool(self) -> List[Any]:
        choice = self.combo_pool.currentText()
        if "Active Called" in choice:
            session_id = database.get_or_create_active_session()
            called = database.get_called_numbers(session_id)
            all_songs = {s["id"]: s["title"] for s in database.get_all_songs()}
            return [f"#{num} ({all_songs.get(num, '')})" for num in called]
        elif "Registered Ticket" in choice:
            tickets = database.get_all_tickets()
            return [f"Ticket #{t['ticket_id']}" for t in tickets]
        else:
            # Custom range
            min_val = self.spin_min.value()
            max_val = self.spin_max.value()
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            return [f"#{n}" for n in range(min_val, max_val + 1)]

    def start_draw_animation(self):
        pool = self._resolve_pool()
        if not pool:
            QMessageBox.warning(self, "Empty Pool", "The selected draw pool contains 0 candidates!")
            return

        winner_count = self.spin_count.value()
        if len(pool) < winner_count:
            winner_count = len(pool)

        # Clear display stage
        while self.winners_layout.count() > 0:
            item = self.winners_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.current_pool = pool
        self.pending_winners = random.sample(pool, winner_count)
        self.animating_display_items = []

        # Create cards for each winner
        for i in range(winner_count):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {THEME['bg_card']};
                    border: 2px solid {THEME['gold']};
                    border-radius: 10px;
                    padding: 12px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            lbl_title = QLabel(f"Winner #{i+1}")
            lbl_title.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            lbl_title.setStyleSheet(f"color: {THEME['gold']};")
            lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl_val = QLabel("???")
            lbl_val.setFont(QFont("Arial", 20, QFont.Weight.Bold))
            lbl_val.setStyleSheet(f"color: {THEME['text_primary']};")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

            card_layout.addWidget(lbl_title)
            card_layout.addWidget(lbl_val)
            self.winners_layout.addWidget(card)
            self.animating_display_items.append(lbl_val)

        self.animation_ticks = 0
        self.btn_draw.setEnabled(False)
        self.lbl_stage_status.setText("🎰 Spinning... Best of luck!")
        self.lbl_stage_status.setStyleSheet(f"color: {THEME['gold']};")
        self.animation_timer.start(80)

    def _on_animation_step(self):
        self.animation_ticks += 1
        # Shuffle temporary numbers on screen
        for lbl in self.animating_display_items:
            lbl.setText(str(random.choice(self.current_pool)))

        if self.animation_ticks >= self.max_ticks:
            self.animation_timer.stop()
            self._finalize_draw()

    def _finalize_draw(self):
        # Reveal actual winners
        for idx, lbl in enumerate(self.animating_display_items):
            lbl.setText(str(self.pending_winners[idx]))
            lbl.setStyleSheet(f"color: {THEME['emerald']}; font-size: 22px; font-weight: bold;")

        self.lbl_stage_status.setText("🎉 CONGRATULATIONS TO THE WINNER(S)!")
        self.lbl_stage_status.setStyleSheet(f"color: {THEME['emerald']};")
        self.btn_draw.setEnabled(True)

        # Save to database audit log
        prize = self.txt_prize.text().strip() or "Lucky Draw"
        pool_type = self.combo_pool.currentText()
        database.add_lucky_draw_record(prize, pool_type, self.pending_winners)
        self.refresh_audit_table()

    def export_audit_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Audit Log", "lucky_draw_audit.csv", "CSV Files (*.csv)")
        if not path:
            return

        records = database.get_lucky_draw_records()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Round ID", "Prize", "Pool Type", "Winners", "Drawn At"])
            for r in records:
                writer.writerow([r["round_id"], r["prize_name"], r["pool_type"], ", ".join(r["winner_ids"]), r.get("drawn_at")])

        QMessageBox.information(self, "Export Success", f"Audit log exported to {path}")

    def clear_audit_log(self):
        reply = QMessageBox.question(self, "Clear Log", "Clear all lucky draw audit records?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            database.clear_lucky_draw_records()
            self.refresh_audit_table()
