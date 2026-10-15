"""
generate_housie_tickets.py - Dynamic Housie / Tambola Ticket Generation Engine
Generates 1-strip and 2-strip landscape A4 HTML tickets with dynamic background template overlay,
participant slot masking, and persistent SQLite & tickets.json registration.
"""
import os
import sys
import base64
import random
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter

# Ensure root workspace is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import song_bank
import database

# Constants
COLUMN_RANGES = song_bank.COLUMN_RANGES
STRIP_ROWS = 3
STRIP_COLS = 9
NUMBERS_PER_ROW = 5
NUMBERS_PER_STRIP = 15


class HousieTicketGenerator:
    """Algorithmic Housie Ticket Generator with mathematical constraint balancing."""

    def __init__(self):
        self.frequencies = Counter()

    def _generate_valid_mask(self) -> List[List[int]]:
        """Generate a valid 3x9 grid binary mask."""
        while True:
            # 1 in each of 9 columns, 6 extra ones distributed to columns with count < 3
            col_counts = [1] * STRIP_COLS
            rem = NUMBERS_PER_STRIP - STRIP_COLS
            avail_cols = list(range(STRIP_COLS))
            random.shuffle(avail_cols)

            for _ in range(rem):
                valid = [c for c in avail_cols if col_counts[c] < 3]
                if not valid:
                    break
                c = random.choice(valid)
                col_counts[c] += 1

            if sum(col_counts) != 15:
                continue

            mask = [[0] * STRIP_COLS for _ in range(STRIP_ROWS)]
            row_counts = [0] * STRIP_ROWS
            success = True

            cols_sorted = sorted(range(STRIP_COLS), key=lambda c: col_counts[c], reverse=True)
            for col in cols_sorted:
                needed = col_counts[col]
                avail_rows = [r for r in range(STRIP_ROWS) if row_counts[r] < 5]
                if len(avail_rows) < needed:
                    success = False
                    break
                avail_rows.sort(key=lambda r: row_counts[r])
                chosen = avail_rows[:needed]
                for r in chosen:
                    mask[r][col] = 1
                    row_counts[r] += 1

            if success and row_counts == [5, 5, 5]:
                return mask

    def generate_single_strip(self, exclude_songs: Optional[set] = None) -> List[List[int]]:
        """Generate a single 3x9 strip of 15 numbers."""
        if exclude_songs is None:
            exclude_songs = set()

        mask = self._generate_valid_mask()
        strip = [[0] * STRIP_COLS for _ in range(STRIP_ROWS)]

        for col_idx in range(STRIP_COLS):
            start_num, end_num = COLUMN_RANGES[col_idx]
            needed_in_col = sum(mask[r][col_idx] for r in range(STRIP_ROWS))
            if needed_in_col == 0:
                continue

            available = [n for n in range(start_num, end_num + 1) if n not in exclude_songs]
            if len(available) < needed_in_col:
                # If exhausted due to excludes, fallback to entire range
                available = list(range(start_num, end_num + 1))

            # Frequency balancing: prefer songs used least frequently
            available.sort(key=lambda n: self.frequencies[n] + random.random() * 0.4)
            chosen = sorted(available[:needed_in_col])

            row_indices = [r for r in range(STRIP_ROWS) if mask[r][col_idx] == 1]
            for r, song_id in zip(row_indices, chosen):
                strip[r][col_idx] = song_id
                self.frequencies[song_id] += 1

        return strip

    def generate_batch(self, count: int = 100, mode: str = "2-strip", start_id: int = 1) -> List[Dict[str, Any]]:
        """
        Generate a batch of tickets.
        In 2-strip mode: 2 paired strips per ticket (30 unique songs total per sheet, zero overlap).
        In 1-strip mode: 1 strip per ticket (15 songs).
        """
        tickets = []
        for i in range(count):
            t_id = f"{start_id + i:03d}"
            if mode == "1-strip":
                s1 = self.generate_single_strip()
                strips = [s1]
            else:  # 2-strip
                s1 = self.generate_single_strip()
                s1_used = {c for r in s1 for c in r if c > 0}
                s2 = self.generate_single_strip(exclude_songs=s1_used)
                strips = [s1, s2]

            tickets.append({
                "ticket_id": t_id,
                "mode": mode,
                "batch_id": f"batch_{count}_{mode}",
                "strips": strips
            })

        return tickets


def image_to_base64_uri(image_path: Optional[str]) -> str:
    """Read an image file and return its data URI string."""
    if not image_path:
        return ""
    p = Path(image_path)
    if not p.is_file():
        return ""
    ext = p.suffix.lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    try:
        with open(p, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/{ext};base64,{encoded}"
    except Exception as e:
        print(f"Warning: Could not encode template image {image_path}: {e}")
        return ""


import re
from datetime import datetime
from config import TICKETS_ARCHIVE_DIR
def sanitize_batch_name(name: Optional[str]) -> str:
    """Sanitize custom batch/event name to prevent invalid characters."""
    if not name or not name.strip():
        return datetime.now().strftime("musical_housie_tickets_%Y%m%d")
    clean = re.sub(r'[^a-zA-Z0-9_\-]+', '_', name.strip()).strip('_')
    return clean if clean else datetime.now().strftime("musical_housie_tickets_%Y%m%d")


def resolve_unique_batch_name(name: Optional[str], archive_dir: Optional[Path] = None) -> str:
    """
    Ensure batch name is sanitized and uniquely non-colliding.
    Prevents overwriting existing HTML batches or JSON registries.
    """
    if archive_dir is None:
        archive_dir = TICKETS_ARCHIVE_DIR
    base = sanitize_batch_name(name)
    target_html = archive_dir / f"{base}.html"
    target_json = archive_dir / f"{base}_registry.json"
    if not target_html.exists() and not target_json.exists():
        return base

    counter = 2
    while True:
        candidate = f"{base}_{counter:02d}"
        if not (archive_dir / f"{candidate}.html").exists() and not (archive_dir / f"{candidate}_registry.json").exists():
            return candidate
        counter += 1


def generate_housie_tickets(
    num_sheets: int = 100,
    format_mode: str = "2-strip",
    template_path: Optional[str] = None,
    show_participant_slots: bool = True,
    output_html_path: Optional[str] = None,
    batch_name: Optional[str] = None,
    save_to_database: bool = True,
    preset_id: Optional[str] = None,
    calibration: Optional[Dict[str, Any]] = None,
    participants_list: Optional[List[Dict[str, str]]] = None,
    print_mode: Optional[str] = None,
    show_song_number: bool = False
) -> str:
    """
    Core function to generate Housie tickets and export to an interactive,
    printable HTML sheet.
    Supports pixel-perfect Direct In-Cell printing into pre-designed template cells,
    customizable coordinate calibration, and personalized participant name printing.
    Strictly non-destructive: auto-resolves collisions in tickets_archive/.
    """
    import template_config

    archive_dir = TICKETS_ARCHIVE_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)
    clean_batch_name = resolve_unique_batch_name(batch_name, archive_dir)

    if template_path is None or not Path(template_path).is_file():
        # Check standard default locations with Garba Night priority
        candidates = [
            BASE_DIR / "assets" / "branding" / "Garba_Night_Musical_Housie_Template.png",
            BASE_DIR / "assets" / "branding" / "uploaded_template_664.png",
            BASE_DIR / "generator" / "ticket_template.png",
            BASE_DIR / "assets" / "branding" / "Festive_Musical_Housie_Template.png",
            BASE_DIR / "Festive Musical Housie Ticket Templates.png",
        ]
        for c in candidates:
            if c.is_file():
                template_path = str(c)
                break

    bg_data_uri = image_to_base64_uri(template_path)

    # Resolve calibration configuration
    if calibration is None:
        if preset_id:
            calibration = template_config.get_template_config(preset_id)
        else:
            t_str = str(template_path).lower() if template_path else ""
            if "festive" in t_str and "garba" not in t_str:
                calibration = template_config.get_template_config("festive_gold")
            else:
                calibration = template_config.get_template_config("garba_night")
    else:
        # Merge with defaults
        base_def = template_config.get_template_config("garba_night")
        base_def.update(calibration)
        calibration = base_def

    effective_print_mode = print_mode or calibration.get("print_mode", "direct_in_cell")
    effective_show_song_number = calibration.get("show_song_number", show_song_number) if calibration else show_song_number

    # 1. Generate tickets
    generator = HousieTicketGenerator()
    tickets = generator.generate_batch(count=num_sheets, mode=format_mode)

    # 2. Persist to SQLite & JSON
    if save_to_database:
        try:
            database.init_db()
            database.save_tickets(tickets, sync_json=True)
        except Exception as e:
            print(f"Warning: Database save encountered an issue: {e}")

    # 3. Enrich ticket numbers with metadata from Audio Catalog (SQLite DB)
    song_bank.sync_with_database()
    db_catalog: Dict[int, Dict[str, Any]] = {}
    try:
        db_songs = database.get_all_songs()
        if db_songs:
            db_catalog = {s["id"]: s for s in db_songs}
    except Exception as e:
        print(f"Warning: Could not query database audio catalog: {e}")

    enriched_tickets = []
    for t in tickets:
        enriched_strips = []
        for strip in t["strips"]:
            enriched_row_list = []
            for row in strip:
                enriched_row = []
                for sid in row:
                    if sid > 0:
                        s_meta = db_catalog.get(sid) or song_bank.get_song(sid)
                        title = ""
                        artist = ""
                        if isinstance(s_meta, dict):
                            title = (s_meta.get("title") or "").strip()
                            artist = (s_meta.get("artist") or "").strip()
                        elif s_meta is not None:
                            title = getattr(s_meta, "title", "")
                            artist = getattr(s_meta, "artist", "")
                        
                        if not title:
                            title = f"Track #{sid}"
                        
                        enriched_row.append({
                            "id": sid,
                            "title": title,
                            "artist": artist
                        })
                    else:
                        enriched_row.append({"id": 0, "title": "", "artist": ""})
                enriched_row_list.append(enriched_row)
            enriched_strips.append(enriched_row_list)

        enriched_tickets.append({
            "ticket_id": t["ticket_id"],
            "mode": t["mode"],
            "strips": enriched_strips
        })

    # 4. Generate HTML content
    is_2_strip = (format_mode == "2-strip")
    orientation = "landscape" if is_2_strip else "portrait"
    page_w_mm = 297 if is_2_strip else 210
    page_h_mm = 210 if is_2_strip else 297

    per_page = 1 if is_2_strip else 2
    page_batches = [enriched_tickets[i:i + per_page] for i in range(0, len(enriched_tickets), per_page)]

    s1 = calibration.get("strip_1", {"top_pct": 14.45, "left_pct": 2.0, "width_pct": 96.0, "height_pct": 28.07})
    s2 = calibration.get("strip_2", {"top_pct": 60.49, "left_pct": 2.0, "width_pct": 96.0, "height_pct": 28.18})
    f_num = calibration.get("font_number", {"size_pt": 16, "weight": 900, "color": "#800020"})
    def_title_sz = 17.0 if not effective_show_song_number else 9.5
    def_title_wt = 800 if not effective_show_song_number else 700
    raw_f_title = calibration.get("font_title", {})
    title_sz = raw_f_title.get("size_pt", def_title_sz)
    if not effective_show_song_number and title_sz < 14:
        title_sz = 17.0
    f_title = {
        "size_pt": title_sz,
        "weight": raw_f_title.get("weight", def_title_wt),
        "color": raw_f_title.get("color", "#1e293b")
    }
    badge_1_cfg = calibration.get("badge_1", {"enabled": True, "top_pct": 5.6, "left_pct": 7.1, "width_pct": 13.0, "height_pct": 4.8, "color": "#ffffff", "bg_color": "#800020", "format": "टिकट क्रमांक : {ticket_id}"})
    badge_2_cfg = calibration.get("badge_2", {"enabled": True, "top_pct": 51.9, "left_pct": 7.1, "width_pct": 13.0, "height_pct": 4.8, "color": "#ffffff", "bg_color": "#800020", "format": "टिकट क्रमांक : {ticket_id}"})
    part_name_cfg = calibration.get("participant_name", {"enabled": True, "top_pct": 91.5, "left_pct": 20.0, "width_pct": 28.0, "font_size_pt": 11, "color": "#800020"})
    part_mob_cfg = calibration.get("participant_mobile", {"enabled": True, "top_pct": 91.5, "left_pct": 63.0, "width_pct": 26.0, "font_size_pt": 11, "color": "#800020"})

    bg_css = f"background-image: url('{bg_data_uri}'); background-size: 100% 100%; background-position: center; background-repeat: no-repeat;" if bg_data_uri else "background: #0f172a;"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Musical Tambola - Printable Housie Tickets ({num_sheets} Sheets)</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;700;800;900&family=Inter:wght@400;600;700;800&family=Noto+Sans+Devanagari:wght@600;700;800&display=swap');
    
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: 'Inter', sans-serif;
      background: #090d16;
      color: #0f172a;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}

    .no-print-toolbar {{
      position: sticky;
      top: 0;
      z-index: 9999;
      background: rgba(15, 23, 42, 0.95);
      backdrop-filter: blur(8px);
      border-bottom: 2px solid #f59e0b;
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: white;
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }}

    .toolbar-title {{
      font-family: 'Outfit', sans-serif;
      font-weight: 800;
      font-size: 16px;
      color: #fef08a;
      letter-spacing: 0.5px;
    }}

    .btn-print {{
      background: linear-gradient(135deg, #e11d48, #be123c);
      color: white;
      border: 1px solid #f43f5e;
      padding: 8px 20px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 2px 10px rgba(225, 29, 72, 0.4);
      transition: all 0.2s ease;
    }}

    .btn-print:hover {{
      transform: translateY(-1px);
      background: linear-gradient(135deg, #f43f5e, #e11d48);
    }}

    /* Print Setup */
    @page {{
      size: A4 {orientation};
      margin: 0;
    }}

    @media print {{
      .no-print-toolbar {{
        display: none !important;
      }}
      body {{
        background: transparent;
      }}
      .sheet-page {{
        margin: 0 !important;
        box-shadow: none !important;
        page-break-after: always;
        break-after: page;
      }}
    }}

    .sheet-page {{
      width: {page_w_mm}mm;
      height: {page_h_mm}mm;
      margin: 8mm auto;
      position: relative;
      {bg_css}
      box-shadow: 0 10px 30px rgba(0,0,0,0.4);
      overflow: hidden;
    }}

    /* DIRECT IN-CELL GRID CSS (No opaque white boxes or overlapping tables) */
    .in-cell-grid {{
      position: absolute;
      display: grid;
      grid-template-columns: repeat(9, 1fr);
      grid-template-rows: repeat(3, 1fr);
      box-sizing: border-box;
      pointer-events: none;
    }}

    .cell-direct-blank {{
      background: transparent;
    }}

    .cell-direct-song {{
      background: transparent;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 2px 4px;
      overflow: hidden;
      box-sizing: border-box;
    }}

    .song-num-direct {{
      font-family: 'Outfit', sans-serif;
      font-weight: {f_num.get('weight', 900)};
      font-size: {f_num.get('size_pt', 16)}pt;
      color: {f_num.get('color', '#800020')};
      line-height: 1.05;
      margin-bottom: 2px;
    }}

    .song-title-direct {{
      font-family: 'Noto Sans Devanagari', 'Mukta', 'Inter', -apple-system, sans-serif;
      font-weight: {f_title['weight']};
      font-size: {f_title['size_pt']}pt;
      color: {f_title['color']};
      line-height: 1.25;
      max-width: 96%;
      word-break: break-word;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .direct-badge {{
      position: absolute;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'Outfit', 'Inter', sans-serif;
      font-weight: 800;
      border-radius: 6px;
      letter-spacing: 0.5px;
      white-space: nowrap;
    }}

    .direct-participant {{
      position: absolute;
      font-family: 'Inter', sans-serif;
      font-weight: 800;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    /* OVERLAY BOX CARD MODE (Fallback when no pre-drawn grid exists) */
    .sheet-page.overlay-card-mode {{
      padding: 8mm 10mm;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .ticket-wrapper {{ width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }}
    .ticket-header {{ display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.88); border: 1.5px solid #f59e0b; border-radius: 8px; padding: 6px 14px; }}
    .ticket-title {{ font-family: 'Outfit', sans-serif; font-size: 16px; font-weight: 800; color: #fef08a; }}
    .ticket-badge {{ background: #be123c; color: #fff; padding: 3px 12px; border-radius: 14px; font-weight: 800; font-size: 13px; }}
    .strips-container {{ display: flex; flex-direction: column; gap: 12px; margin: 8px 0; flex: 1; justify-content: space-around; }}
    .strip-box {{ background: rgba(255, 255, 255, 0.94); border: 2px solid #be123c; border-radius: 8px; overflow: hidden; }}
    .strip-header {{ background: linear-gradient(135deg, #881337, #be123c); color: #fff; padding: 3px 10px; font-size: 10px; font-weight: 700; display: flex; justify-content: space-between; }}
    .housie-table {{ width: 100%; border-collapse: collapse; table-layout: fixed; background: #fff; }}
    .housie-table td {{ width: 11.11%; height: 44px; border: 1px solid #94a3b8; text-align: center; vertical-align: middle; padding: 2px; }}
    .cell-empty {{ background-color: #f1f5f9; }}
    .cell-song {{ background-color: #ffffff; }}
    .song-number {{ font-family: 'Outfit', sans-serif; font-size: 14px; font-weight: 900; color: #be123c; line-height: 1; margin-bottom: 2px; }}
    .song-name {{ font-size: 8.5px; font-weight: 600; color: #0f172a; line-height: 1.1; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
    .participant-slots {{ display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.88); border: 1.5px solid #f59e0b; border-radius: 8px; padding: 6px 16px; color: white; font-size: 11px; }}
    .hide-top-slots {{ display: none !important; }}
  </style>
</head>
<body>

  <!-- Screen Toolbar -->
  <div class="no-print-toolbar">
    <div class="toolbar-title">
      🎶 MUSICAL TAMBOLA &bull; {num_sheets} {format_mode.upper()} SHEETS READY &bull; {effective_print_mode.upper().replace('_', ' ')}
    </div>
    <div style="display: flex; align-items: center; gap: 14px;">
      <div style="display: flex; align-items: center; background: rgba(30, 41, 59, 0.95); border: 1.5px solid #f59e0b; border-radius: 6px; padding: 4px 12px; gap: 8px;">
        <span style="font-size: 12px; font-weight: 800; color: #fef08a; letter-spacing: 0.3px;">🔤 Font Size:</span>
        <button type="button" onclick="adjustFontSize(-1)" style="background: #1e293b; color: white; border: 1px solid #64748b; border-radius: 4px; width: 26px; height: 26px; font-weight: 800; font-size: 15px; cursor: pointer; display: flex; align-items: center; justify-content: center; line-height: 1;" title="Decrease Font Size">-</button>
        <input type="range" id="toolbar-font-slider" min="10" max="28" step="0.5" value="{f_title['size_pt']}" oninput="setFontSizeDirect(this.value)" style="width: 85px; accent-color: #f59e0b; cursor: pointer;">
        <button type="button" onclick="adjustFontSize(1)" style="background: #1e293b; color: white; border: 1px solid #64748b; border-radius: 4px; width: 26px; height: 26px; font-weight: 800; font-size: 15px; cursor: pointer; display: flex; align-items: center; justify-content: center; line-height: 1;" title="Increase Font Size">+</button>
        <span id="current-font-size-label" style="font-size: 13px; font-weight: 800; min-width: 44px; text-align: center; color: #38bdf8;">{f_title['size_pt']}pt</span>
        <div style="display: flex; gap: 4px; margin-left: 4px; border-left: 1px solid #475569; padding-left: 8px;">
          <button type="button" onclick="setFontSizeDirect(14)" style="background: #0f172a; color: #cbd5e1; border: 1px solid #475569; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 700; cursor: pointer;">14pt</button>
          <button type="button" onclick="setFontSizeDirect(17)" style="background: #0f172a; color: #fef08a; border: 1px solid #f59e0b; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 700; cursor: pointer;">17pt</button>
          <button type="button" onclick="setFontSizeDirect(20)" style="background: #0f172a; color: #cbd5e1; border: 1px solid #475569; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 700; cursor: pointer;">20pt</button>
        </div>
      </div>
      <button class="btn-print" onclick="window.print()">🖨️ Print / Save as PDF</button>
    </div>
  </div>
"""

    sheet_counter = 0
    for page_idx, batch in enumerate(page_batches):
        for t in batch:
            sheet_counter += 1
            tid_num = int(t['ticket_id']) if str(t['ticket_id']).isdigit() else sheet_counter

            if effective_print_mode == "direct_in_cell":
                # Pixel-perfect Direct In-Cell Grid aligned with template
                html += f"""
  <div class="sheet-page">
"""
                # Strip 1 (3x9 grid)
                if len(t["strips"]) > 0:
                    strip1 = t["strips"][0]
                    html += f"""
    <!-- Strip 1 Direct In-Cell Grid -->
    <div class="in-cell-grid" style="top: {s1['top_pct']}%; left: {s1['left_pct']}%; width: {s1['width_pct']}%; height: {s1['height_pct']}%;">
"""
                    for row in strip1:
                        for cell in row:
                            if cell["id"] > 0:
                                num_html = f"        <div class=\"song-num-direct\">{cell['id']}</div>\n" if effective_show_song_number else ""
                                html += f"""      <div class="cell-direct-song">
{num_html}        <div class="song-title-direct">{cell['title']}</div>
      </div>\n"""
                            else:
                                html += '      <div class="cell-direct-blank"></div>\n'
                    html += "    </div>\n"

                # Strip 2 (3x9 grid)
                if len(t["strips"]) > 1:
                    strip2 = t["strips"][1]
                    html += f"""
    <!-- Strip 2 Direct In-Cell Grid -->
    <div class="in-cell-grid" style="top: {s2['top_pct']}%; left: {s2['left_pct']}%; width: {s2['width_pct']}%; height: {s2['height_pct']}%;">
"""
                    for row in strip2:
                        for cell in row:
                            if cell["id"] > 0:
                                num_html = f"        <div class=\"song-num-direct\">{cell['id']}</div>\n" if effective_show_song_number else ""
                                html += f"""      <div class="cell-direct-song">
{num_html}        <div class="song-title-direct">{cell['title']}</div>
      </div>\n"""
                            else:
                                html += '      <div class="cell-direct-blank"></div>\n'
                    html += "    </div>\n"

                # Dynamic Ticket Badges (Overlaying badge coordinates)
                if badge_1_cfg.get("enabled", True):
                    b1_text = badge_1_cfg.get("format", "टिकट क्रमांक : {ticket_id}").format(ticket_id=f"{(tid_num * 2 - 1):03d}" if is_2_strip else f"{tid_num:03d}")
                    html += f"""    <div class="direct-badge" style="top: {badge_1_cfg['top_pct']}%; left: {badge_1_cfg['left_pct']}%; width: {badge_1_cfg['width_pct']}%; height: {badge_1_cfg['height_pct']}%; background: {badge_1_cfg.get('bg_color', '#800020')}; color: {badge_1_cfg.get('color', '#ffffff')}; font-size: 11pt;">
      {b1_text}
    </div>\n"""

                if is_2_strip and badge_2_cfg.get("enabled", True):
                    b2_text = badge_2_cfg.get("format", "टिकट क्रमांक : {ticket_id}").format(ticket_id=f"{(tid_num * 2):03d}")
                    html += f"""    <div class="direct-badge" style="top: {badge_2_cfg['top_pct']}%; left: {badge_2_cfg['left_pct']}%; width: {badge_2_cfg['width_pct']}%; height: {badge_2_cfg['height_pct']}%; background: {badge_2_cfg.get('bg_color', '#800020')}; color: {badge_2_cfg.get('color', '#ffffff')}; font-size: 11pt;">
      {b2_text}
    </div>\n"""

                # Participant Name & Mobile (if provided)
                if participants_list and (sheet_counter - 1) < len(participants_list):
                    p_info = participants_list[sheet_counter - 1]
                    p_name = p_info.get("name", "")
                    p_mob = p_info.get("mobile", "")
                    if p_name and part_name_cfg.get("enabled", True):
                        html += f"""    <div class="direct-participant" style="top: {part_name_cfg['top_pct']}%; left: {part_name_cfg['left_pct']}%; width: {part_name_cfg['width_pct']}%; font-size: {part_name_cfg.get('font_size_pt', 11)}pt; color: {part_name_cfg.get('color', '#800020')};">
      {p_name}
    </div>\n"""
                    if p_mob and part_mob_cfg.get("enabled", True):
                        html += f"""    <div class="direct-participant" style="top: {part_mob_cfg['top_pct']}%; left: {part_mob_cfg['left_pct']}%; width: {part_mob_cfg['width_pct']}%; font-size: {part_mob_cfg.get('font_size_pt', 11)}pt; color: {part_mob_cfg.get('color', '#800020')};">
      {p_mob}
    </div>\n"""

                html += "  </div>\n"

            else:
                # Fallback: Overlay Card Box Mode
                html += f"""
  <div class="sheet-page overlay-card-mode">
    <div class="ticket-wrapper">
      <div class="ticket-header">
        <div class="ticket-title">🎶 MUSICAL TAMBOLA NIGHT</div>
        <div class="ticket-badge">SHEET #{t['ticket_id']}</div>
      </div>
      <div class="strips-container">
"""
                for s_idx, strip in enumerate(t["strips"], start=1):
                    strip_title = f"STRIP {s_idx} &bull; 15 SONGS TOTAL (5 / ROW)"
                    html += f"""        <div class="strip-box">
          <div class="strip-header">
            <span>{strip_title}</span>
            <span>TICKET #{t['ticket_id']}</span>
          </div>
          <table class="housie-table"><tbody>
"""
                    for row in strip:
                        html += "            <tr>\n"
                        for cell in row:
                            if cell["id"] > 0:
                                num_html = f"                <div class=\"song-number\">{cell['id']}</div>\n" if effective_show_song_number else ""
                                html += f"""              <td class="cell-song">
{num_html}                <div class="song-name">{cell['title']}</div>
              </td>\n"""
                            else:
                                html += '              <td class="cell-empty"></td>\n'
                        html += "            </tr>\n"
                    html += "          </tbody></table>\n        </div>\n"

                html += """      </div>
      <div class="participant-slots">
        <div class="slot-item"><span>Participant Name:</span> <span style="display:inline-block; width:180px; border-bottom:1.5px dashed #f59e0b;"></span></div>
        <div class="slot-item"><span>Mobile Number:</span> <span style="display:inline-block; width:180px; border-bottom:1.5px dashed #f59e0b;"></span></div>
        <div style="font-size:10px; color:#cbd5e1;">Prizes: Early 5 &bull; 3 Lines &bull; 4 Corners &bull; Full House</div>
      </div>
    </div>
  </div>
"""
    html += f"""
  <script>
    let currentTitleFontSize = {f_title['size_pt']};
    function updateFontSizeDisplay(sz) {{
      currentTitleFontSize = sz;
      const lbl = document.getElementById('current-font-size-label');
      if (lbl) lbl.innerText = sz + 'pt';
      const slider = document.getElementById('toolbar-font-slider');
      if (slider) slider.value = sz;
      const items = document.querySelectorAll('.song-title-direct, .song-name');
      items.forEach(el => {{
        el.style.fontSize = sz + 'pt';
      }});
    }}

    function adjustFontSize(delta) {{
      const next = Math.max(8, Math.min(32, Math.round((currentTitleFontSize + delta) * 10) / 10));
      updateFontSizeDisplay(next);
    }}

    function setFontSizeDirect(sz) {{
      updateFontSizeDisplay(parseFloat(sz));
    }}
  </script>
</body>
</html>
"""

    # 5. Archive and Output File Writing
    archive_html = archive_dir / f"{clean_batch_name}.html"
    archive_registry = archive_dir / f"{clean_batch_name}_registry.json"

    # Always write to tickets_archive
    with open(archive_html, "w", encoding="utf-8") as f:
        f.write(html)

    # Save Layout Registry JSON for Game Day Verification
    detailed_tickets = []
    for s_idx, t in enumerate(tickets, start=1):
        raw_tid = str(t.get("ticket_id", s_idx)).lstrip("#")
        s_num = int(raw_tid) if raw_tid.isdigit() else s_idx
        strips = t.get("strips", [])
        if is_2_strip and len(strips) >= 2:
            top_tid = f"{(s_num * 2 - 1):03d}"
            bot_tid = f"{(s_num * 2):03d}"
            detailed_tickets.append({
                "ticket_id": top_tid,
                "sheet": s_num,
                "strip_pos": "Top Strip",
                "paired_ticket_id": bot_tid,
                "grid": strips[0],
                "strips": [strips[0]]
            })
            detailed_tickets.append({
                "ticket_id": bot_tid,
                "sheet": s_num,
                "strip_pos": "Bottom Strip",
                "paired_ticket_id": top_tid,
                "grid": strips[1],
                "strips": [strips[1]]
            })
        elif strips:
            tid = f"{s_num:03d}"
            detailed_tickets.append({
                "ticket_id": tid,
                "sheet": s_num,
                "strip_pos": "Single Strip",
                "paired_ticket_id": None,
                "grid": strips[0],
                "strips": [strips[0]]
            })

    registry_data = {
        "batch_name": clean_batch_name,
        "generated_at": datetime.now().isoformat(),
        "format_mode": format_mode,
        "print_mode": effective_print_mode,
        "total_sheets": num_sheets,
        "total_tickets": len(detailed_tickets),
        "template_path": str(template_path) if template_path else "",
        "calibration": calibration,
        "tickets": detailed_tickets,
        "sheets": tickets
    }
    with open(archive_registry, "w", encoding="utf-8") as rf:
        json.dump(registry_data, rf, indent=2)

    # Backwards compatibility
    compat_out = BASE_DIR / "generator" / "housie_tickets_output.html"
    compat_out.parent.mkdir(parents=True, exist_ok=True)
    with open(compat_out, "w", encoding="utf-8") as f:
        f.write(html)

    if output_html_path and Path(output_html_path).resolve() != archive_html.resolve():
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_html_path

    return str(archive_html)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate Musical Tambola Housie Tickets")
    parser.add_argument("--sheets", type=int, default=100, help="Number of sheets (default: 100)")
    parser.add_argument("--format", type=str, default="2-strip", choices=["1-strip", "2-strip"], help="Format mode")
    parser.add_argument("--template", type=str, default=None, help="Path to background template image")
    parser.add_argument("--batch-name", type=str, default=None, help="Custom batch or event name")
    parser.add_argument("--no-slots", action="store_true", help="Hide participant name/mobile slots")
    parser.add_argument("--output", type=str, default=None, help="Output HTML file path")
    args = parser.parse_args()

    result = generate_housie_tickets(
        num_sheets=args.sheets,
        format_mode=args.format,
        template_path=args.template,
        show_participant_slots=not args.no_slots,
        batch_name=args.batch_name,
        output_html_path=args.output
    )
    print(f"Success! Housie tickets exported to: {result}")

