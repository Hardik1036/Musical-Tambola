"""
Ticket Engine UI Widget (PRD Module 2.2)
Allows host to select/upload custom background templates with thumbnail preview & resolution,
configure batch size (default 100), format mode, participant name/mobile slot masking,
generate algorithmic tickets to SQLite/JSON and generator/housie_tickets_output.html,
and preview immediately in default web browser.
"""
import os
import webbrowser
from pathlib import Path
from typing import Optional

from qt_compat import (
    Qt, QtGui,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QComboBox, QLineEdit, QFileDialog, QFrame,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QFont
)

from config import THEME, BRANDING_DIR, BASE_DIR
import database
from modules.ticket_engine import TicketEngine
from generator.generate_housie_tickets import generate_housie_tickets


class TicketGeneratorWidget(QWidget):
    """Host UI for generating, managing, and exporting Tambola tickets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = TicketEngine()
        self.template_path: Optional[str] = None
        self._init_ui()
        self._load_default_template()
        self.refresh_tickets_table()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Left Column: Generation & Branding Controls
        left_panel = QVBoxLayout()
        left_panel.setSpacing(12)

        gen_frame = QFrame()
        gen_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 14px;
            }}
        """)
        gen_layout = QVBoxLayout(gen_frame)
        gen_layout.setSpacing(10)

        lbl_title = QLabel("🎫 TICKET GENERATOR & TEMPLATE STUDIO")
        lbl_title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {THEME['gold']};")
        gen_layout.addWidget(lbl_title)

        # 1. Template Selection Button
        lbl_step1 = QLabel("1. Background Template:")
        lbl_step1.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl_step1.setStyleSheet(f"color: {THEME['text_primary']};")
        gen_layout.addWidget(lbl_step1)

        row_tpl = QHBoxLayout()
        btn_upload_tpl = QPushButton("📁 Upload / Select Background Template")
        btn_upload_tpl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_upload_tpl.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME['bg_card_hover']};
            }}
        """)
        btn_upload_tpl.clicked.connect(self.select_template_file)
        row_tpl.addWidget(btn_upload_tpl)
        gen_layout.addLayout(row_tpl)

        self.lbl_tpl_name = QLabel("Template: Default Festive Template")
        self.lbl_tpl_name.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        gen_layout.addWidget(self.lbl_tpl_name)

        self.lbl_tpl_res = QLabel("Resolution: Loading...")
        self.lbl_tpl_res.setStyleSheet(f"color: {THEME['emerald']}; font-size: 11px; font-weight: bold;")
        gen_layout.addWidget(self.lbl_tpl_res)

        # Template Thumbnail Preview
        self.lbl_preview_img = QLabel()
        self.lbl_preview_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_img.setFixedHeight(120)
        self.lbl_preview_img.setStyleSheet(f"""
            QLabel {{
                background-color: {THEME['bg_subtle']};
                border: 1px dashed {THEME['border']};
                border-radius: 8px;
            }}
        """)
        gen_layout.addWidget(self.lbl_preview_img)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"border-top: 1px solid {THEME['border']};")
        gen_layout.addWidget(sep)

        # 2. Configuration Controls
        lbl_step2 = QLabel("2. Batch Configuration:")
        lbl_step2.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl_step2.setStyleSheet(f"color: {THEME['text_primary']};")
        gen_layout.addWidget(lbl_step2)

        # Mode Selection
        row_mode = QHBoxLayout()
        lbl_mode = QLabel("Format:")
        lbl_mode.setStyleSheet(f"color: {THEME['text_primary']}; font-weight: bold;")
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "2-Strip per Page (Combined Single Person)",
            "1-Strip per Page"
        ])
        self.combo_mode.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        row_mode.addWidget(lbl_mode)
        row_mode.addWidget(self.combo_mode, stretch=1)
        gen_layout.addLayout(row_mode)

        # Batch Size (Default 100 sheets)
        row_counts = QHBoxLayout()
        lbl_count = QLabel("Number of Sheets:")
        lbl_count.setStyleSheet(f"color: {THEME['text_primary']}; font-weight: bold;")
        self.spin_count = QSpinBox()
        self.spin_count.setRange(1, 1000)
        self.spin_count.setValue(100)  # Default: 100 sheets
        self.spin_count.setStyleSheet(f"""
            QSpinBox {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px;
            }}
        """)

        lbl_start = QLabel("Start ID:")
        lbl_start.setStyleSheet(f"color: {THEME['text_primary']}; font-weight: bold;")
        self.spin_start_id = QSpinBox()
        self.spin_start_id.setRange(1, 9999)
        self.spin_start_id.setValue(1)
        self.spin_start_id.setStyleSheet(f"""
            QSpinBox {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px;
            }}
        """)

        row_counts.addWidget(lbl_count)
        row_counts.addWidget(self.spin_count)
        row_counts.addWidget(lbl_start)
        row_counts.addWidget(self.spin_start_id)
        gen_layout.addLayout(row_counts)

        # Participant Slots Checkbox (CSS Mask Overlay)
        self.chk_slots = QCheckBox("Include Participant Name & Mobile Slots in Overlay")
        self.chk_slots.setChecked(True)
        self.chk_slots.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 11px;")
        gen_layout.addWidget(self.chk_slots)

        # Print Song Numbers Checkbox (Default False)
        self.chk_show_song_number = QCheckBox("Print Song Numbers (1-90) on Tickets")
        self.chk_show_song_number.setChecked(False)
        self.chk_show_song_number.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 11px;")
        gen_layout.addWidget(self.chk_show_song_number)

        # Song Title Font Size Control
        row_font = QHBoxLayout()
        lbl_font = QLabel("Song Title Font Size (pt):")
        lbl_font.setStyleSheet(f"color: {THEME['text_primary']}; font-weight: bold;")
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 28)
        self.spin_font_size.setValue(17)
        self.spin_font_size.setStyleSheet(f"""
            QSpinBox {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        row_font.addWidget(lbl_font)
        row_font.addWidget(self.spin_font_size)
        gen_layout.addLayout(row_font)

        # Event Branding Title
        row_title = QHBoxLayout()
        lbl_ev = QLabel("Event Banner Title:")
        lbl_ev.setStyleSheet(f"color: {THEME['text_primary']};")
        self.txt_event_title = QLineEdit("Musical Tambola Night")
        self.txt_event_title.setStyleSheet(f"""
            QLineEdit {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        row_title.addWidget(lbl_ev)
        row_title.addWidget(self.txt_event_title)
        gen_layout.addLayout(row_title)

        # Batch Name Entry
        row_batch = QHBoxLayout()
        lbl_batch = QLabel("Batch / Event Name:")
        lbl_batch.setStyleSheet(f"color: {THEME['text_primary']}; font-weight: bold;")
        from datetime import datetime
        self.txt_batch_name = QLineEdit(datetime.now().strftime("musical_housie_tickets_%Y%m%d"))
        self.txt_batch_name.setStyleSheet(f"""
            QLineEdit {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['gold']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: bold;
            }}
        """)
        row_batch.addWidget(lbl_batch)
        row_batch.addWidget(self.txt_batch_name)
        gen_layout.addLayout(row_batch)

        lbl_archive_hint = QLabel("Saved to tickets_archive/<Batch_Name>.html & _registry.json")
        lbl_archive_hint.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 10px;")
        gen_layout.addWidget(lbl_archive_hint)

        # Generate Button
        self.btn_generate = QPushButton("✨ GENERATE & ARCHIVE TICKETS")
        self.btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.btn_generate.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['crimson']}, stop:1 {THEME['gold']});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['crimson_hover']}, stop:1 {THEME['gold_hover']});
            }}
        """)
        self.btn_generate.clicked.connect(self.generate_tickets)
        gen_layout.addWidget(self.btn_generate)

        # Quick Action Buttons
        row_actions = QHBoxLayout()
        self.btn_open_folder = QPushButton("📂 Open Tickets Folder")
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 7px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME['bg_card_hover']};
            }}
        """)
        self.btn_open_folder.clicked.connect(self.open_archive_folder)

        self.btn_preview_browser = QPushButton("🌐 Open in Browser")
        self.btn_preview_browser.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview_browser.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_preview_browser.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['gold']};
                color: {THEME['text_dark']};
                border: none;
                border-radius: 6px;
                padding: 7px;
            }}
            QPushButton:hover {{
                background-color: {THEME['gold_hover']};
            }}
        """)
        self.btn_preview_browser.clicked.connect(self.preview_in_browser)

        row_actions.addWidget(self.btn_open_folder)
        row_actions.addWidget(self.btn_preview_browser)
        gen_layout.addLayout(row_actions)

        left_panel.addWidget(gen_frame)

        # Export Actions Card (PDF & Save-As HTML)
        export_frame = QFrame()
        export_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 12px;
            }}
        """)
        export_layout = QVBoxLayout(export_frame)
        export_layout.setSpacing(8)

        lbl_exp_title = QLabel("🖨️ PDF VECTOR EXPORT")
        lbl_exp_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lbl_exp_title.setStyleSheet(f"color: {THEME['text_primary']};")
        export_layout.addWidget(lbl_exp_title)

        self.btn_export_pdf = QPushButton("📄 Export Printable Vector PDF Document")
        self.btn_export_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_pdf.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['crimson']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME['crimson_hover']};
            }}
        """)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        export_layout.addWidget(self.btn_export_pdf)

        left_panel.addWidget(export_frame)
        main_layout.addLayout(left_panel, stretch=5)

        # Right Column: Generated Ticket Registry Table
        right_frame = QFrame()
        right_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 14px;
            }}
        """)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setSpacing(10)

        r_header = QHBoxLayout()
        lbl_reg = QLabel("📋 REGISTERED TICKETS IN DATABASE")
        lbl_reg.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        lbl_reg.setStyleSheet(f"color: {THEME['gold']};")

        btn_clear_tickets = QPushButton("🗑️ Clear All Tickets")
        btn_clear_tickets.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_tickets.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME['crimson']};
                border: 1px solid {THEME['crimson']};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
            }}
        """)
        btn_clear_tickets.clicked.connect(self.clear_all_tickets)

        r_header.addWidget(lbl_reg)
        r_header.addStretch()
        r_header.addWidget(btn_clear_tickets)
        right_layout.addLayout(r_header)

        self.table_tickets = QTableWidget()
        self.table_tickets.setColumnCount(4)
        self.table_tickets.setHorizontalHeaderLabels(["Ticket ID", "Mode", "Song Count", "Created At"])
        self.table_tickets.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tickets.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tickets.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tickets.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_tickets.setStyleSheet(f"""
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
        right_layout.addWidget(self.table_tickets)

        main_layout.addWidget(right_frame, stretch=7)

    def _load_default_template(self):
        """Auto-load default background template."""
        candidates = [
            BASE_DIR / "generator" / "ticket_template.png",
            BASE_DIR / "assets" / "branding" / "Festive_Musical_Housie_Template.png",
        ]
        for c in candidates:
            if c.is_file():
                self._apply_template_image(str(c))
                break

    def select_template_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Template (.png, .jpg, .jpeg)",
            str(BASE_DIR),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_path:
            self._apply_template_image(file_path)

    def _apply_template_image(self, file_path: str):
        p = Path(file_path)
        if not p.is_file():
            QMessageBox.critical(self, "Invalid File", f"Selected image not found:\n{file_path}")
            return

        try:
            pixmap = QtGui.QPixmap(file_path)
            if pixmap.isNull():
                raise ValueError("Could not decode image.")

            self.template_path = str(p.resolve())
            w, h = pixmap.width(), pixmap.height()
            self.lbl_tpl_name.setText(f"Template: {p.name}")
            self.lbl_tpl_res.setText(f"Resolution: {w} × {h} px")

            # Scale thumbnail
            scaled = pixmap.scaled(
                260, 110,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_preview_img.setPixmap(scaled)
        except Exception as e:
            QMessageBox.critical(self, "Image Load Error", f"Failed to load image preview:\n{e}")

    def open_archive_folder(self):
        """Open tickets_archive directory in file explorer."""
        from config import TICKETS_ARCHIVE_DIR
        TICKETS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        folder = str(TICKETS_ARCHIVE_DIR)
        try:
            if os.name == 'nt':
                os.startfile(folder)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', folder])
        except Exception as e:
            QMessageBox.critical(self, "Folder Error", f"Could not open archive folder:\n{e}")

    def generate_tickets(self):
        mode_idx = self.combo_mode.currentIndex()
        mode = "2-strip" if mode_idx == 0 else "1-strip"
        count = self.spin_count.value()
        show_slots = self.chk_slots.isChecked()
        raw_name = self.txt_batch_name.text().strip()

        try:
            # 1. Trigger generate_housie_tickets engine with batch_name
            out_html = generate_housie_tickets(
                num_sheets=count,
                format_mode=mode,
                template_path=self.template_path,
                show_participant_slots=show_slots,
                batch_name=raw_name,
                save_to_database=True,
                show_song_number=self.chk_show_song_number.isChecked(),
                calibration={"font_title": {"size_pt": float(self.spin_font_size.value()), "weight": 800}}
            )
            self.last_generated_html = out_html

            self.refresh_tickets_table()
            from generator.generate_housie_tickets import sanitize_batch_name
            clean_batch = sanitize_batch_name(raw_name)

            QMessageBox.information(
                self,
                "Archive Generation Success",
                f"Successfully generated and archived {count} {mode.upper()} sheets!\n\n"
                f"📁 Dedicated Archive Storage:\n"
                f"• Printable Document: tickets_archive/{clean_batch}.html\n"
                f"• Layout Registry: tickets_archive/{clean_batch}_registry.json\n\n"
                f"Click 'Open in Browser' to view or print."
            )
        except Exception as e:
            QMessageBox.critical(self, "Generation Error", str(e))

    def preview_in_browser(self):
        from config import TICKETS_ARCHIVE_DIR
        target = None
        if hasattr(self, 'last_generated_html') and self.last_generated_html and Path(self.last_generated_html).is_file():
            target = Path(self.last_generated_html)
        else:
            raw_name = self.txt_batch_name.text().strip()
            from generator.generate_housie_tickets import sanitize_batch_name
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
            QMessageBox.warning(
                self,
                "File Not Found",
                "Please click 'Generate & Archive Tickets' first before previewing."
            )
            return

        try:
            uri = target.resolve().as_uri()
            webbrowser.open_new_tab(uri)
        except Exception as e:
            QMessageBox.critical(self, "Browser Error", f"Could not launch browser:\n{e}")


    def refresh_tickets_table(self):
        tickets = database.get_all_tickets()
        self.table_tickets.setRowCount(len(tickets))
        for row, t in enumerate(tickets):
            num_songs = sum(1 for strip in t.get("strips", []) for r in strip for c in r if c > 0)
            self.table_tickets.setItem(row, 0, QTableWidgetItem(f"#{t['ticket_id']}"))
            self.table_tickets.setItem(row, 1, QTableWidgetItem(t.get('mode', '1-strip')))
            self.table_tickets.setItem(row, 2, QTableWidgetItem(f"{num_songs} Songs"))
            self.table_tickets.setItem(row, 3, QTableWidgetItem(t.get('created_at', '')))

    def export_pdf(self):
        tickets = database.get_all_tickets()
        if not tickets:
            QMessageBox.warning(self, "No Tickets", "Please generate tickets first before exporting.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Tickets PDF", "Musical_Tambola_Tickets.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        try:
            title = self.txt_event_title.text().strip() or "Musical Tambola Night"
            self.engine.export_pdf(tickets, out_path, event_title=title, branding_image_path=self.template_path)
            QMessageBox.information(self, "Export Complete", f"Printable PDF successfully saved to:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def clear_all_tickets(self):
        reply = QMessageBox.question(self, "Clear All", "Delete all registered tickets from database?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            database.clear_all_tickets()
            self.refresh_tickets_table()
