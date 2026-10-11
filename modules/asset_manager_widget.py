"""
Asset Manager UI Widget
Universal metadata import (.xlsx, .csv, .docx, .txt), bulk audio file pairing,
manual audio file reassignment, and track preview.
"""
import os
from pathlib import Path
from typing import Optional

from qt_compat import (
    Qt,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QFileDialog, QLineEdit,
    QFont, QColor
)

from config import THEME, SONGS_DIR
import database
from modules.asset_manager import AssetManager
from modules.audio_player import AudioPlayer


class AssetManagerWidget(QWidget):
    """Song and Audio Catalog management interface."""

    def __init__(self, audio_player: Optional[AudioPlayer] = None, parent=None):
        super().__init__(parent)
        self.audio_player = audio_player or AudioPlayer()
        self.asset_mgr = AssetManager()
        self._init_ui()
        self.refresh_catalog_table()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Top Control Toolbar
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 12px;
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setSpacing(10)

        # Import button
        btn_import = QPushButton("📂 Import Catalog (.xlsx, .csv, .docx, .txt)")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        btn_import.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['crimson']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {THEME['crimson_hover']};
            }}
        """)
        btn_import.clicked.connect(self.import_catalog_file)

        # Bulk Map button
        btn_bulk_map = QPushButton("🔍 Auto-Pair Audio Files")
        btn_bulk_map.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_bulk_map.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        btn_bulk_map.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['gold']};
                color: {THEME['text_dark']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {THEME['gold_hover']};
            }}
        """)
        btn_bulk_map.clicked.connect(self.bulk_auto_pair_audio)

        # Change Audio Folder
        btn_audio_dir = QPushButton("📁 Audio Folder...")
        btn_audio_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_audio_dir.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 8px 14px;
            }}
        """)
        btn_audio_dir.clicked.connect(self.select_audio_folder)

        # Default Seeding button
        btn_seed_default = QPushButton("🔄 Reset Default Bollywood Hits")
        btn_seed_default.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_seed_default.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 8px 14px;
            }}
            QPushButton:hover {{
                color: {THEME['gold']};
                border-color: {THEME['gold']};
            }}
        """)
        btn_seed_default.clicked.connect(self.seed_default_catalog)

        toolbar_layout.addWidget(btn_import)
        toolbar_layout.addWidget(btn_bulk_map)
        toolbar_layout.addWidget(btn_audio_dir)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(btn_seed_default)

        main_layout.addWidget(toolbar_frame)

        # Status Summary Ribbon
        self.lbl_catalog_summary = QLabel("Catalog: 90 Songs | 90 Mapped with Audio")
        self.lbl_catalog_summary.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.lbl_catalog_summary.setStyleSheet(f"color: {THEME['gold']}; padding-left: 4px;")
        main_layout.addWidget(self.lbl_catalog_summary)

        # Songs Table
        self.table_songs = QTableWidget()
        self.table_songs.setColumnCount(6)
        self.table_songs.setHorizontalHeaderLabels(["ID", "Song Title", "Artist / Movie", "Year", "Audio File Status", "Actions"])
        self.table_songs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_songs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_songs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_songs.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_songs.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table_songs.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.table_songs.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME['bg_card']};
                color: {THEME['text_primary']};
                gridline-color: {THEME['border']};
                border: 1px solid {THEME['border']};
                border-radius: 8px;
            }}
            QHeaderView::section {{
                background-color: {THEME['bg_subtle']};
                color: {THEME['text_secondary']};
                padding: 8px;
                font-weight: bold;
                border: 1px solid {THEME['border']};
            }}
        """)
        main_layout.addWidget(self.table_songs, stretch=1)

    def refresh_catalog_table(self):
        songs = database.get_all_songs()
        self.table_songs.setRowCount(len(songs))
        mapped_count = 0

        for row, s in enumerate(songs):
            sid = s["id"]
            audio_path = s.get("audio_path", "")
            has_audio = bool(audio_path and Path(audio_path).exists())
            if has_audio:
                mapped_count += 1

            self.table_songs.setItem(row, 0, QTableWidgetItem(f"#{sid:02d}"))
            self.table_songs.setItem(row, 1, QTableWidgetItem(s["title"]))
            self.table_songs.setItem(row, 2, QTableWidgetItem(s.get("artist", "")))
            self.table_songs.setItem(row, 3, QTableWidgetItem(s.get("year", "")))

            # Audio Status
            if has_audio:
                status_text = f"✓ {Path(audio_path).name}"
                item_status = QTableWidgetItem(status_text)
                item_status.setForeground(QColor(THEME['emerald']))
            else:
                item_status = QTableWidgetItem("⚠️ Missing Audio")
                item_status.setForeground(QColor(THEME['crimson']))
            self.table_songs.setItem(row, 4, item_status)

            # Action Buttons widget
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            btn_play = QPushButton("▶")
            btn_play.setFixedSize(28, 26)
            btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_play.setEnabled(has_audio)
            btn_play.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME['gold']};
                    color: {THEME['text_dark']};
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }}
            """)
            btn_play.clicked.connect(lambda ch, p=audio_path: self.preview_audio(p))

            btn_browse = QPushButton("📁")
            btn_browse.setFixedSize(28, 26)
            btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_browse.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME['bg_subtle']};
                    color: {THEME['text_primary']};
                    border: 1px solid {THEME['border']};
                    border-radius: 4px;
                }}
            """)
            btn_browse.clicked.connect(lambda ch, target_id=sid: self.browse_single_audio(target_id))

            btn_layout.addWidget(btn_play)
            btn_layout.addWidget(btn_browse)
            self.table_songs.setCellWidget(row, 5, btn_container)

        self.lbl_catalog_summary.setText(
            f"Catalog: {len(songs)} Songs | {mapped_count} Mapped with Audio | {len(songs) - mapped_count} Missing Audio"
        )

    def import_catalog_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Song Catalog",
            "",
            "Catalog Files (*.xlsx *.csv *.docx *.txt);;Excel (*.xlsx);;CSV (*.csv);;Word (*.docx);;Text (*.txt)"
        )
        if not file_path:
            return

        try:
            total, mapped = self.asset_mgr.import_and_save(file_path, auto_map=True)
            self.refresh_catalog_table()
            QMessageBox.information(
                self,
                "Import Successful",
                f"Imported {total} tracks from {Path(file_path).name}.\n{mapped} tracks successfully mapped with audio files!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import file:\n{e}")

    def bulk_auto_pair_audio(self):
        updated = self.asset_mgr.map_audio_files()
        mapped = sum(1 for s in updated if s.get("audio_path"))
        self.refresh_catalog_table()
        QMessageBox.information(
            self,
            "Audio Mapping Complete",
            f"Scanned {self.asset_mgr.audio_dir}.\n{mapped} / {len(updated)} songs are mapped with audio files!"
        )

    def select_audio_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Audio Folder", str(self.asset_mgr.audio_dir))
        if folder:
            self.asset_mgr.audio_dir = Path(folder)
            self.bulk_auto_pair_audio()

    def browse_single_audio(self, song_id: int):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select Audio File for Song #{song_id}",
            str(self.asset_mgr.audio_dir),
            "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a)"
        )
        if file_path:
            database.update_audio_path(song_id, file_path)
            self.refresh_catalog_table()

    def preview_audio(self, path: str):
        if path and Path(path).exists():
            self.audio_player.play_track(path)

    def seed_default_catalog(self):
        reply = QMessageBox.question(
            self,
            "Reset Catalog",
            "Reset song catalog to the 90 Evergreen Bollywood and Pop Classics?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.seed_default_songs(force=True)
            self.asset_mgr.map_audio_files()
            self.refresh_catalog_table()
