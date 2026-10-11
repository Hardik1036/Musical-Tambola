"""
Module 2.3: Live Gameplay Engine & Master Calling Board
Interactive 90-number grid caller, random selector without replacement,
undo/reset controls, active call logging, and integrated audio player with real-time seek bar.
"""
import random
import logging
from typing import Optional, List, Dict, Any

from qt_compat import (
    Qt, QTimer, pyqtSignal,
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QSlider, QProgressBar, QFrame, QMessageBox,
    QScrollArea, QCheckBox, QSizePolicy,
    QFont, QColor
)

from config import THEME, TOTAL_NUMBERS
import database
from modules.audio_player import AudioPlayer

logger = logging.getLogger("tambola.game_host")


class GameHostWidget(QWidget):
    """Main Host Interface: 90-grid master caller, random selector, and audio controls."""
    call_made_signal = pyqtSignal(int)  # Emitted when a number is called

    def __init__(self, audio_player: Optional[AudioPlayer] = None, parent=None):
        super().__init__(parent)
        self.audio_player = audio_player or AudioPlayer()
        self.session_id = database.get_or_create_active_session()
        self.song_catalog = {s["id"]: s for s in database.get_all_songs()}
        
        self.called_numbers = set(database.get_called_numbers(self.session_id))
        self.current_song_id: Optional[int] = None
        self.is_scrubbing = False

        self._init_ui()
        self._init_timers()
        self._refresh_board_state()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Left / Center Area: Board and Calling Controls
        left_panel = QVBoxLayout()
        left_panel.setSpacing(12)

        # 1. Top Header Stats & Actions
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_frame.setStyleSheet(f"""
            #HeaderFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 12px;
            }}
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)

        # Stats display
        self.lbl_stats = QLabel("Called: 0 / 90")
        self.lbl_stats.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.lbl_stats.setStyleSheet(f"color: {THEME['gold']};")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, TOTAL_NUMBERS)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {THEME['bg_subtle']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                text-align: center;
                color: {THEME['text_primary']};
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {THEME['crimson']};
                border-radius: 5px;
            }}
        """)

        header_layout.addWidget(self.lbl_stats)
        header_layout.addWidget(self.progress_bar)
        header_layout.addStretch()

        # Action Buttons
        self.btn_draw = QPushButton("🎲 DRAW NEXT SONG")
        self.btn_draw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_draw.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.btn_draw.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['crimson']}, stop:1 {THEME['gold']});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 22px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['crimson_hover']}, stop:1 {THEME['gold_hover']});
            }}
            QPushButton:disabled {{
                background: {THEME['bg_card_hover']};
                color: {THEME['text_muted']};
            }}
        """)
        self.btn_draw.clicked.connect(self.draw_random_number)

        self.btn_undo = QPushButton("↩️ Undo")
        self.btn_undo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_undo.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['bg_card_hover']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME['border']};
            }}
        """)
        self.btn_undo.clicked.connect(self.undo_call)

        self.btn_reset = QPushButton("🔄 Reset Game")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']};
                border-radius: 8px;
                padding: 8px 14px;
            }}
            QPushButton:hover {{
                color: {THEME['crimson']};
                border-color: {THEME['crimson']};
            }}
        """)
        self.btn_reset.clicked.connect(self.confirm_reset_game)

        header_layout.addWidget(self.btn_draw)
        header_layout.addWidget(self.btn_undo)
        header_layout.addWidget(self.btn_reset)

        left_panel.addWidget(header_frame)

        # 2. 90-Grid Master Calling Board
        board_frame = QFrame()
        board_frame.setObjectName("BoardFrame")
        board_frame.setStyleSheet(f"""
            #BoardFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 10px;
            }}
        """)
        board_layout = QGridLayout(board_frame)
        board_layout.setSpacing(6)
        board_layout.setContentsMargins(8, 8, 8, 8)

        self.grid_buttons: Dict[int, QPushButton] = {}

        # 90 numbers arranged in 10 rows x 9 cols (each col = decade)
        for num in range(1, 91):
            btn = QPushButton(str(num))
            btn.setFixedSize(50, 44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            btn.setProperty("song_id", num)
            btn.clicked.connect(lambda checked, n=num: self.on_number_clicked(n))
            
            # Row and column coordinates (0-9 rows, 0-8 cols)
            r = (num - 1) // 9
            c = (num - 1) % 9
            board_layout.addWidget(btn, r, c)
            self.grid_buttons[num] = btn

        left_panel.addWidget(board_frame)

        # 3. Audio Player Bar with Real-time Scrubber
        audio_frame = QFrame()
        audio_frame.setObjectName("AudioFrame")
        audio_frame.setStyleSheet(f"""
            #AudioFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 10px 14px;
            }}
        """)
        audio_layout = QVBoxLayout(audio_frame)
        audio_layout.setSpacing(8)

        # Track metadata label
        self.lbl_now_playing = QLabel("🎵 Ready - No song playing")
        self.lbl_now_playing.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.lbl_now_playing.setStyleSheet(f"color: {THEME['text_primary']};")
        audio_layout.addWidget(self.lbl_now_playing)

        # Scrubber bar (Slider + Timers)
        scrubber_layout = QHBoxLayout()
        self.lbl_time_curr = QLabel("00:00")
        self.lbl_time_curr.setStyleSheet(f"color: {THEME['text_muted']}; font-family: monospace;")
        
        self.slider_seek = QSlider(Qt.Orientation.Horizontal)
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.setValue(0)
        self.slider_seek.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_seek.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: {THEME['bg_subtle']};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {THEME['gold']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {THEME['text_primary']};
                border: 2px solid {THEME['gold']};
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }}
        """)
        self.slider_seek.sliderPressed.connect(self._on_seek_pressed)
        self.slider_seek.sliderReleased.connect(self._on_seek_released)
        self.slider_seek.valueChanged.connect(self._on_seek_value_changed)

        self.lbl_time_total = QLabel("00:00")
        self.lbl_time_total.setStyleSheet(f"color: {THEME['text_muted']}; font-family: monospace;")

        scrubber_layout.addWidget(self.lbl_time_curr)
        scrubber_layout.addWidget(self.slider_seek)
        scrubber_layout.addWidget(self.lbl_time_total)
        audio_layout.addLayout(scrubber_layout)

        # Audio control buttons row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        self.btn_play_pause = QPushButton("▶ Play")
        self.btn_play_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play_pause.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['gold']};
                color: {THEME['text_dark']};
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {THEME['gold_hover']};
            }}
        """)
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)

        self.btn_replay = QPushButton("↺ Replay")
        self.btn_replay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_replay.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['bg_card_hover']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {THEME['border']};
            }}
        """)
        self.btn_replay.clicked.connect(self.replay_current_song)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['bg_card_hover']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {THEME['border']};
            }}
        """)
        self.btn_stop.clicked.connect(self.stop_audio)

        # Volume slider
        lbl_vol = QLabel("🔊")
        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(80)
        self.slider_vol.setFixedWidth(90)
        self.slider_vol.valueChanged.connect(self.change_volume)

        # Auto-play toggle
        self.chk_autoplay = QCheckBox("Auto-play on draw")
        self.chk_autoplay.setChecked(True)
        self.chk_autoplay.setStyleSheet(f"color: {THEME['text_secondary']};")

        controls_layout.addWidget(self.btn_play_pause)
        controls_layout.addWidget(self.btn_replay)
        controls_layout.addWidget(self.btn_stop)
        controls_layout.addSpacing(15)
        controls_layout.addWidget(lbl_vol)
        controls_layout.addWidget(self.slider_vol)
        controls_layout.addStretch()
        controls_layout.addWidget(self.chk_autoplay)

        audio_layout.addLayout(controls_layout)
        left_panel.addWidget(audio_frame)

        main_layout.addLayout(left_panel, stretch=7)

        # Right Panel: Spotlight Display & Recent Calls Ribbon
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)

        # Active Big Number Display
        spotlight_frame = QFrame()
        spotlight_frame.setObjectName("SpotlightFrame")
        spotlight_frame.setStyleSheet(f"""
            #SpotlightFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {THEME['bg_card']}, stop:1 {THEME['bg_subtle']});
                border: 2px solid {THEME['border_highlight']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        spotlight_layout = QVBoxLayout(spotlight_frame)
        spotlight_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_spotlight_title = QLabel("CURRENT SONG")
        lbl_spotlight_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl_spotlight_title.setStyleSheet(f"color: {THEME['gold']}; letter-spacing: 2px;")
        lbl_spotlight_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_big_number = QLabel("--")
        self.lbl_big_number.setFont(QFont("Arial", 54, QFont.Weight.Bold))
        self.lbl_big_number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_big_number.setStyleSheet(f"color: {THEME['gold']};")

        self.lbl_spotlight_song = QLabel("No song called yet")
        self.lbl_spotlight_song.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.lbl_spotlight_song.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_spotlight_song.setWordWrap(True)
        self.lbl_spotlight_song.setStyleSheet(f"color: {THEME['text_primary']};")

        self.lbl_spotlight_artist = QLabel("")
        self.lbl_spotlight_artist.setFont(QFont("Arial", 10))
        self.lbl_spotlight_artist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_spotlight_artist.setStyleSheet(f"color: {THEME['text_secondary']};")

        spotlight_layout.addWidget(lbl_spotlight_title)
        spotlight_layout.addWidget(self.lbl_big_number)
        spotlight_layout.addWidget(self.lbl_spotlight_song)
        spotlight_layout.addWidget(self.lbl_spotlight_artist)

        right_panel.addWidget(spotlight_frame)

        # Call History Feed
        history_frame = QFrame()
        history_frame.setObjectName("HistoryFrame")
        history_frame.setStyleSheet(f"""
            #HistoryFrame {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
                padding: 12px;
            }}
        """)
        hist_layout = QVBoxLayout(history_frame)
        
        lbl_hist_title = QLabel("📜 RECENT CALL HISTORY")
        lbl_hist_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl_hist_title.setStyleSheet(f"color: {THEME['text_secondary']};")
        hist_layout.addWidget(lbl_hist_title)

        self.scroll_hist = QScrollArea()
        self.scroll_hist.setWidgetResizable(True)
        self.scroll_hist.setStyleSheet("background: transparent; border: none;")
        self.hist_container = QWidget()
        self.hist_vbox = QVBoxLayout(self.hist_container)
        self.hist_vbox.setSpacing(6)
        self.hist_vbox.setContentsMargins(0, 0, 0, 0)
        self.hist_vbox.addStretch()
        self.scroll_hist.setWidget(self.hist_container)

        hist_layout.addWidget(self.scroll_hist)
        right_panel.addWidget(history_frame)

        main_layout.addLayout(right_panel, stretch=3)

    def _init_timers(self):
        # Timer for updating playback seek slider & position
        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(200)  # 5 times a second
        self.playback_timer.timeout.connect(self._update_playback_ui)
        self.playback_timer.start()

    def _refresh_board_state(self):
        """Update button styles on the 90 grid based on called status."""
        self.song_catalog = {s["id"]: s for s in database.get_all_songs()}
        self.called_numbers = set(database.get_called_numbers(self.session_id))
        total_called = len(self.called_numbers)
        rem = TOTAL_NUMBERS - total_called

        self.lbl_stats.setText(f"Called: {total_called} / {TOTAL_NUMBERS}  (Remaining: {rem})")
        self.progress_bar.setValue(total_called)
        self.btn_draw.setEnabled(total_called < TOTAL_NUMBERS)

        # Update each button
        for num, btn in self.grid_buttons.items():
            song = self.song_catalog.get(num, {})
            title = song.get("title", f"Track #{num}")
            artist = song.get("artist", "")
            btn.setToolTip(f"#{num}: {title}\n{artist}")

            if num == self.current_song_id:
                # Active playing number
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {THEME['gold']};
                        color: {THEME['text_dark']};
                        border: 2px solid white;
                        border-radius: 6px;
                    }}
                """)
            elif num in self.called_numbers:
                # Called number
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {THEME['crimson']};
                        color: white;
                        border: 1px solid {THEME['crimson_hover']};
                        border-radius: 6px;
                    }}
                """)
            else:
                # Uncalled number
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {THEME['bg_subtle']};
                        color: {THEME['text_secondary']};
                        border: 1px solid {THEME['border']};
                        border-radius: 6px;
                    }}
                    QPushButton:hover {{
                        background-color: {THEME['bg_card_hover']};
                        color: {THEME['text_primary']};
                        border-color: {THEME['gold']};
                    }}
                """)

        self._refresh_history_feed()

    def _refresh_history_feed(self):
        # Clear existing items
        while self.hist_vbox.count() > 1:
            child = self.hist_vbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        history = database.get_called_history(self.session_id)
        for item in history[:20]:  # Top 20 recent calls
            chip = QFrame()
            chip.setStyleSheet(f"""
                QFrame {{
                    background-color: {THEME['bg_subtle']};
                    border: 1px solid {THEME['border']};
                    border-radius: 6px;
                    padding: 4px 8px;
                }}
            """)
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(6, 4, 6, 4)

            lbl_ord = QLabel(f"#{item['call_order']}")
            lbl_ord.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            lbl_ord.setStyleSheet(f"color: {THEME['gold']};")

            lbl_info = QLabel(f"<b>[{item['song_id']}]</b> {item['title']}")
            lbl_info.setFont(QFont("Arial", 9))
            lbl_info.setStyleSheet(f"color: {THEME['text_primary']};")

            btn_play_chip = QPushButton("▶")
            btn_play_chip.setFixedSize(24, 24)
            btn_play_chip.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_play_chip.setStyleSheet("background: transparent; border: none; font-size: 11px;")
            btn_play_chip.clicked.connect(lambda ch, sid=item['song_id']: self.play_song_by_id(sid))

            chip_layout.addWidget(lbl_ord)
            chip_layout.addWidget(lbl_info, stretch=1)
            chip_layout.addWidget(btn_play_chip)
            self.hist_vbox.insertWidget(self.hist_vbox.count() - 1, chip)

    def draw_random_number(self):
        """Pick an uncalled number uniformly at random."""
        uncalled = [n for n in range(1, 91) if n not in self.called_numbers]
        if not uncalled:
            QMessageBox.information(self, "Game Finished", "All 90 numbers have been called!")
            return

        chosen = random.choice(uncalled)
        self._execute_call(chosen)

    def on_number_clicked(self, number: int):
        """Host clicks a specific number on the board."""
        if number in self.called_numbers:
            # Already called: play song or re-focus
            self.play_song_by_id(number)
        else:
            # Confirm manual call
            reply = QMessageBox.question(
                self,
                "Manual Call",
                f"Do you want to manually call Song #{number}?\n{self.song_catalog.get(number, {}).get('title', '')}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._execute_call(number)

    def _execute_call(self, song_id: int):
        """Register the call, update UI spotlight, and trigger audio."""
        try:
            database.call_number(self.session_id, song_id)
            self.called_numbers.add(song_id)
            self.current_song_id = song_id
            
            # Spotlight info
            song = self.song_catalog.get(song_id, {})
            self.lbl_big_number.setText(f"{song_id:02d}")
            self.lbl_spotlight_song.setText(song.get("title", f"Track #{song_id}"))
            self.lbl_spotlight_artist.setText(song.get("artist", ""))

            self._refresh_board_state()
            self.call_made_signal.emit(song_id)

            if self.chk_autoplay.isChecked():
                self.play_song_by_id(song_id)
        except Exception as e:
            QMessageBox.warning(self, "Call Error", str(e))

    def play_song_by_id(self, song_id: int):
        """Trigger audio playback for a given song ID."""
        song = self.song_catalog.get(song_id, {})
        audio_path = song.get("audio_path", "")
        title = song.get("title", f"Track #{song_id}")
        
        self.lbl_now_playing.setText(f"🎵 #{song_id} - {title}")
        self.current_song_id = song_id
        self._refresh_board_state()

        if audio_path:
            success = self.audio_player.play_track(audio_path, start_pos=0.0)
            if not success:
                self.lbl_now_playing.setText(f"⚠️ Audio file error for #{song_id} ({audio_path})")
        else:
            self.lbl_now_playing.setText(f"⚠️ No audio file mapped for #{song_id} ({title})")

    def toggle_play_pause(self):
        self.audio_player.toggle_play_pause()
        self._update_playback_ui()

    def replay_current_song(self):
        self.audio_player.replay()

    def stop_audio(self):
        self.audio_player.stop()
        self._update_playback_ui()

    def change_volume(self, val: int):
        self.audio_player.set_volume(val)

    def _on_seek_pressed(self):
        self.is_scrubbing = True

    def _on_seek_released(self):
        self.is_scrubbing = False
        val = self.slider_seek.value()
        total = self.audio_player.total_duration
        if total > 0:
            target_sec = (val / 1000.0) * total
            self.audio_player.seek(target_sec)

    def _on_seek_value_changed(self, val: int):
        if self.is_scrubbing:
            total = self.audio_player.total_duration
            if total > 0:
                curr_sec = (val / 1000.0) * total
                self.lbl_time_curr.setText(self._format_time(curr_sec))

    def _update_playback_ui(self):
        """Update play/pause icon, scrubber position, and timestamps."""
        if self.audio_player.is_playing and not self.audio_player.is_paused:
            self.btn_play_pause.setText("⏸ Pause")
        else:
            self.btn_play_pause.setText("▶ Play")

        if not self.is_scrubbing:
            curr = self.audio_player.get_current_position()
            total = self.audio_player.total_duration

            self.lbl_time_curr.setText(self._format_time(curr))
            self.lbl_time_total.setText(self._format_time(total))

            if total > 0:
                slider_pos = int((curr / total) * 1000)
                self.slider_seek.blockSignals(True)
                self.slider_seek.setValue(min(1000, max(0, slider_pos)))
                self.slider_seek.blockSignals(False)

    def _format_time(self, seconds: float) -> str:
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins:02d}:{secs:02d}"

    def undo_call(self):
        """Revert the most recent call."""
        removed = database.undo_last_call(self.session_id)
        if removed:
            self.called_numbers.discard(removed)
            if self.current_song_id == removed:
                self.current_song_id = None
                self.audio_player.stop()
                self.lbl_big_number.setText("--")
                self.lbl_spotlight_song.setText("Last call undone")
                self.lbl_spotlight_artist.setText("")
                self.lbl_now_playing.setText("🎵 Ready")
            self._refresh_board_state()
        else:
            QMessageBox.information(self, "Undo", "No calls to undo in this session.")

    def confirm_reset_game(self):
        reply = QMessageBox.question(
            self,
            "Reset Game Session",
            "Are you sure you want to start a fresh game?\nAll current call records will be archived.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.audio_player.stop()
            self.session_id = database.reset_active_session()
            self.called_numbers.clear()
            self.current_song_id = None
            self.lbl_big_number.setText("--")
            self.lbl_spotlight_song.setText("New game started")
            self.lbl_spotlight_artist.setText("")
            self.lbl_now_playing.setText("🎵 Ready")
            self._refresh_board_state()
