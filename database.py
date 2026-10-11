"""
Musical Tambola - SQLite Persistence Engine
Handles offline persistence for songs, live gameplay session states,
ticket registry, and lucky draw audit logs.
"""
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from pathlib import Path
from config import DATABASE_PATH, DEFAULT_90_SONGS, SONGS_DIR

logger = logging.getLogger("tambola.database")


@contextmanager
def get_connection():
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initialize all SQLite tables if they do not exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Songs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT DEFAULT '',
                year TEXT DEFAULT '',
                audio_path TEXT DEFAULT '',
                duration REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Game Session Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                session_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 3. Called Numbers History
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS called_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                song_id INTEGER NOT NULL,
                call_order INTEGER NOT NULL,
                called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES game_sessions (session_id) ON DELETE CASCADE,
                FOREIGN KEY (song_id) REFERENCES songs (id) ON DELETE CASCADE
            )
        """)
        
        # 4. Tickets Master Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                batch_id TEXT DEFAULT 'default',
                mode TEXT NOT NULL, -- '1-strip' or '2-strip'
                player_name TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 5. Ticket Cells Table (Coordinates & Song Mapping)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticket_cells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                strip_index INTEGER NOT NULL, -- 1 or 2
                row_idx INTEGER NOT NULL,      -- 0 to 2
                col_idx INTEGER NOT NULL,      -- 0 to 8
                song_id INTEGER NOT NULL,      -- 1 to 90
                FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id) ON DELETE CASCADE,
                FOREIGN KEY (song_id) REFERENCES songs (id) ON DELETE CASCADE
            )
        """)
        
        # 6. Lucky Draw Audit Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lucky_draw_audit (
                round_id INTEGER PRIMARY KEY AUTOINCREMENT,
                prize_name TEXT NOT NULL,
                pool_type TEXT NOT NULL,
                winner_ids_json TEXT NOT NULL,
                drawn_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 7. Claim History
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claim_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                ticket_id TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                verdict TEXT NOT NULL, -- 'VALID' or 'BOGEY'
                claimed_by TEXT DEFAULT '',
                claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()


def seed_default_songs(force: bool = False) -> int:
    """Seeds the catalog with 90 default songs if the table is empty or forced."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM songs")
        row = cursor.fetchone()
        if row and row["count"] > 0 and not force:
            return 0
        
        for item in DEFAULT_90_SONGS:
            song_id, title, artist, year = item
            # Check if default audio file exists in assets/songs/
            audio_candidate = ""
            for ext in [".mp3", ".wav", ".ogg"]:
                candidate = SONGS_DIR / f"{song_id}{ext}"
                if candidate.exists():
                    audio_candidate = str(candidate)
                    break
            
            cursor.execute("""
                INSERT OR REPLACE INTO songs (id, title, artist, year, audio_path, duration)
                VALUES (?, ?, ?, ?, ?, 0.0)
            """, (song_id, title, artist, year, audio_candidate))
            
        conn.commit()
        return len(DEFAULT_90_SONGS)


def get_all_songs() -> List[Dict[str, Any]]:
    """Retrieve all 90 songs ordered by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM songs ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]


def get_song(song_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single song by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM songs WHERE id = ?", (song_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def upsert_song(song_id: int, title: str, artist: str = "", year: str = "", audio_path: str = "", duration: float = 0.0) -> None:
    """Insert or update a song."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO songs (id, title, artist, year, audio_path, duration, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                artist = excluded.artist,
                year = excluded.year,
                audio_path = CASE WHEN excluded.audio_path != '' THEN excluded.audio_path ELSE songs.audio_path END,
                duration = CASE WHEN excluded.duration > 0 THEN excluded.duration ELSE songs.duration END,
                updated_at = CURRENT_TIMESTAMP
        """, (song_id, title, artist, year, audio_path, duration))
        conn.commit()


def update_audio_path(song_id: int, audio_path: str, duration: float = 0.0) -> None:
    """Update audio file path and duration for a specific song ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE songs
            SET audio_path = ?, duration = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (audio_path, duration, song_id))
        conn.commit()


# Game Session & Live Calls Management
def get_or_create_active_session() -> str:
    """Get the active game session ID or create one if none exists."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT session_id FROM game_sessions WHERE status = 'active' ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row["session_id"]
        
        session_id = f"SESSION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cursor.execute("""
            INSERT INTO game_sessions (session_id, name, status)
            VALUES (?, ?, 'active')
        """, (session_id, f"Musical Tambola Live Game"))
        conn.commit()
        return session_id


def reset_active_session() -> str:
    """Closes old session and creates a fresh active session."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE game_sessions SET status = 'completed' WHERE status = 'active'")
        session_id = f"SESSION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cursor.execute("""
            INSERT INTO game_sessions (session_id, name, status)
            VALUES (?, ?, 'active')
        """, (session_id, f"Musical Tambola Live Game"))
        conn.commit()
        return session_id


def call_number(session_id: str, song_id: int) -> int:
    """Logs a called song/number in the current session. Returns new call order."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Verify not already called
        cursor.execute("SELECT COUNT(*) as count FROM called_numbers WHERE session_id = ? AND song_id = ?", (session_id, song_id))
        if cursor.fetchone()["count"] > 0:
            raise ValueError(f"Song #{song_id} has already been called in this session.")
        
        cursor.execute("SELECT COALESCE(MAX(call_order), 0) + 1 as next_order FROM called_numbers WHERE session_id = ?", (session_id,))
        next_order = cursor.fetchone()["next_order"]
        
        cursor.execute("""
            INSERT INTO called_numbers (session_id, song_id, call_order, called_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (session_id, song_id, next_order))
        conn.commit()
        return next_order


def undo_last_call(session_id: str) -> Optional[int]:
    """Reverts the most recent call in the session. Returns the removed song ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, song_id FROM called_numbers
            WHERE session_id = ?
            ORDER BY call_order DESC LIMIT 1
        """, (session_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        record_id = row["id"]
        removed_song = row["song_id"]
        cursor.execute("DELETE FROM called_numbers WHERE id = ?", (record_id,))
        conn.commit()
        return removed_song


def get_called_numbers(session_id: str) -> List[int]:
    """Returns sorted list of unique song IDs called so far."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT song_id FROM called_numbers
            WHERE session_id = ?
            ORDER BY song_id ASC
        """, (session_id,))
        return [row["song_id"] for row in cursor.fetchall()]


def get_called_history(session_id: str) -> List[Dict[str, Any]]:
    """Returns chronologically ordered list of calls with song metadata."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.call_order, c.song_id, s.title, s.artist, s.audio_path, c.called_at
            FROM called_numbers c
            JOIN songs s ON c.song_id = s.id
            WHERE c.session_id = ?
            ORDER BY c.call_order DESC
        """, (session_id,))
        return [dict(row) for row in cursor.fetchall()]


# Ticket Registry
def save_tickets(tickets: List[Dict[str, Any]], sync_json: bool = True) -> int:
    """Persist generated tickets into SQLite and sync with tickets.json."""
    with get_connection() as conn:
        cursor = conn.cursor()
        count = 0
        for t in tickets:
            ticket_id = str(t["ticket_id"])
            mode = t.get("mode", "1-strip")
            batch_id = t.get("batch_id", "batch_1")
            player = t.get("player_name", "")
            
            cursor.execute("""
                INSERT OR REPLACE INTO tickets (ticket_id, batch_id, mode, player_name, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (ticket_id, batch_id, mode, player))
            
            # Delete old cells for this ticket if any
            cursor.execute("DELETE FROM ticket_cells WHERE ticket_id = ?", (ticket_id,))
            
            for strip_idx, strip in enumerate(t.get("strips", []), start=1):
                # strip is a 3x9 matrix of ints (0 for empty, 1-90 for song)
                for r_idx, row in enumerate(strip):
                    for c_idx, song_id in enumerate(row):
                        if song_id and song_id > 0:
                            cursor.execute("""
                                INSERT INTO ticket_cells (ticket_id, strip_index, row_idx, col_idx, song_id)
                                VALUES (?, ?, ?, ?, ?)
                            """, (ticket_id, strip_idx, r_idx, c_idx, int(song_id)))
            count += 1
            
        conn.commit()

    if sync_json:
        export_tickets_to_json()
    return count


def get_all_tickets() -> List[Dict[str, Any]]:
    """Fetch all registered tickets with complete cell data."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets ORDER BY ticket_id ASC")
        ticket_rows = cursor.fetchall()
        
        results = []
        for trow in ticket_rows:
            tid = trow["ticket_id"]
            ticket_dict = dict(trow)
            
            # Build strips
            cursor.execute("""
                SELECT strip_index, row_idx, col_idx, song_id
                FROM ticket_cells
                WHERE ticket_id = ?
                ORDER BY strip_index, row_idx, col_idx
            """, (tid,))
            cells = cursor.fetchall()
            
            max_strip = 2 if ticket_dict["mode"] == "2-strip" else 1
            strips = [[[0 for _ in range(9)] for _ in range(3)] for _ in range(max_strip)]
            
            for cell in cells:
                s_idx = cell["strip_index"] - 1
                if 0 <= s_idx < max_strip:
                    strips[s_idx][cell["row_idx"]][cell["col_idx"]] = cell["song_id"]
            
            ticket_dict["strips"] = strips
            results.append(ticket_dict)
        return results


def get_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full ticket details by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
        trow = cursor.fetchone()
        if not trow:
            # Try stripped / zero-padded match
            cursor.execute("SELECT * FROM tickets WHERE ticket_id LIKE ?", (f"%{ticket_id}%",))
            trow = cursor.fetchone()
            if not trow:
                return None
        
        ticket_dict = dict(trow)
        tid = ticket_dict["ticket_id"]
        
        cursor.execute("""
            SELECT strip_index, row_idx, col_idx, song_id
            FROM ticket_cells
            WHERE ticket_id = ?
            ORDER BY strip_index, row_idx, col_idx
        """, (tid,))
        cells = cursor.fetchall()
        
        max_strip = 2 if ticket_dict["mode"] == "2-strip" else 1
        strips = [[[0 for _ in range(9)] for _ in range(3)] for _ in range(max_strip)]
        
        for cell in cells:
            s_idx = cell["strip_index"] - 1
            if 0 <= s_idx < max_strip:
                strips[s_idx][cell["row_idx"]][cell["col_idx"]] = cell["song_id"]
                
        ticket_dict["strips"] = strips
        return ticket_dict


def clear_all_tickets() -> None:
    """Clear all tickets from database and json."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ticket_cells")
        cursor.execute("DELETE FROM tickets")
        conn.commit()
    export_tickets_to_json()


def export_tickets_to_json() -> None:
    """Dump current tickets to tickets.json for fast external inspection and backup."""
    tickets = get_all_tickets()
    try:
        from config import TICKETS_JSON_PATH
        with open(TICKETS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to export tickets to JSON: {e}")


# Lucky Draw Audit Log
def add_lucky_draw_record(prize_name: str, pool_type: str, winner_ids: List[Any]) -> int:
    """Record a lucky draw round in audit log."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lucky_draw_audit (prize_name, pool_type, winner_ids_json, drawn_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (prize_name, pool_type, json.dumps(winner_ids)))
        conn.commit()
        return cursor.lastrowid


def get_lucky_draw_records() -> List[Dict[str, Any]]:
    """Get lucky draw history."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lucky_draw_audit ORDER BY round_id DESC")
        records = []
        for row in cursor.fetchall():
            rec = dict(row)
            try:
                rec["winner_ids"] = json.loads(rec["winner_ids_json"])
            except Exception:
                rec["winner_ids"] = []
            records.append(rec)
        return records


def clear_lucky_draw_records() -> None:
    """Clear lucky draw audit records."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lucky_draw_audit")
        conn.commit()
