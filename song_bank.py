"""
song_bank.py - 90 Indexed Songs Mapped Across 9 Columns
Provides universal song catalog, decade column mapping, and audio file resolution.
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Column decade boundaries: 9 columns (0 to 8)
COLUMN_RANGES = [
    (1, 9),    # Col 0: 1 to 9 (9 numbers)
    (10, 19),  # Col 1: 10 to 19 (10 numbers)
    (20, 29),  # Col 2: 20 to 29 (10 numbers)
    (30, 39),  # Col 3: 30 to 39 (10 numbers)
    (40, 49),  # Col 4: 40 to 49 (10 numbers)
    (50, 59),  # Col 5: 50 to 59 (10 numbers)
    (60, 69),  # Col 6: 60 to 69 (10 numbers)
    (70, 79),  # Col 7: 70 to 79 (10 numbers)
    (80, 90),  # Col 8: 80 to 90 (11 numbers)
]

# 90 Evergreen Indian and Bollywood Hit Songs
_DEFAULT_SONG_LIST = [
    (1, "Dum Maro Dum", "Hare Rama Hare Krishna", "1971"),
    (2, "Jai Ho", "Slumdog Millionaire", "2008"),
    (3, "Chaiyya Chaiyya", "Dil Se", "1998"),
    (4, "Tum Hi Ho", "Aashiqui 2", "2013"),
    (5, "Kal Ho Naa Ho", "Kal Ho Naa Ho", "2003"),
    (6, "Kabira", "Yeh Jawaani Hai Deewani", "2013"),
    (7, "Channa Mereya", "Ae Dil Hai Mushkil", "2016"),
    (8, "Pehla Nasha", "Jo Jeeta Wohi Sikandar", "1992"),
    (9, "Tujhe Dekha Toh", "DDLJ", "1995"),
    (10, "Senorita", "ZNMD", "2011"),
    (11, "Galliyan", "Ek Villain", "2014"),
    (12, "Raabta", "Agent Vinod", "2012"),
    (13, "Tere Bina", "Guru", "2007"),
    (14, "Maa Tujhe Salaam", "Vande Mataram", "1997"),
    (15, "Dil Chahta Hai", "Dil Chahta Hai", "2001"),
    (16, "Kun Faya Kun", "Rockstar", "2011"),
    (17, "Kajra Re", "Bunty Aur Babli", "2005"),
    (18, "Badtameez Dil", "Yeh Jawaani Hai Deewani", "2013"),
    (19, "Gerua", "Dilwale", "2015"),
    (20, "Ghungroo", "War", "2019"),
    (21, "Ae Mere Humsafar", "QSQT", "1988"),
    (22, "Lag Jaa Gale", "Woh Kaun Thi", "1964"),
    (23, "Pal Pal Dil Ke Paas", "Blackmail", "1973"),
    (24, "Mere Sapno Ki Rani", "Aradhana", "1969"),
    (25, "Roop Tera Mastana", "Aradhana", "1969"),
    (26, "Kabhi Kabhie Mere Dil Mein", "Kabhi Kabhie", "1976"),
    (27, "Yeh Dosti Hum Nahi", "Sholay", "1975"),
    (28, "Mehbooba Mehbooba", "Sholay", "1975"),
    (29, "Om Shanti Om", "Karz", "1980"),
    (30, "Ek Do Teen", "Tezaab", "1988"),
    (31, "Tip Tip Barsa Paani", "Mohra", "1994"),
    (32, "Chura Ke Dil Mera", "Main Khiladi Tu Anari", "1994"),
    (33, "Aankh Marey", "Simmba", "2018"),
    (34, "Lungi Dance", "Chennai Express", "2013"),
    (35, "Malhari", "Bajirao Mastani", "2015"),
    (36, "Gallan Goodiyaan", "Dil Dhadakne Do", "2015"),
    (37, "Zingaat", "Dhadak", "2018"),
    (38, "Kar Gayi Chull", "Kapoor & Sons", "2016"),
    (39, "Kala Chashma", "Baar Baar Dekho", "2016"),
    (40, "London Thumakda", "Queen", "2014"),
    (41, "Jeene Ke Hain Chaar Din", "Mujhse Shaadi Karogi", "2004"),
    (42, "Mauja Hi Mauja", "Jab We Met", "2007"),
    (43, "Nagada Sang Dhol", "Goliyon Ki Raasleela", "2013"),
    (44, "Dola Re Dola", "Devdas", "2002"),
    (45, "Bole Chudiyan", "K3G", "2001"),
    (46, "Say Shava Shava", "K3G", "2001"),
    (47, "Desi Girl", "Dostana", "2008"),
    (48, "Subah Hone Na De", "Desi Boyz", "2011"),
    (49, "Sooraj Dooba Hain", "Roy", "2015"),
    (50, "Balam Pichkari", "Yeh Jawaani Hai Deewani", "2013"),
    (51, "Gaddi Lambi", "Diljit Dosanjh", "2020"),
    (52, "Proper Patola", "Namaste England", "2018"),
    (53, "High Rated Gabru", "Nawabzaade", "2018"),
    (54, "Lahore", "Guru Randhawa", "2017"),
    (55, "Suit Suit", "Hindi Medium", "2017"),
    (56, "Ban Ja Rani", "Tumhari Sulu", "2017"),
    (57, "Nashe Si Chadh Gayi", "Befikre", "2016"),
    (58, "Dilbar", "Satyameva Jayate", "2018"),
    (59, "Garmi", "Street Dancer 3D", "2020"),
    (60, "Muqabla", "Street Dancer 3D", "2020"),
    (61, "Chammak Challo", "Ra.One", "2011"),
    (62, "Sheila Ki Jawani", "Tees Maar Khan", "2010"),
    (63, "Munni Badnaam Hui", "Dabangg", "2010"),
    (64, "Fevicol Se", "Dabangg 2", "2012"),
    (65, "Chikni Chameli", "Agneepath", "2012"),
    (66, "Ooh La La", "The Dirty Picture", "2011"),
    (67, "Gandi Baat", "R... Rajkumar", "2013"),
    (68, "Dhating Nach", "Phata Poster Nikhla Hero", "2013"),
    (69, "Hookah Bar", "Khiladi 786", "2012"),
    (70, "Party All Night", "Boss", "2013"),
    (71, "Sunny Sunny", "Yaariyan", "2014"),
    (72, "Char Botal Vodka", "Ragini MMS 2", "2014"),
    (73, "Baby Doll", "Ragini MMS 2", "2014"),
    (74, "Chittiyaan Kalaiyaan", "Roy", "2015"),
    (75, "Afreen Afreen", "Coke Studio", "2016"),
    (76, "Tajdar-e-Haram", "Coke Studio", "2015"),
    (77, "Pasoori", "Coke Studio", "2022"),
    (78, "Kesariya", "Brahmastra", "2022"),
    (79, "Apna Bana Le", "Bhediya", "2022"),
    (80, "Raataan Lambiyan", "Shershaah", "2021"),
    (81, "Ranjha", "Shershaah", "2021"),
    (82, "Maan Meri Jaan", "Champagne Talk", "2022"),
    (83, "Kahani Suno 2.0", "Kaifi Khalil", "2022"),
    (84, "Heeriye", "Jasleen Royal", "2023"),
    (85, "Chal Tere Ishq Mein", "Gadar 2", "2023"),
    (86, "Jhoome Jo Pathaan", "Pathaan", "2023"),
    (87, "Besharam Rang", "Pathaan", "2023"),
    (88, "Not Ramaiya Vastavaiya", "Jawan", "2023"),
    (89, "Chaleya", "Jawan", "2023"),
    (90, "Lutt Putt Gaya", "Dunki", "2023"),
]


def _determine_column(num: int) -> int:
    """Return column index (0-8) for a number 1-90."""
    if num < 1 or num > 90:
        raise ValueError(f"Song number {num} out of bounds (1-90).")
    if num <= 9:
        return 0
    if num >= 80:
        return 8
    return num // 10


# Initialize Song Bank Dictionary
SONG_BANK: Dict[int, Dict[str, Any]] = {}

for s_id, s_title, s_album, s_year in _DEFAULT_SONG_LIST:
    col = _determine_column(s_id)
    SONG_BANK[s_id] = {
        "id": s_id,
        "title": s_title,
        "artist": s_album,
        "year": s_year,
        "column": col,
        "column_range": COLUMN_RANGES[col]
    }


def sync_with_database() -> None:
    """
    Sync in-memory SONG_BANK with songs from SQLite Audio Catalog (tambola.db).
    If database contains customized catalog items, they override default songs
    while maintaining decade column mappings and audio paths.
    """
    try:
        import database
        db_songs = database.get_all_songs()
        if db_songs:
            for s in db_songs:
                s_id = s.get("id")
                if s_id and 1 <= s_id <= 90:
                    col = _determine_column(s_id)
                    title = (s.get("title") or "").strip()
                    if not title:
                        title = SONG_BANK.get(s_id, {}).get("title", f"Track #{s_id}")
                    artist = (s.get("artist") or "").strip()
                    year = str(s.get("year") or "").strip()
                    audio_path = s.get("audio_path") or ""
                    SONG_BANK[s_id] = {
                        "id": s_id,
                        "title": title,
                        "artist": artist,
                        "year": year,
                        "column": col,
                        "column_range": COLUMN_RANGES[col],
                        "audio_path": audio_path,
                        "duration": s.get("duration", 0.0)
                    }
    except Exception:
        pass


# Immediately synchronize with database on import
sync_with_database()


def get_column_for_index(index: int) -> int:
    """Return the 0-8 decade column index for a song number."""
    return _determine_column(index)


def get_song(index: int, refresh: bool = False) -> Optional[Dict[str, Any]]:
    """Retrieve song metadata dict by index (1-90)."""
    if refresh:
        sync_with_database()
    return SONG_BANK.get(index)


def get_song_title(index: int) -> str:
    """Retrieve song title by index, with fallback."""
    song = SONG_BANK.get(index)
    return song["title"] if song and song.get("title") else f"Track #{index}"


def get_all_songs(refresh: bool = False) -> List[Dict[str, Any]]:
    """Return all 90 songs sorted by index."""
    if refresh:
        sync_with_database()
    return [SONG_BANK[i] for i in range(1, 91) if i in SONG_BANK]


def get_songs_for_column(col_idx: int) -> List[Dict[str, Any]]:
    """Retrieve all songs that fall into a specific decade column (0 to 8)."""
    if col_idx < 0 or col_idx > 8:
        return []
    start, end = COLUMN_RANGES[col_idx]
    return [SONG_BANK[i] for i in range(start, end + 1) if i in SONG_BANK]


def find_audio_file(song_id: Any, base_dir: Optional[Path] = None) -> Optional[str]:
    """
    Search for audio file for song_id (handles int 1, '1', '01').
    Checks:
    - audio_config.json custom folder and mapped file_path
    - Prefix scanning in custom folder (e.g. '1. Khaike Paan Banaras Wala.mp3', '01 - ...')
    - songs/ and assets/songs/ for 1.mp3, 01.mp3, track1.mp3, etc.
    Returns absolute path string if found, else None.
    """
    try:
        s_id = int(str(song_id).strip().lstrip("0") or "0")
    except Exception:
        s_id = 1

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    exts = [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"]

    # 1. Check audio_config.json if present
    cfg_file = base_dir / "audio_config.json"
    if cfg_file.exists():
        try:
            import json
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            cues = cfg.get("song_cues", {})
            # Check both "1" and "01"
            for k in [str(s_id), f"{s_id:02d}"]:
                cue_path = cues.get(k, {}).get("file_path")
                if cue_path and Path(cue_path).exists():
                    return str(Path(cue_path).resolve())

            # Check custom audio folder
            custom_folder = cfg.get("audio_folder_path")
            if custom_folder and Path(custom_folder).is_dir():
                cf_path = Path(custom_folder)

                # Exact pattern match
                pats = [str(s_id), f"{s_id:02d}", f"track{s_id}", f"track_{s_id}", f"track {s_id}"]
                for p in pats:
                    for ext in exts:
                        fp = cf_path / f"{p}{ext}"
                        if fp.exists():
                            return str(fp.resolve())

                # Scan folder for files starting with song number (e.g. '1. Khaike Paan Banaras Wala.mp3')
                pattern = re.compile(rf'^(?:track[_\s-]*)?0*{s_id}[\s\._\-]', re.IGNORECASE)
                for entry in cf_path.iterdir():
                    if entry.is_file() and entry.suffix.lower() in exts:
                        if pattern.match(entry.stem) or entry.stem == str(s_id) or entry.stem == f"{s_id:02d}":
                            return str(entry.resolve())
        except Exception:
            pass

    # 2. Check candidate local directories
    candidate_dirs = [
        base_dir / "songs",
        base_dir / "assets" / "songs",
        base_dir / "assets",
    ]
    pattern = re.compile(rf'^(?:track[_\s-]*)?0*{s_id}[\s\._\-]', re.IGNORECASE)

    for d in candidate_dirs:
        if not d.exists() or not d.is_dir():
            continue
        # Direct pattern match
        pats = [str(s_id), f"{s_id:02d}", f"track{s_id}", f"track_{s_id}"]
        for p in pats:
            for ext in exts:
                fp = d / f"{p}{ext}"
                if fp.exists():
                    return str(fp.resolve())
        # Prefix match
        for entry in d.iterdir():
            if entry.is_file() and entry.suffix.lower() in exts:
                if pattern.match(entry.stem) or entry.stem == str(s_id) or entry.stem == f"{s_id:02d}":
                    return str(entry.resolve())

    return None


