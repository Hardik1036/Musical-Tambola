"""
Comprehensive Automated Test Suite for Musical Tambola
Validates database, asset parser, ticket generator constraints,
audio player, and PyQt6 GUI integration.
"""
import sys
import os
import unittest
from pathlib import Path

# Ensure paths
sys.path.insert(0, str(Path(__file__).parent))

import database
from modules.asset_manager import AssetManager
from modules.ticket_engine import TicketEngine
from modules.audio_player import AudioPlayer


class TestMusicalTambola(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()
        if not database.get_all_songs():
            database.seed_default_songs(force=False)

    def test_01_database_and_songs(self):
        songs = database.get_all_songs()
        self.assertEqual(len(songs), 90, "Should have exactly 90 songs in catalog")
        
        # Test session management
        sess_id = database.get_or_create_active_session()
        self.assertTrue(sess_id.startswith("SESSION_"))

        # Test call and undo
        initial_called = database.get_called_numbers(sess_id)
        order = database.call_number(sess_id, 42)
        self.assertIn(42, database.get_called_numbers(sess_id))
        
        undone = database.undo_last_call(sess_id)
        self.assertEqual(undone, 42)
        self.assertNotIn(42, database.get_called_numbers(sess_id))

    def test_02_ticket_constraints_1_strip(self):
        engine = TicketEngine()
        tickets = engine.generate_batch(count=10, mode="1-strip")
        self.assertEqual(len(tickets), 10)

        for t in tickets:
            strip = t["strips"][0]
            # Check 3 rows
            self.assertEqual(len(strip), 3)
            # Check 9 cols
            for row in strip:
                self.assertEqual(len(row), 9)
                # Exactly 5 items per row
                filled_in_row = sum(1 for c in row if c > 0)
                self.assertEqual(filled_in_row, 5, f"Row should have 5 items, got {filled_in_row}")

            # Check column ranges and ascending order
            for col_idx in range(9):
                col_nums = [strip[r][col_idx] for r in range(3) if strip[r][col_idx] > 0]
                self.assertTrue(1 <= len(col_nums) <= 3, f"Col {col_idx} count {len(col_nums)} out of bounds")
                # Ascending order
                self.assertEqual(col_nums, sorted(col_nums), f"Col {col_idx} not sorted: {col_nums}")

    def test_03_ticket_constraints_2_strip(self):
        engine = TicketEngine()
        tickets = engine.generate_batch(count=5, mode="2-strip")
        self.assertEqual(len(tickets), 5)

        for t in tickets:
            self.assertEqual(len(t["strips"]), 2)
            s1_songs = {c for r in t["strips"][0] for c in r if c > 0}
            s2_songs = {c for r in t["strips"][1] for c in r if c > 0}

            self.assertEqual(len(s1_songs), 15)
            self.assertEqual(len(s2_songs), 15)
            # Zero repetition between Strip 1 and Strip 2
            overlap = s1_songs.intersection(s2_songs)
            self.assertEqual(len(overlap), 0, f"Overlapping songs found in 2-strip ticket: {overlap}")

    def test_04_lucky_draw_audit(self):
        rec_id = database.add_lucky_draw_record("Hamper 1", "Registered Ticket IDs", ["Ticket #001", "Ticket #005"])
        self.assertGreater(rec_id, 0)
        records = database.get_lucky_draw_records()
        self.assertTrue(any(r["round_id"] == rec_id for r in records))

    def test_05_asset_parser_formats(self):
        mgr = AssetManager()
        
        # Test TXT parsing
        txt_path = Path("test_catalog.txt")
        txt_path.write_text("1. Chura Liya - Asha Bhosle\n2 - Tum Hi Ho - Arijit Singh\n", encoding="utf-8")
        parsed = mgr.parse_file(str(txt_path))
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["title"], "Chura Liya")
        self.assertEqual(parsed[1]["title"], "Tum Hi Ho")
        if txt_path.exists():
            txt_path.unlink()

        # Test CSV parsing
        csv_path = Path("test_catalog.csv")
        csv_path.write_text("ID,Title,Artist\n10,Senorita,Farhan Akhtar\n11,Galliyan,Ankit Tiwari\n", encoding="utf-8")
        parsed_csv = mgr.parse_file(str(csv_path))
        self.assertEqual(len(parsed_csv), 2)
        self.assertEqual(parsed_csv[0]["id"], 10)
        self.assertEqual(parsed_csv[0]["title"], "Senorita")
        if csv_path.exists():
            csv_path.unlink()

    def test_06_pyqt_ui_instantiation(self):
        from qt_compat import QApplication
        from main import MusicalTambolaApp

        # Run QApplication in offscreen mode
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)

        window = MusicalTambolaApp()
        self.assertEqual(window.tabs.count(), 5, "App should have 5 navigation tabs")
        window.close()

    def test_07_song_bank_and_columns(self):
        import song_bank
        self.assertEqual(len(song_bank.SONG_BANK), 90)
        # Verify 9 columns
        for sid in range(1, 91):
            col = song_bank.get_column_for_index(sid)
            self.assertTrue(0 <= col <= 8)
            start, end = song_bank.COLUMN_RANGES[col]
            self.assertTrue(start <= sid <= end)

    def test_08_housie_ticket_generator_dynamic(self):
        from generator.generate_housie_tickets import generate_housie_tickets
        # 1. Direct in-cell mode (zero overlap directly in template cells)
        out_direct = generate_housie_tickets(num_sheets=3, format_mode="2-strip", print_mode="direct_in_cell")
        self.assertTrue(Path(out_direct).is_file())
        content_direct = Path(out_direct).read_text(encoding="utf-8")
        self.assertIn("in-cell-grid", content_direct)

        # 2. Overlay card mode
        out_overlay = generate_housie_tickets(num_sheets=3, format_mode="2-strip", show_participant_slots=True, print_mode="overlay_box")
        self.assertTrue(Path(out_overlay).is_file())
        content_overlay = Path(out_overlay).read_text(encoding="utf-8")
        self.assertIn("Participant Name:", content_overlay)
        self.assertIn("SHEET #001", content_overlay)

    def test_09_custom_batch_archive_storage_and_loading(self):
        import json
        from config import TICKETS_ARCHIVE_DIR
        from generator.generate_housie_tickets import generate_housie_tickets, sanitize_batch_name

        # 1. Test sanitizer
        clean = sanitize_batch_name("New_Year_Eve @ 2026 / Batch#1")
        self.assertEqual(clean, "New_Year_Eve_2026_Batch_1")

        # 2. Test generation into tickets_archive
        out_html = generate_housie_tickets(
            num_sheets=2,
            format_mode="2-strip",
            batch_name="Test_Gala_2026"
        )
        self.assertTrue(Path(out_html).is_file())
        self.assertEqual(Path(out_html).name, "Test_Gala_2026.html")

        registry_path = TICKETS_ARCHIVE_DIR / "Test_Gala_2026_registry.json"
        self.assertTrue(registry_path.is_file(), "Registry JSON must exist in tickets_archive/")

        with open(registry_path, "r", encoding="utf-8") as rf:
            reg_data = json.load(rf)

        self.assertEqual(reg_data["batch_name"], "Test_Gala_2026")
        self.assertEqual(len(reg_data["tickets"]), 2)
        # Check 3x9 grid structure in registry
        for t in reg_data["tickets"]:
            self.assertIn("ticket_id", t)
            self.assertEqual(len(t["strips"]), 2)
            for strip in t["strips"]:
                self.assertEqual(len(strip), 3)
                for row in strip:
                    self.assertEqual(len(row), 9)


if __name__ == "__main__":
    unittest.main()


