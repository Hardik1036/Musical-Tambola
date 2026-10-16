"""
Musical Tambola - Localhost Web Studio Server
FastAPI web application exposing interactive Host Studio, Claim Verifier,
Ticket Generator, Lucky Draw Raffle, and Audio Streaming on http://localhost:8000.
"""
import os
import sys

# Ensure headless environment flags are configured before any imports
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import re
import io
import csv
import json
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import (
    BASE_DIR, SONGS_DIR, BRANDING_DIR, GENERATOR_DIR, TICKETS_ARCHIVE_DIR,
    DATABASE_PATH, TICKETS_JSON_PATH, TOTAL_NUMBERS
)
import database
import song_bank
from modules.asset_manager import AssetManager
from modules.ticket_engine import TicketEngine
from main_app import (
    normalize_batch_registry,
    normalize_ticket_query,
    evaluate_strip_patterns,
    load_audio_config,
    save_audio_config,
    get_song_cue,
    scan_audio_folder,
    format_seconds_to_time,
    parse_time_to_seconds,
    extract_cell_id
)

logger = logging.getLogger("tambola.web")

app = FastAPI(title="Musical Tambola Host Studio", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure database is initialized
database.init_db()
database.seed_default_songs()
asset_mgr = AssetManager()
ticket_engine = TicketEngine()


def extract_title_from_stem(stem: str) -> str:
    """Extract clean song title without leading track numbers or prefixes."""
    t = re.sub(r'^(?:track[_\s-]*)?0*([1-9]|[1-8][0-9]|90)[\s\._\-]+', '', stem, flags=re.IGNORECASE).strip()
    return t if t else stem


def resolve_song_meta(num: int) -> Dict[str, Any]:
    """Resolves full metadata, English & Hindi titles, decade pillar, and audio file for a song 1-90."""
    cfg = load_audio_config()
    cues = cfg.get("song_cues", {})
    cue = cues.get(str(num)) or cues.get(f"{num:02d}") or {}
    file_path = cue.get("file_path", "")
    if not file_path or not Path(file_path).exists():
        file_path = song_bank.find_audio_file(num) or ""
    override_title = (cue.get("title") or "").strip()

    db_song = database.get_song(num) or {}
    db_title = (db_song.get("title") or "").strip()
    db_artist = (db_song.get("artist") or "").strip()
    db_year = str(db_song.get("year") or "").strip()

    bank_entry = song_bank.get_song(num) or {}
    bank_title = (bank_entry.get("title") or "").strip()

    file_title = ""
    if file_path:
        stem = Path(file_path).stem
        file_title = extract_title_from_stem(stem)

    title = override_title or file_title or bank_title or db_title or f"Song #{num}"
    hindi = db_title if any(ord(c) > 127 for c in db_title) else ""
    english = file_title or bank_title or title

    pillar_name = "Satyam" if num <= 29 else ("Shivam" if num <= 59 else "Sundaram")
    pillar = f"{pillar_name} ({'1–29' if num <= 29 else ('30–59' if num <= 59 else '60–90')})"
    col_idx = ((num - 1) // 10) + 1 if num <= 80 else 9

    return {
        "id": num,
        "number": num,
        "title": title,
        "english": english,
        "hindi": hindi,
        "artist": db_artist,
        "year": db_year,
        "pillar": pillar,
        "pillar_name": pillar_name,
        "column": col_idx,
        "start_time": cue.get("start_time", 0.0),
        "duration": cue.get("duration", 0.0),
        "has_audio": bool(file_path and Path(file_path).exists()),
        "file_path": file_path
    }


@app.get("/api/songs")
def get_all_songs_dict():
    """Retrieve full 1-90 song dictionary with real titles, pillars, and cues."""
    return {str(num): resolve_song_meta(num) for num in range(1, TOTAL_NUMBERS + 1)}


@app.get("/api/state")
def get_game_state():
    """Retrieve active session state, called numbers, and latest call."""
    session_id = database.get_or_create_active_session()
    called = database.get_called_numbers(session_id)
    history = database.get_called_history(session_id)
    all_songs = {str(num): resolve_song_meta(num) for num in range(1, TOTAL_NUMBERS + 1)}

    last_call = None
    if history:
        last_id = history[0]["song_id"]
        last_call = {
            "song_id": last_id,
            "song": resolve_song_meta(last_id),
            "called_at": history[0].get("called_at")
        }

    return {
        "session_id": session_id,
        "total_numbers": TOTAL_NUMBERS,
        "called_numbers": called,
        "called_count": len(called),
        "remaining_count": TOTAL_NUMBERS - len(called),
        "last_call": last_call,
        "history": history[:25],
        "all_songs": all_songs,
        "songs": all_songs
    }


@app.post("/api/call/random")
def call_random_number():
    """Draw next uncalled number at random."""
    session_id = database.get_or_create_active_session()
    called = set(database.get_called_numbers(session_id))
    uncalled = [n for n in range(1, TOTAL_NUMBERS + 1) if n not in called]

    if not uncalled:
        raise HTTPException(status_code=400, detail="All 90 numbers have been called!")

    chosen = random.choice(uncalled)
    database.call_number(session_id, chosen)
    song = resolve_song_meta(chosen)

    return {
        "song_id": chosen,
        "song": song,
        "called_count": len(called) + 1,
        "remaining_count": TOTAL_NUMBERS - len(called) - 1,
    }


@app.post("/api/call/{song_id}")
def manual_call_number(song_id: int):
    """Manually call a specific song ID."""
    if not 1 <= song_id <= TOTAL_NUMBERS:
        raise HTTPException(status_code=400, detail=f"Song ID must be between 1 and {TOTAL_NUMBERS}")

    session_id = database.get_or_create_active_session()
    try:
        database.call_number(session_id, song_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    song = resolve_song_meta(song_id)
    return {"status": "success", "song_id": song_id, "song": song}


@app.post("/api/call/undo")
def undo_last_call():
    """Revert most recent call."""
    session_id = database.get_or_create_active_session()
    removed = database.undo_last_call(session_id)
    if not removed:
        raise HTTPException(status_code=400, detail="No calls to undo in current session.")
    return {"status": "undone", "removed_song_id": removed}


@app.post("/api/reset")
def reset_session():
    """Reset game to a fresh session."""
    session_id = database.reset_active_session()
    return {"status": "reset", "new_session_id": session_id}


@app.get("/api/audio/{song_id}")
def stream_audio(song_id: str):
    """Stream audio file for the requested song ID with HTTP Range request & inline playback support."""
    try:
        clean_id = int(str(song_id).strip().lstrip("0") or "0")
    except Exception:
        clean_id = 1

    cue = get_song_cue(clean_id)
    audio_path = cue.get("file_path")
    p = Path(audio_path) if audio_path else None

    if not p or not p.exists():
        p_str = song_bank.find_audio_file(clean_id)
        if p_str:
            p = Path(p_str)

    if not p or not p.exists():
        song = database.get_song(clean_id)
        if song and song.get("audio_path"):
            cand = Path(song["audio_path"])
            if cand.exists():
                p = cand

    if not p or not p.exists():
        for ext in [".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"]:
            cand = SONGS_DIR / f"{clean_id}{ext}"
            if cand.exists():
                p = cand
                break

    if not p or not p.exists():
        raise HTTPException(status_code=404, detail=f"Audio file for Song #{clean_id} not found")

    ext = p.suffix.lower()
    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
    }
    media_type = mime_map.get(ext, "audio/mpeg")

    headers = {
        "Accept-Ranges": "bytes",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length",
        "Cache-Control": "public, max-age=3600",
    }

    return FileResponse(
        path=str(p),
        media_type=media_type,
        content_disposition_type="inline",
        headers=headers
    )



@app.post("/api/audio/seek")
async def audio_seek(request: Request):
    """Acknowledge audio seek timestamp."""
    try:
        data = await request.json()
        return {"status": "ok", "currentTime": data.get("currentTime", 0.0)}
    except Exception:
        return {"status": "ok"}



@app.get("/api/audio-config")
def get_audio_config():
    """Retrieve persistent audio configuration."""
    return load_audio_config()


@app.post("/api/audio-config")
async def update_audio_config(request: Request):
    """Update audio folder path or song cues in audio_config.json."""
    data = await request.json()
    cfg = load_audio_config()
    if "audio_folder_path" in data:
        cfg["audio_folder_path"] = data["audio_folder_path"]
    if "song_cues" in data:
        cfg["song_cues"] = data["song_cues"]
    save_audio_config(cfg)
    return {"status": "success", "config": cfg}


@app.post("/api/audio-config/rescan")
def rescan_audio_folder():
    """Rescan the active audio directory for tracks 1-90."""
    cfg = load_audio_config()
    folder = cfg.get("audio_folder_path") or str(SONGS_DIR.resolve())
    matched = scan_audio_folder(folder) if Path(folder).is_dir() else {}
    for num, fpath in matched.items():
        num_str = str(num)
        if num_str not in cfg["song_cues"]:
            cfg["song_cues"][num_str] = {}
        cfg["song_cues"][num_str]["file_path"] = fpath
        try:
            database.update_audio_path(num, fpath)
        except Exception:
            pass
    save_audio_config(cfg)
    return {"status": "success", "folder": folder, "matched_count": len(matched)}


@app.post("/api/catalog/save-cue")
async def save_song_cue(request: Request):
    """Save start time and duration cue for a track."""
    data = await request.json()
    song_id = int(data.get("song_id"))
    start_time = data.get("start_time", 0.0)
    duration = data.get("duration", 0.0)
    title = data.get("title")

    cfg = load_audio_config()
    s_key = str(song_id)
    if s_key not in cfg["song_cues"]:
        cfg["song_cues"][s_key] = {}

    cfg["song_cues"][s_key]["start_time"] = parse_time_to_seconds(start_time)
    cfg["song_cues"][s_key]["duration"] = parse_time_to_seconds(duration)
    if title:
        cfg["song_cues"][s_key]["title"] = title
    if data.get("file_path"):
        cfg["song_cues"][s_key]["file_path"] = data["file_path"]

    save_audio_config(cfg)
    return {"status": "success", "song_id": song_id, "cue": cfg["song_cues"][s_key]}


@app.get("/api/archive-batch/{batch_name}")
def get_archive_batch(batch_name: str):
    """Retrieve normalized batch summary with total sheets and tickets."""
    clean = batch_name.replace("_registry", "").replace(".json", "")
    reg_file = TICKETS_ARCHIVE_DIR / f"{clean}_registry.json"
    if not reg_file.exists():
        candidates = list(TICKETS_ARCHIVE_DIR.glob(f"*{clean}*_registry.json"))
        if candidates:
            reg_file = candidates[0]
        else:
            raise HTTPException(status_code=404, detail=f"Archive batch '{batch_name}' not found")

    with open(reg_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    normalized = normalize_batch_registry(data)
    return {
        "batch_name": normalized["batch_name"],
        "total_sheets": normalized["total_sheets"],
        "total_tickets": normalized["total_tickets"],
        "ordered_sheet_nums": normalized["ordered_sheet_nums"],
        "ordered_ticket_nums": normalized["ordered_ticket_nums"],
    }


@app.get("/api/verify-sheet/{batch_name}/{ticket_query}")
def verify_sheet_endpoint(batch_name: str, ticket_query: str):
    """Resolves player's 2-strip sheet for any ticket ID and evaluates live patterns & call orders."""
    clean = batch_name.replace("_registry", "").replace(".json", "")
    reg_file = TICKETS_ARCHIVE_DIR / f"{clean}_registry.json"
    if not reg_file.exists():
        candidates = list(TICKETS_ARCHIVE_DIR.glob(f"*{clean}*_registry.json"))
        if candidates:
            reg_file = candidates[0]
        else:
            raise HTTPException(status_code=404, detail=f"Archive batch '{batch_name}' not found")

    with open(reg_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    normalized = normalize_batch_registry(data)
    num = normalize_ticket_query(ticket_query)
    if num is None:
        raise HTTPException(status_code=400, detail="Invalid ticket query")

    # Find sheet and focused ticket
    sheet_num = None
    focused_tid = None
    if num in normalized["tickets_by_num"]:
        t_obj = normalized["tickets_by_num"][num]
        sheet_num = t_obj["sheet"]
        focused_tid = t_obj["ticket_id"]
    elif num in normalized["sheets"]:
        sheet_num = num
        sh = normalized["sheets"][num]
        focused_tid = sh["top"]["ticket_id"] if sh.get("top") else f"{num:03d}"
    else:
        est = (num + 1) // 2 if num % 2 != 0 else num // 2
        if est in normalized["sheets"]:
            sheet_num = est
            focused_tid = f"{num:03d}"
        else:
            raise HTTPException(status_code=404, detail=f"Ticket or sheet #{num} not found in batch '{clean}'")

    sheet_data = normalized["sheets"].get(sheet_num)
    if not sheet_data:
        raise HTTPException(status_code=404, detail="Sheet data not found")

    top_ticket = sheet_data.get("top")
    bottom_ticket = sheet_data.get("bottom")

    session_id = database.get_or_create_active_session()
    called = database.get_called_numbers(session_id)
    called_set = set(called)
    call_orders = {song_id: idx + 1 for idx, song_id in enumerate(called)}
    last_called = called[-1] if called else None

    # Evaluate patterns
    ev1 = evaluate_strip_patterns(top_ticket["grid"], called_set) if top_ticket else None
    ev2 = evaluate_strip_patterns(bottom_ticket["grid"], called_set) if bottom_ticket else None

    combined_hits = (ev1["total_hits"] if ev1 else 0) + (ev2["total_hits"] if ev2 else 0)
    combined_total = (ev1["total_nums"] if ev1 else 0) + (ev2["total_nums"] if ev2 else 0)
    sheet_house_ok = (combined_hits == combined_total and combined_total > 0)

    # Format grids with song titles, call orders, and latest flags
    def format_grid(grid):
        formatted = []
        for row in grid:
            f_row = []
            for cell in row:
                cid = extract_cell_id(cell)
                if cid > 0:
                    is_hit = cid in called_set
                    order = call_orders.get(cid, 0)
                    meta = resolve_song_meta(cid)
                    f_row.append({
                        "id": cid,
                        "title": meta["title"],
                        "english": meta["english"],
                        "hindi": meta["hindi"],
                        "is_hit": is_hit,
                        "order": order,
                        "is_latest": (cid == last_called)
                    })
                else:
                    f_row.append(None)
            formatted.append(f_row)
        return formatted

    top_formatted = format_grid(top_ticket["grid"]) if top_ticket else None
    bot_formatted = format_grid(bottom_ticket["grid"]) if bottom_ticket else None

    return {
        "batch_name": clean,
        "sheet_num": sheet_num,
        "focused_ticket_id": focused_tid,
        "total_game_drawn": len(called),
        "total_game_remaining": TOTAL_NUMBERS - len(called),
        "last_called_song": last_called,
        "top_ticket": {
            "ticket_id": top_ticket["ticket_id"] if top_ticket else None,
            "strip_pos": "Top Strip",
            "paired_ticket_id": top_ticket.get("paired_ticket_id") if top_ticket else None,
            "grid": top_formatted,
            "eval": ev1
        } if top_ticket else None,
        "bottom_ticket": {
            "ticket_id": bottom_ticket["ticket_id"] if bottom_ticket else None,
            "strip_pos": "Bottom Strip",
            "paired_ticket_id": bottom_ticket.get("paired_ticket_id") if bottom_ticket else None,
            "grid": bot_formatted,
            "eval": ev2
        } if bottom_ticket else None,
        "combined_hits": combined_hits,
        "combined_total": combined_total,
        "sheet_house_ok": sheet_house_ok,
    }



@app.get("/api/tickets")
def list_tickets():
    """Retrieve all registered tickets."""
    return database.get_all_tickets()


@app.get("/api/ticket/{ticket_id}")
def inspect_ticket(ticket_id: str):
    """Inspect ticket layout and compute verdict against called numbers."""
    ticket = database.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found")

    session_id = database.get_or_create_active_session()
    called = set(database.get_called_numbers(session_id))
    all_songs = {s["id"]: s for s in database.get_all_songs()}

    strips = ticket["strips"]
    all_ticket_songs = [sid for strip in strips for row in strip for sid in row if sid > 0]
    called_ticket_songs = [sid for sid in all_ticket_songs if sid in called]

    # Evaluate patterns
    verdicts = []

    # 1. Early 5
    early5_done = len(called_ticket_songs) >= 5
    verdicts.append({
        "pattern": "Early 5 (Jaldi 5)",
        "complete": early5_done,
        "detail": f"{min(5, len(called_ticket_songs))}/5 numbers called"
    })

    # Per strip checks
    for s_idx, strip in enumerate(strips, start=1):
        pfx = f"Strip {s_idx} - " if len(strips) > 1 else ""
        row0 = [sid for sid in strip[0] if sid > 0]
        row1 = [sid for sid in strip[1] if sid > 0]
        row2 = [sid for sid in strip[2] if sid > 0]

        r0_done = all(sid in called for sid in row0)
        verdicts.append({
            "pattern": f"{pfx}Top Line",
            "complete": r0_done,
            "detail": f"{sum(1 for s in row0 if s in called)}/5 called" + ("" if r0_done else f" (Missing: {list(set(row0) - called)})")
        })

        r1_done = all(sid in called for sid in row1)
        verdicts.append({
            "pattern": f"{pfx}Middle Line",
            "complete": r1_done,
            "detail": f"{sum(1 for s in row1 if s in called)}/5 called" + ("" if r1_done else f" (Missing: {list(set(row1) - called)})")
        })

        r2_done = all(sid in called for sid in row2)
        verdicts.append({
            "pattern": f"{pfx}Bottom Line",
            "complete": r2_done,
            "detail": f"{sum(1 for s in row2 if s in called)}/5 called" + ("" if r2_done else f" (Missing: {list(set(row2) - called)})")
        })

        corners = []
        if row0:
            corners.append(row0[0])
            if len(row0) > 1:
                corners.append(row0[-1])
        if row2:
            corners.append(row2[0])
            if len(row2) > 1:
                corners.append(row2[-1])
        c_done = (len(corners) == 4) and all(sid in called for sid in corners)
        verdicts.append({
            "pattern": f"{pfx}Four Corners",
            "complete": c_done,
            "detail": f"{sum(1 for s in corners if s in called)}/{len(corners)} called" + ("" if c_done else f" (Missing: {list(set(corners) - called)})")
        })

        strip_all = [sid for row in strip for sid in row if sid > 0]
        fh_done = all(sid in called for sid in strip_all)
        verdicts.append({
            "pattern": f"{pfx}Full House",
            "complete": fh_done,
            "detail": f"{sum(1 for s in strip_all if s in called)}/15 called" + ("" if fh_done else f" (Missing {15 - sum(1 for s in strip_all if s in called)})")
        })

    if len(strips) == 2:
        dual_fh = len(called_ticket_songs) == 30
        verdicts.append({
            "pattern": "Dual Full House (30 Songs)",
            "complete": dual_fh,
            "detail": f"{len(called_ticket_songs)}/30 called"
        })

    is_any_valid = any(v["complete"] for v in verdicts)

    return {
        "ticket": ticket,
        "called_numbers": list(called),
        "all_songs": all_songs,
        "is_valid_claim": is_any_valid,
        "verdicts": verdicts,
    }


@app.get("/api/template-presets")
def list_template_presets():
    """List all available template configurations."""
    import template_config
    return template_config.load_template_configs()


@app.get("/api/template-presets/{preset_id}")
def get_preset_detail(preset_id: str):
    """Retrieve full calibration details for a preset."""
    import template_config
    return template_config.get_template_config(preset_id)


@app.post("/api/template-presets/{preset_id}")
async def save_preset_detail(preset_id: str, request: Request):
    """Save or update custom preset calibration."""
    import template_config
    data = await request.json()
    return template_config.save_custom_preset(preset_id, data)


@app.get("/api/template-image/{preset_id}")
def get_template_image(preset_id: str):
    """Serve template image for preview."""
    import template_config
    cfg = template_config.get_template_config(preset_id)
    t_file = BASE_DIR / cfg.get("template_file", "assets/branding/Garba_Night_Musical_Housie_Template.png")
    if not t_file.exists():
        t_file = BRANDING_DIR / "uploaded_template_664.png"
    if not t_file.exists():
        t_file = BRANDING_DIR / "Festive_Musical_Housie_Template.png"
    if t_file.exists():
        return FileResponse(str(t_file))
    raise HTTPException(status_code=404, detail="Template image not found")


@app.post("/api/generate-tickets")
async def generate_ticket_batch(
    count: int = Form(100),
    mode: str = Form("2-strip"),
    batch_name: Optional[str] = Form(None),
    show_slots: bool = Form(True),
    template_file: Optional[UploadFile] = File(None),
    preset_id: Optional[str] = Form("garba_night"),
    print_mode: Optional[str] = Form("direct_in_cell"),
    calibration_json: Optional[str] = Form(None),
    participants_text: Optional[str] = Form(None),
    show_song_number: bool = Form(False)
):
    """Generate batch of 1-strip or 2-strip tickets with customizable in-cell calibration."""
    from generator.generate_housie_tickets import generate_housie_tickets, sanitize_batch_name
    import template_config

    tpl_path = None
    if template_file and template_file.filename:
        ext = Path(template_file.filename).suffix.lower()
        tpl_saved = BRANDING_DIR / f"uploaded_template_{random.randint(100,999)}{ext}"
        BRANDING_DIR.mkdir(parents=True, exist_ok=True)
        content = await template_file.read()
        with open(tpl_saved, "wb") as f:
            f.write(content)
        tpl_path = str(tpl_saved)

    calibration_dict = None
    if calibration_json:
        try:
            calibration_dict = json.loads(calibration_json)
        except Exception:
            pass

    # Parse participant names if provided
    participants_list = []
    if participants_text and participants_text.strip():
        for line in participants_text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if len(parts) >= 2:
                participants_list.append({"name": parts[0], "mobile": parts[1]})
            elif len(parts) == 1:
                participants_list.append({"name": parts[0], "mobile": ""})

    out_file = generate_housie_tickets(
        num_sheets=count,
        format_mode=mode,
        template_path=tpl_path,
        show_participant_slots=show_slots,
        batch_name=batch_name,
        save_to_database=True,
        preset_id=preset_id,
        calibration=calibration_dict,
        participants_list=participants_list if participants_list else None,
        print_mode=print_mode,
        show_song_number=show_song_number
    )
    clean_batch = sanitize_batch_name(batch_name)
    return {
        "status": "success",
        "count": count,
        "mode": mode,
        "print_mode": print_mode,
        "batch_name": clean_batch,
        "html_url": f"/archive/{clean_batch}",
        "file": str(out_file)
    }


@app.get("/api/archive/{batch_name}/registry")
def get_archived_registry(batch_name: str):
    """Retrieve full layout registry JSON for an archived batch."""
    from config import TICKETS_ARCHIVE_DIR
    from generator.generate_housie_tickets import sanitize_batch_name
    clean = sanitize_batch_name(batch_name)
    target = TICKETS_ARCHIVE_DIR / f"{clean}_registry.json"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Registry not found")
    with open(target, "r", encoding="utf-8") as rf:
        return json.load(rf)


@app.get("/api/archive/{batch_name}/ticket/{ticket_id}")
def inspect_archive_ticket(batch_name: str, ticket_id: str):
    """Inspect ticket from an archived batch against currently called numbers."""
    from config import TICKETS_ARCHIVE_DIR
    from generator.generate_housie_tickets import sanitize_batch_name
    clean = sanitize_batch_name(batch_name)
    target = TICKETS_ARCHIVE_DIR / f"{clean}_registry.json"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Batch registry not found")
    with open(target, "r", encoding="utf-8") as rf:
        data = json.load(rf)

    target_tid = str(ticket_id).strip().lstrip("0") or "0"
    matched_t = None
    for t in data.get("tickets", []):
        t_id_str = str(t.get("ticket_id", "")).strip().lstrip("0") or "0"
        if t_id_str == target_tid or str(t.get("ticket_id", "")) == str(ticket_id):
            matched_t = t
            break

    if not matched_t:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found in batch '{batch_name}'")

    session_id = database.get_or_create_active_session()
    called = set(database.get_called_numbers(session_id))
    all_songs = {s["id"]: s for s in database.get_all_songs()}

    strips = matched_t.get("strips", [])
    all_ticket_songs = [sid for strip in strips for row in strip for sid in row if sid > 0]
    called_ticket_songs = [sid for sid in all_ticket_songs if sid in called]

    verdicts = []
    # Early 5
    early5_done = len(called_ticket_songs) >= 5
    verdicts.append({
        "pattern": "Early 5 (Jaldi 5)",
        "complete": early5_done,
        "detail": f"{min(5, len(called_ticket_songs))}/5 numbers called"
    })

    # Per strip checks
    for s_idx, strip in enumerate(strips, start=1):
        pfx = f"Strip {s_idx} - " if len(strips) > 1 else ""
        row0 = [sid for sid in strip[0] if sid > 0]
        row1 = [sid for sid in strip[1] if sid > 0]
        row2 = [sid for sid in strip[2] if sid > 0]

        r0_done = all(sid in called for sid in row0)
        verdicts.append({
            "pattern": f"{pfx}Top Line",
            "complete": r0_done,
            "detail": f"{sum(1 for s in row0 if s in called)}/5 called" + ("" if r0_done else f" (Missing: {list(set(row0) - called)})")
        })

        r1_done = all(sid in called for sid in row1)
        verdicts.append({
            "pattern": f"{pfx}Middle Line",
            "complete": r1_done,
            "detail": f"{sum(1 for s in row1 if s in called)}/5 called" + ("" if r1_done else f" (Missing: {list(set(row1) - called)})")
        })

        r2_done = all(sid in called for sid in row2)
        verdicts.append({
            "pattern": f"{pfx}Bottom Line",
            "complete": r2_done,
            "detail": f"{sum(1 for s in row2 if s in called)}/5 called" + ("" if r2_done else f" (Missing: {list(set(row2) - called)})")
        })

        corners = []
        if row0:
            corners.append(row0[0])
            if len(row0) > 1:
                corners.append(row0[-1])
        if row2:
            corners.append(row2[0])
            if len(row2) > 1:
                corners.append(row2[-1])
        c_done = (len(corners) == 4) and all(sid in called for sid in corners)
        verdicts.append({
            "pattern": f"{pfx}Four Corners",
            "complete": c_done,
            "detail": f"{sum(1 for s in corners if s in called)}/{len(corners)} called" + ("" if c_done else f" (Missing: {list(set(corners) - called)})")
        })

        strip_all = [sid for row in strip for sid in row if sid > 0]
        fh_done = all(sid in called for sid in strip_all)
        verdicts.append({
            "pattern": f"{pfx}Full House",
            "complete": fh_done,
            "detail": f"{sum(1 for s in strip_all if s in called)}/15 called" + ("" if fh_done else f" (Missing {15 - sum(1 for s in strip_all if s in called)})")
        })

    if len(strips) == 2:
        dual_fh = len(called_ticket_songs) == 30
        verdicts.append({
            "pattern": "Dual Full House (30 Songs)",
            "complete": dual_fh,
            "detail": f"{len(called_ticket_songs)}/30 called"
        })

    is_any_valid = any(v["complete"] for v in verdicts)

    return {
        "ticket": matched_t,
        "called_numbers": list(called),
        "all_songs": all_songs,
        "is_valid_claim": is_any_valid,
        "verdicts": verdicts,
        "batch_name": clean
    }


# ===========================================================================
# FEATURE 1 & 2: LUCKY DRAW APIs (Tie-Breaker & Whole-Batch Strict No-Repeat)
# ===========================================================================
@app.get("/api/lucky-draw/state")
def get_lucky_draw_state(
    batch_name: Optional[str] = None,
    is_custom: Optional[bool] = False,
    start: Optional[int] = None,
    end: Optional[int] = None
):
    """Retrieves current lucky draw audit log and drawn tickets pool."""
    from config import TICKETS_ARCHIVE_DIR
    from generator.generate_housie_tickets import sanitize_batch_name
    
    clean_batch = sanitize_batch_name(batch_name) if (batch_name and batch_name != "custom_range" and not is_custom) else ""
    is_custom_mode = bool(is_custom or batch_name in ("custom_range", "") or (start is not None and end is not None))
    
    drawn_tickets = database.get_drawn_lucky_tickets(clean_batch if clean_batch else None)
    audit_history = database.get_lucky_draw_records()
    
    total_tickets = 0
    all_ticket_ids = []
    
    if is_custom_mode and start is not None and end is not None:
        s = max(1, int(start))
        e = max(s, int(end))
        all_ticket_ids = [f"{i:03d}" for i in range(s, e + 1)]
        total_tickets = len(all_ticket_ids)
        clean_batch = "custom_range"
    elif clean_batch:
        target = TICKETS_ARCHIVE_DIR / f"{clean_batch}_registry.json"
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    data = json.load(f)
                all_ticket_ids = [str(t.get("ticket_id", "")).strip() for t in data.get("tickets", []) if t.get("ticket_id")]
                total_tickets = len(all_ticket_ids)
            except Exception:
                pass

    drawn_set = set(str(t).strip() for t in drawn_tickets)
    eligible = [t for t in all_ticket_ids if t not in drawn_set] if all_ticket_ids else []

    return {
        "batch_name": clean_batch,
        "audit_history": audit_history,
        "drawn_tickets": list(drawn_set),
        "drawn_count": len(drawn_set),
        "total_tickets": total_tickets,
        "remaining_count": len(eligible) if total_tickets > 0 else 0,
        "eligible_tickets": eligible
    }


@app.post("/api/lucky-draw/tie-breaker")
async def execute_tie_breaker(request: Request):
    """
    Lucky Draw Mode A: Picks winner(s) exclusively from entered candidate ticket numbers.
    Payload: { candidate_tickets: str or list, winner_count: int, prize_name: str }
    """
    body = await request.json()
    raw_candidates = body.get("candidate_tickets", "")
    winner_count = max(1, min(10, int(body.get("winner_count", body.get("winners_count", 1)))))
    prize = str(body.get("prize_name", body.get("prize_label", "Tie-Breaker Winner"))).strip() or "Tie-Breaker Winner"

    candidates_list: List[str] = []
    if isinstance(raw_candidates, list):
        for c in raw_candidates:
            val = str(c).strip().lstrip("#")
            if val:
                candidates_list.append(val)
    elif isinstance(raw_candidates, str):
        # Split on comma, space, semicolon, or newline
        tokens = re.split(r'[\s,;\n\r]+', raw_candidates.strip())
        for tok in tokens:
            t = tok.strip().lstrip("#")
            if t:
                candidates_list.append(t)

    # De-duplicate while preserving order
    unique_candidates = []
    seen = set()
    for c in candidates_list:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)

    if not unique_candidates:
        raise HTTPException(status_code=400, detail="Please enter at least one candidate Ticket Number.")

    k = min(winner_count, len(unique_candidates))
    winners = random.sample(unique_candidates, k)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Record into audit log
    database.add_lucky_draw_audit_entry(
        prize_name=prize,
        pool_type="🤝 Tie-Breaker Draw",
        winner_ids=winners
    )

    winners_objs = [{"ticket_id": w} for w in winners]
    return {
        "status": "success",
        "mode": "tie-breaker",
        "prize_name": prize,
        "prize": prize,
        "winner": winners_objs[0],
        "winners": winners_objs,
        "candidates": unique_candidates,
        "timestamp": timestamp
    }


@app.post("/api/lucky-draw/whole-batch")
async def execute_whole_batch_draw(request: Request):
    """
    Lucky Draw Mode B: Picks non-repeating lucky ticket from whole batch or custom range.
    Payload: { batch_name: str, prize_name: str, custom_range_start: int, custom_range_end: int }
    """
    from config import TICKETS_ARCHIVE_DIR
    from generator.generate_housie_tickets import sanitize_batch_name

    body = await request.json()
    batch_name = str(body.get("batch_name", "")).strip()
    prize = str(body.get("prize_name", body.get("prize_label", body.get("prize", "Whole-Set Lucky Ticket")))).strip() or "Whole-Set Lucky Ticket"
    is_custom = body.get("is_custom_range", False) or (batch_name in ("custom_range", ""))
    range_start = body.get("range_start", body.get("custom_range_start"))
    range_end = body.get("range_end", body.get("custom_range_end"))

    all_tickets_map: Dict[str, Any] = {}
    clean_batch = sanitize_batch_name(batch_name) if (batch_name and not is_custom and batch_name != "custom_range") else ""

    if is_custom or batch_name in ("custom_range", "") or (range_start is not None and range_end is not None):
        try:
            start_i = max(1, int(range_start if range_start is not None else 1))
            end_i = max(start_i, int(range_end if range_end is not None else 100))
            for i in range(start_i, end_i + 1):
                tid = f"{i:03d}"
                all_tickets_map[tid] = {"ticket_id": tid, "sheet_num": (i + 1) // 2}
            clean_batch = "custom_range"
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ticket number range.")
    elif clean_batch:
        target = TICKETS_ARCHIVE_DIR / f"{clean_batch}_registry.json"
        if not target.exists():
            raise HTTPException(status_code=404, detail=f"Ticket batch '{batch_name}' not found.")
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            for t in data.get("tickets", []):
                tid = str(t.get("ticket_id", "")).strip()
                if tid:
                    all_tickets_map[tid] = t
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read batch registry: {e}")
    else:
        raise HTTPException(status_code=400, detail="Please select a ticket batch or specify a range.")

    all_ticket_ids = list(all_tickets_map.keys())
    if not all_ticket_ids:
        raise HTTPException(status_code=400, detail="No tickets available in selected pool.")

    # Exclude previously drawn lucky tickets (STRICT NO-REPEAT GUARANTEE)
    drawn_tickets = database.get_drawn_lucky_tickets(clean_batch if clean_batch else None)
    drawn_set = set(str(t).strip() for t in drawn_tickets)
    available_tickets = [tid for tid in all_ticket_ids if tid not in drawn_set]

    if not available_tickets:
        raise HTTPException(
            status_code=400,
            detail=f"All {len(all_ticket_ids)} tickets in this batch have already won! Click 'Reset Lucky Ticket Pool' to start fresh."
        )

    winner_tid = random.choice(available_tickets)
    database.add_drawn_lucky_ticket(clean_batch, winner_tid, prize)

    # Record into audit log
    database.add_lucky_draw_audit_entry(
        prize_name=prize,
        pool_type=f"🎟️ Whole-Set ({clean_batch or 'Custom Range'})",
        winner_ids=[winner_tid]
    )

    winner_meta = all_tickets_map.get(winner_tid, {})
    remaining = len(available_tickets) - 1
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "status": "success",
        "mode": "whole-batch",
        "batch_name": clean_batch,
        "prize_name": prize,
        "prize": prize,
        "winner": {
            "ticket_id": winner_tid,
            "sheet_num": winner_meta.get("sheet_num")
        },
        "winner_id": winner_tid,
        "winner_meta": winner_meta,
        "remaining_count": remaining,
        "total_count": len(all_ticket_ids),
        "total_pool": len(all_ticket_ids),
        "timestamp": timestamp
    }


@app.post("/api/lucky-draw/reset-pool")
async def reset_lucky_pool(request: Request):
    """Resets drawn lucky tickets for a batch (or all batches) so all tickets can win again."""
    from generator.generate_housie_tickets import sanitize_batch_name
    body = await request.json()
    batch_name = str(body.get("batch_name", "")).strip()
    clean_batch = sanitize_batch_name(batch_name) if batch_name else None
    database.reset_drawn_lucky_pool(clean_batch)
    return {"status": "success", "message": f"Lucky ticket pool reset for '{clean_batch or 'all'}'."}


@app.post("/api/lucky-draw/clear-audit")
def clear_lucky_audit():
    """Clears all lucky draw audit history."""
    database.clear_lucky_draw_records()
    return {"status": "success"}


# ===========================================================================
# FEATURE 3: CLAIM VERIFIER & HOST CUSTOM OFFERS LOG
# ===========================================================================
@app.get("/api/claims/log")
def get_claims_log():
    """Retrieves all host-approved or rejected custom claims."""
    return database.get_host_claims_log()


@app.post("/api/claims/log")
async def record_host_claim(request: Request):
    """
    Records a host-approved or rejected claim with custom offer name, prize, and details.
    """
    body = await request.json()
    ticket_id = str(body.get("ticket_id", body.get("ticket_no", ""))).strip()
    sheet_num = int(body.get("sheet_num", 1))
    offer_name = str(body.get("offer_name", "General Claim")).strip() or "General Claim"
    prize = str(body.get("prize", body.get("prize_label", ""))).strip()
    status = str(body.get("status", "APPROVED")).upper().strip()
    details = str(body.get("details", body.get("condition_summary", body.get("notes", "")))).strip()

    if not ticket_id:
        raise HTTPException(status_code=400, detail="Ticket ID is required to log a claim.")

    session_id = database.get_or_create_active_session()
    rec_id = database.log_host_claim(
        session_id=session_id,
        ticket_id=ticket_id,
        sheet_num=sheet_num,
        offer_name=offer_name,
        prize=prize,
        status=status,
        details=details
    )

    return {
        "status": "success",
        "claim_id": rec_id,
        "ticket_id": ticket_id,
        "sheet_num": sheet_num,
        "offer_name": offer_name,
        "prize": prize,
        "verdict": status
    }


@app.post("/api/claims/clear")
def clear_claims():
    """Clears host approved claims log."""
    database.clear_host_claims_log()
    return {"status": "success"}


@app.get("/api/export/pdf")
def export_tickets_pdf(event_title: str = "Musical Tambola Night"):
    """Generate and download printable PDF tickets."""
    tickets = database.get_all_tickets()
    if not tickets:
        raise HTTPException(status_code=400, detail="No tickets in database. Generate tickets first.")

    out_file = BASE_DIR / "Musical_Tambola_Tickets.pdf"
    ticket_engine.export_pdf(tickets, str(out_file), event_title=event_title)
    return FileResponse(path=str(out_file), media_type="application/pdf", filename="Musical_Tambola_Tickets.pdf")


@app.get("/api/export/html", response_class=HTMLResponse)
def export_tickets_html(event_title: str = "Musical Tambola Night"):
    """Render and return printable HTML bundle."""
    tickets = database.get_all_tickets()
    if not tickets:
        raise HTTPException(status_code=400, detail="No tickets in database. Generate tickets first.")

    out_file = BASE_DIR / "Musical_Tambola_Tickets.html"
    ticket_engine.export_html(tickets, str(out_file), event_title=event_title)
    with open(out_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/preview-tickets", response_class=HTMLResponse)
@app.get("/api/export/housie-html", response_class=HTMLResponse)
def get_housie_tickets_output():
    """Serve the generated Housie tickets HTML sheet."""
    from config import TICKETS_ARCHIVE_DIR
    html_files = sorted(TICKETS_ARCHIVE_DIR.glob("*.html"), key=os.path.getmtime, reverse=True)
    if html_files:
        with open(html_files[0], "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    out_file = GENERATOR_DIR / "housie_tickets_output.html"
    if not out_file.exists():
        from generator.generate_housie_tickets import generate_housie_tickets
        generate_housie_tickets(num_sheets=10, format_mode="2-strip")
    with open(out_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/archives")
def list_ticket_archives():
    """List all archived ticket batches."""
    from config import TICKETS_ARCHIVE_DIR
    archives = []
    for reg_path in sorted(TICKETS_ARCHIVE_DIR.glob("*_registry.json"), key=os.path.getmtime, reverse=True):
        try:
            with open(reg_path, "r", encoding="utf-8") as rf:
                data = json.load(rf)
            b_name = data.get("batch_name", reg_path.stem.replace("_registry", ""))
            html_p = TICKETS_ARCHIVE_DIR / f"{b_name}.html"
            archives.append({
                "batch_name": b_name,
                "generated_at": data.get("generated_at", ""),
                "format_mode": data.get("format_mode", "2-strip"),
                "total_sheets": data.get("total_sheets", 0),
                "total_tickets": len(data.get("tickets", [])),
                "has_html": html_p.exists(),
                "registry_file": reg_path.name
            })
        except Exception as e:
            continue
    return archives


@app.get("/archive/{batch_name}", response_class=HTMLResponse)
def get_archived_html(batch_name: str):
    """View a specific archived printable sheet by batch name."""
    from config import TICKETS_ARCHIVE_DIR
    from generator.generate_housie_tickets import sanitize_batch_name
    clean = sanitize_batch_name(batch_name)
    target = TICKETS_ARCHIVE_DIR / f"{clean}.html"
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Archived ticket batch '{batch_name}' not found.")
    with open(target, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())



@app.post("/api/lucky-draw")
def run_lucky_draw(
    prize_name: str = Form("Lucky Draw"),
    pool_type: str = Form("Active Called Songs"),
    winner_count: int = Form(1),
    range_min: int = Form(1),
    range_max: int = Form(100)
):
    """Perform lucky draw raffle and store record in audit log."""
    session_id = database.get_or_create_active_session()
    pool = []

    if "Active Called" in pool_type:
        called = database.get_called_numbers(session_id)
        all_songs = {s["id"]: s["title"] for s in database.get_all_songs()}
        pool = [f"#{n} - {all_songs.get(n, '')}" for n in called]
    elif "Registered Ticket" in pool_type:
        tickets = database.get_all_tickets()
        pool = [f"Ticket #{t['ticket_id']}" for t in tickets]
    else:
        mn, mx = min(range_min, range_max), max(range_min, range_max)
        pool = [f"#{n}" for n in range(mn, mx + 1)]

    if not pool:
        raise HTTPException(status_code=400, detail="Selected pool is empty!")

    winner_count = min(winner_count, len(pool))
    winners = random.sample(pool, winner_count)

    database.add_lucky_draw_record(prize_name, pool_type, winners)
    return {"status": "success", "prize": prize_name, "winners": winners, "pool_size": len(pool)}


@app.get("/api/lucky-draw/history")
def get_lucky_draw_history():
    """Retrieve audit log."""
    return database.get_lucky_draw_records()


@app.delete("/api/lucky-draw/history")
def clear_lucky_draw_history():
    database.clear_lucky_draw_records()
    return {"status": "cleared"}


@app.post("/api/claim/record")
def record_claim(
    ticket_id: str = Form(...),
    winner_name: str = Form("Anonymous"),
    pattern_name: str = Form("Winning Claim")
):
    session_id = database.get_or_create_active_session()
    with database.get_connection() as conn:
        conn.execute("""
            INSERT INTO claim_records (session_id, ticket_id, pattern_name, verdict, claimed_by)
            VALUES (?, ?, ?, 'VALID', ?)
        """, (session_id, ticket_id, pattern_name, winner_name))
        conn.commit()
    return {"status": "recorded"}


@app.get("/api/catalog")
def get_catalog():
    """Get all 90 songs with audio cues, pillar, and presence."""
    cfg = load_audio_config()
    session_id = database.get_or_create_active_session()
    called_set = set(database.get_called_numbers(session_id))

    results = []
    for num in range(1, TOTAL_NUMBERS + 1):
        cue = get_song_cue(num, cfg)
        s_db = database.get_song(num) or {}
        title = cue.get("title") or s_db.get("title") or song_bank.get_song_title(num)
        artist = s_db.get("artist", "")
        year = s_db.get("year", "")
        f_path = cue.get("file_path") or s_db.get("audio_path", "")
        has_audio = bool(f_path and Path(f_path).exists())

        pillar = "Satyam" if num <= 29 else ("Shivam" if num <= 59 else "Sundaram")
        col_idx = ((num - 1) // 10) + 1 if num <= 80 else 9

        results.append({
            "id": num,
            "number": num,
            "title": title,
            "artist": artist,
            "year": year,
            "pillar": pillar,
            "column": col_idx,
            "start_time": cue.get("start_time", 0.0),
            "start_time_fmt": format_seconds_to_time(cue.get("start_time", 0.0)),
            "duration": cue.get("duration", 0.0),
            "has_audio": has_audio,
            "file_path": f_path,
            "is_called": num in called_set
        })
    return results


@app.post("/api/catalog/seed-default")
def seed_default_catalog():
    database.seed_default_songs(force=True)
    asset_mgr.map_audio_files()
    song_bank.sync_with_database()
    return {"status": "seeded", "total": 90}


@app.post("/api/catalog/import")
async def import_catalog_file(file: UploadFile = File(...)):
    """Upload and parse catalog file."""
    ext = Path(file.filename).suffix.lower()
    temp_p = BASE_DIR / f"temp_upload{ext}"
    content = await file.read()
    with open(temp_p, "wb") as f:
        f.write(content)

    try:
        total, mapped = asset_mgr.import_and_save(str(temp_p), auto_map=True)
        song_bank.sync_with_database()
    finally:
        if temp_p.exists():
            temp_p.unlink()

    return {"status": "success", "imported": total, "mapped": mapped}


# Serve Single Page Application at root / and new UI routes
@app.get("/", response_class=HTMLResponse)
def index_page():
    index_file = BASE_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content=INDEX_HTML)


@app.get("/new-ui", response_class=HTMLResponse)
@app.get("/stage", response_class=HTMLResponse)
def new_ui_page():
    index_file = BASE_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content=INDEX_HTML)


@app.get("/studio", response_class=HTMLResponse)
def studio_page():
    return HTMLResponse(content=INDEX_HTML)


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Musical Tambola — Offline Host Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0B1120;
      --bg-card: #1E293B;
      --bg-card-hover: #334155;
      --bg-subtle: #0F172A;
      --border: #334155;
      --crimson: #E11D48;
      --crimson-hover: #BE123C;
      --gold: #F59E0B;
      --gold-hover: #D97706;
      --emerald: #10B981;
      --text-primary: #F8FAFC;
      --text-secondary: #94A3B8;
      --text-muted: #64748B;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-primary);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Top Header */
    header {
      background: linear-gradient(135deg, #1E1B4B 0%, #881337 50%, #0F172A 100%);
      border-bottom: 2px solid var(--gold);
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand h1 {
      font-family: 'Outfit', sans-serif;
      font-size: 20px;
      font-weight: 800;
      letter-spacing: 1px;
      color: var(--gold);
    }
    .brand span {
      font-size: 12px;
      color: #CBD5E1;
      border-left: 1px solid rgba(255,255,255,0.2);
      padding-left: 12px;
    }

    /* Tabs Nav */
    nav.tab-bar {
      display: flex;
      background: var(--bg-subtle);
      border-bottom: 1px solid var(--border);
      padding: 0 16px;
      gap: 4px;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      font-weight: 700;
      font-size: 13px;
      padding: 12px 20px;
      cursor: pointer;
      border-bottom: 3px solid transparent;
      transition: all 0.2s;
    }
    .tab-btn:hover {
      color: var(--text-primary);
      background: rgba(255,255,255,0.03);
    }
    .tab-btn.active {
      color: #fff;
      background: var(--crimson);
      border-bottom: 3px solid var(--gold);
      border-radius: 6px 6px 0 0;
    }

    /* Main Container */
    main {
      flex: 1;
      padding: 20px;
      max-width: 1440px;
      margin: 0 auto;
      width: 100%;
    }
    .tab-pane { display: none; }
    .tab-pane.active { display: block; }

    /* Layout Grids */
    .grid-host {
      display: grid;
      grid-template-columns: 1fr 340px;
      gap: 20px;
    }
    @media (max-width: 1024px) {
      .grid-host { grid-template-columns: 1fr; }
    }

    /* Card Panels */
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
    }

    /* Buttons */
    .btn {
      background: var(--crimson);
      color: white;
      border: none;
      border-radius: 6px;
      padding: 8px 16px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .btn:hover { background: var(--crimson-hover); }
    .btn-gold {
      background: var(--gold);
      color: #0F172A;
    }
    .btn-gold:hover { background: var(--gold-hover); }
    .btn-outline {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text-secondary);
    }
    .btn-outline:hover {
      border-color: var(--gold);
      color: var(--text-primary);
    }

    /* 90 Calling Board Grid */
    .board-grid {
      display: grid;
      grid-template-columns: repeat(9, 1fr);
      gap: 6px;
      margin-top: 14px;
    }
    .board-cell {
      height: 48px;
      background: var(--bg-subtle);
      border: 1px solid var(--border);
      border-radius: 6px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.15s ease;
      position: relative;
    }
    .board-cell .num {
      font-family: 'Outfit', sans-serif;
      font-weight: 800;
      font-size: 14px;
      color: var(--text-secondary);
    }
    .board-cell .sub {
      font-size: 8px;
      color: var(--text-muted);
      max-width: 90%;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .board-cell:hover {
      border-color: var(--gold);
      background: var(--bg-card-hover);
    }
    .board-cell.called {
      background: var(--crimson);
      border-color: var(--crimson-hover);
    }
    .board-cell.called .num { color: #fff; }
    .board-cell.called .sub { color: #FFE4E6; }
    .board-cell.active-playing {
      background: var(--gold);
      border: 2px solid #fff;
      transform: scale(1.05);
      z-index: 10;
      box-shadow: 0 0 15px rgba(245, 158, 11, 0.5);
    }
    .board-cell.active-playing .num { color: #0F172A; }
    .board-cell.active-playing .sub { color: #0F172A; font-weight: bold; }

    /* Audio Player Bar */
    .audio-player-bar {
      margin-top: 14px;
      background: var(--bg-subtle);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .audio-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 13px;
      font-weight: bold;
    }
    .scrubber-row {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .scrubber-row input[type="range"] {
      flex: 1;
      accent-color: var(--gold);
      cursor: pointer;
    }
    .audio-controls-row {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    /* Spotlight Sidebar */
    .spotlight-card {
      background: linear-gradient(180deg, var(--bg-card) 0%, var(--bg-subtle) 100%);
      border: 2px solid var(--gold);
      border-radius: 12px;
      padding: 20px;
      text-align: center;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .spotlight-num {
      font-family: 'Outfit', sans-serif;
      font-size: 64px;
      font-weight: 800;
      color: var(--gold);
      line-height: 1;
      margin: 10px 0;
    }
    .spotlight-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 4px;
    }
    .spotlight-artist {
      font-size: 12px;
      color: var(--text-secondary);
    }

    /* History Feed */
    .history-feed {
      margin-top: 16px;
      max-height: 380px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .history-chip {
      background: var(--bg-subtle);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
    }

    /* 3x9 Ticket Layout Display */
    .ticket-table-preview {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      border: 2px solid var(--border);
    }
    .ticket-table-preview td {
      width: 11.11%;
      height: 52px;
      border: 1px solid var(--border);
      text-align: center;
      padding: 4px;
      font-size: 11px;
    }
    .ticket-cell-filled {
      background: var(--bg-subtle);
      color: var(--text-primary);
    }
    .ticket-cell-filled.marked {
      background: var(--emerald);
      color: white;
      font-weight: bold;
    }
    .ticket-cell-blank {
      background: #090e1a;
    }

    /* Verdict Badges */
    .verdict-badge {
      display: flex;
      justify-content: space-between;
      padding: 8px 12px;
      background: var(--bg-subtle);
      border: 1px solid var(--border);
      border-radius: 6px;
      margin-bottom: 6px;
      font-size: 13px;
    }
    .verdict-badge.complete {
      border-color: var(--emerald);
      color: var(--emerald);
      font-weight: bold;
    }

    /* Tables */
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-size: 13px;
    }
    table.data-table th, table.data-table td {
      padding: 8px 12px;
      border: 1px solid var(--border);
      text-align: left;
    }
    table.data-table th {
      background: var(--bg-subtle);
      color: var(--text-secondary);
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <h1>🎶 MUSICAL TAMBOLA</h1>
      <span>Offline Host Studio &bull; Localhost Live</span>
    </div>
    <div>
      <span style="background: rgba(16,185,129,0.15); color: var(--emerald); padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: bold; border: 1px solid var(--emerald);">
        ● LOCALHOST LIVE
      </span>
    </div>
  </header>

  <nav class="tab-bar">
    <button class="tab-btn active" onclick="switchTab('tickets')">🎫 Ticket Generator & Template Studio</button>
    <button class="tab-btn" onclick="switchTab('host')">🎲 Live Master Caller</button>
    <button class="tab-btn" onclick="switchTab('verifier')">🔍 Claim Verifier</button>
    <button class="tab-btn" onclick="switchTab('lucky')">🎁 Lucky Draw Raffle</button>
    <button class="tab-btn" onclick="switchTab('catalog')">🎵 Audio Catalog</button>
  </nav>

  <main>
    <!-- TAB 1: TICKET GENERATOR & TEMPLATE STUDIO -->
    <div id="tab-tickets" class="tab-pane active">
      <div style="display: grid; grid-template-columns: 440px 1fr; gap: 20px;">
        <div class="card">
          <div style="font-size: 16px; font-weight: 800; color: var(--gold); margin-bottom: 12px;">🎫 TICKET GENERATOR & TEMPLATE STUDIO</div>

          <!-- Section 1: Template Selection & Preview -->
          <div style="background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: var(--gold); margin-bottom: 6px; text-transform: uppercase;">1. Background Template & Preset</div>
            
            <label style="font-size: 11px; color: var(--text-secondary); display: block; margin-bottom: 3px;">Select Template Preset:</label>
            <select id="gen-preset-select" onchange="onPresetSelected(this.value)" style="width: 100%; background: var(--bg-card); color: #fff; border: 1px solid var(--border); padding: 7px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-bottom: 8px;">
              <option value="garba_night" selected>🎪 Garba Night Musical Housie (Pre-Designed Grid - Direct In-Cell)</option>
              <option value="festive_gold">✨ Festive Musical Housie (Gold / Crimson)</option>
              <option value="custom">🛠️ Custom Uploaded Template</option>
            </select>

            <label class="btn btn-outline" style="display: block; cursor: pointer; text-align: center; margin-bottom: 6px; font-size: 11px; padding: 6px 12px;">
              📁 Upload Custom Background Template (.png, .jpg)
              <input type="file" id="tpl-file" accept="image/png, image/jpeg, image/jpg, image/webp" onchange="previewSelectedTemplate(event)" style="display: none;">
            </label>
            <div id="tpl-info" style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">
              Template: Garba Night Musical Housie (Direct In-Cell)
            </div>
            <div id="tpl-res-badge" style="font-size: 11px; font-weight: bold; color: var(--emerald); margin-bottom: 8px;">
              Resolution: 2400 × 1792 px &bull; Direct Grid Aligned
            </div>
            <div style="background: #090d16; border: 1px dashed var(--border); border-radius: 6px; padding: 6px; text-align: center;">
              <img id="tpl-preview-img" src="/api/template-image/garba_night" style="max-height: 110px; max-width: 100%; border-radius: 4px; object-fit: contain;">
            </div>
          </div>

          <!-- Section 2: Print Style & Name Printing Configuration -->
          <div style="background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: var(--gold); margin-bottom: 6px; text-transform: uppercase;">2. Print Style & Name Printing</div>

            <div style="margin-bottom: 8px;">
              <label style="font-size: 11px; color: var(--text-secondary); display: block; margin-bottom: 3px;">Print Placement Mode:</label>
              <select id="gen-print-mode" onchange="onPrintModeChanged(this.value)" style="width: 100%; background: var(--bg-card); color: #fff; border: 1px solid var(--border); padding: 7px; border-radius: 6px; font-size: 12px; font-weight: bold;">
                <option value="direct_in_cell" selected>🎯 Direct In-Cell Print (Transparent, Inside Template Grid Cells)</option>
                <option value="overlay_box">📦 Standalone Card Box (With borders & banners)</option>
              </select>
              <div style="font-size: 10px; color: var(--emerald); margin-top: 3px;">✓ Zero overlap: Numbers & songs align directly into pre-printed boxes.</div>
            </div>

            <div style="margin-bottom: 8px;">
              <label style="font-size: 11px; color: var(--text-secondary); display: block; margin-bottom: 3px;">Where & How Names are Printed:</label>
              <select id="gen-name-mode" onchange="toggleNameMode(this.value)" style="width: 100%; background: var(--bg-card); color: #fff; border: 1px solid var(--border); padding: 7px; border-radius: 6px; font-size: 12px; font-weight: bold;">
                <option value="blank" selected>✍️ Leave Blank for Handwriting (Preserves template's 'नाम : ___' lines)</option>
                <option value="personalized">🖨️ Auto-Print Participant Names & Mobiles onto Tickets</option>
              </select>
            </div>

            <div id="container-names-list" style="display: none; margin-top: 8px; background: #0c1222; padding: 8px; border-radius: 6px; border: 1px solid var(--border);">
              <label style="font-size: 11px; color: var(--gold); font-weight: bold; display: block; margin-bottom: 4px;">Paste Participant List (Name, Mobile per line):</label>
              <textarea id="gen-names-text" rows="3" placeholder="Amit Shah, 9825012345&#10;Bhavna Dave, 9898012345&#10;Rahul Sharma, 9876543210" style="width: 100%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 6px; border-radius: 4px; font-family: monospace; font-size: 11px; resize: vertical;"></textarea>
              <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">Each sheet receives the next participant's name & mobile directly printed onto the underline.</div>
            </div>

            <!-- Fine-Tune Calibration Toggle -->
            <button type="button" class="btn btn-outline" onclick="toggleCalibrationPanel()" style="width: 100%; margin-top: 8px; font-size: 11px; padding: 5px 8px; justify-content: center;">
              📐 Adjust / Calibrate Coordinates & Fonts
            </button>

            <!-- Collapsible Calibration Panel -->
            <div id="panel-calibration" style="display: none; margin-top: 8px; background: #070b14; padding: 10px; border-radius: 6px; border: 1px dashed var(--gold);">
              <div style="font-size: 11px; font-weight: 800; color: var(--gold); margin-bottom: 6px;">📐 TEMPLATE GRID COORDINATES (% OF PAGE)</div>
              
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 8px;">
                <div>
                  <div style="font-size: 10px; color: var(--text-secondary); font-weight: bold;">Strip 1 Grid:</div>
                  <div style="display: flex; gap: 4px; margin-top: 2px;">
                    <input type="number" id="cal-s1-top" placeholder="Top %" step="0.01" value="14.45" title="Strip 1 Top %" style="width: 50%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 4px; font-size: 11px; border-radius: 4px;">
                    <input type="number" id="cal-s1-left" placeholder="Left %" step="0.01" value="1.96" title="Strip 1 Left %" style="width: 50%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 4px; font-size: 11px; border-radius: 4px;">
                  </div>
                  <div style="display: flex; gap: 4px; margin-top: 4px;">
                    <input type="number" id="cal-s1-w" placeholder="Width %" step="0.01" value="96.04" title="Strip 1 Width %" style="width: 50%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 4px; font-size: 11px; border-radius: 4px;">
                    <input type="number" id="cal-s1-h" placeholder="Height %" step="0.01" value="28.07" title="Strip 1 Height %" style="width: 50%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 4px; font-size: 11px; border-radius: 4px;">
                  </div>
                </div>

                <div>
                  <div style="font-size: 10px; color: var(--text-secondary); font-weight: bold;">Strip 2 Grid:</div>
                  <div style="display: flex; gap: 4px; margin-top: 2px;">
                    <input type="number" id="cal-s2-top" placeholder="Top %" step="0.01" value="60.49" title="Strip 2 Top %" style="width: 50%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 4px; font-size: 11px; border-radius: 4px;">
                    <input type="number" id="cal-s2-left" placeholder="Left %" step="0.01" value="1.96" title="Strip 2 Left %" style="width: 50%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 4px; font-size: 11px; border-radius: 4px;">
                  </div>
                  <div style="display: flex; gap: 4px; margin-top: 4px;">
                    <input type="number" id="cal-s2-w" placeholder="Width %" step="0.01" value="96.04" title="Strip 2 Width %" style="width: 50%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 4px; font-size: 11px; border-radius: 4px;">
                    <input type="number" id="cal-s2-h" placeholder="Height %" step="0.01" value="28.18" title="Strip 2 Height %" style="width: 50%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 4px; font-size: 11px; border-radius: 4px;">
                  </div>
                </div>
              </div>

              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 8px;">
                <div>
                  <label style="font-size: 10px; color: var(--text-secondary);">Number Font (pt / color):</label>
                  <div style="display: flex; gap: 4px; margin-top: 2px;">
                    <input type="number" id="cal-f-num-sz" value="16" min="8" max="28" style="width: 45%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 4px; font-size: 11px; border-radius: 4px;">
                    <input type="color" id="cal-f-num-col" value="#800020" style="width: 55%; height: 26px; border: 1px solid var(--border); border-radius: 4px; background: transparent; cursor: pointer;">
                  </div>
                </div>
                <div>
                  <label style="font-size: 10px; color: var(--text-secondary);">Title Font (pt / color):</label>
                  <div style="display: flex; gap: 4px; margin-top: 2px;">
                    <input type="number" id="cal-f-tit-sz" value="15.5" step="0.5" min="6" max="24" style="width: 45%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 4px; font-size: 11px; border-radius: 4px;">
                    <input type="color" id="cal-f-tit-col" value="#1e293b" style="width: 55%; height: 26px; border: 1px solid var(--border); border-radius: 4px; background: transparent; cursor: pointer;">
                  </div>
                </div>
              </div>

              <button type="button" class="btn btn-gold" onclick="saveCurrentCalibration()" style="width: 100%; padding: 4px 8px; font-size: 10px; justify-content: center;">
                💾 Save as Custom Preset
              </button>
            </div>
          </div>

          <!-- Section 3: Batch & Storage Configuration -->
          <div style="margin-bottom: 10px;">
            <label style="font-size: 12px; font-weight: bold; color: var(--text-primary);">Batch / Event Name:</label>
            <input type="text" id="gen-batch-name" value="garba_night_batch1" placeholder="e.g. Garba_Night_Batch1" style="width: 100%; background: var(--bg-subtle); color: var(--gold); font-weight: bold; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-top: 4px;">
            <div style="font-size: 10px; color: var(--text-secondary); margin-top: 2px;">Saved to <code>tickets_archive/&lt;Batch_Name&gt;.html</code> & <code>_registry.json</code></div>
          </div>

          <div style="display: flex; gap: 10px; margin-bottom: 12px;">
            <div style="flex: 1;">
              <label style="font-size: 12px; color: var(--text-secondary);">Sheets / Players:</label>
              <input type="number" id="gen-count" value="100" min="1" max="1000" style="width: 100%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-top: 4px;">
            </div>
            <div style="flex: 2;">
              <label style="font-size: 12px; color: var(--text-secondary);">Format Mode:</label>
              <select id="gen-mode" style="width: 100%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-top: 4px;">
                <option value="2-strip">2-Strip per Page (Combined Single Person)</option>
                <option value="1-strip">1-Strip per Page</option>
              </select>
            </div>
          </div>

          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; background: var(--bg-subtle); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border);">
            <div>
              <span style="font-size: 12px; font-weight: bold; color: var(--text-primary);">Print Song Numbers (1-90):</span>
              <div style="font-size: 10px; color: var(--text-secondary);">Unchecked: prints only song titles (no numbers)</div>
            </div>
            <input type="checkbox" id="gen-show-song-number" style="width: 18px; height: 18px; cursor: pointer; accent-color: var(--gold);">
          </div>

          <!-- Interactive Song Title Font Size Control -->
          <div style="margin-bottom: 12px; background: var(--bg-subtle); padding: 10px 12px; border-radius: 6px; border: 1px solid var(--border);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-size: 12px; font-weight: bold; color: var(--text-primary);">🔤 Song Title Font Size in Cells:</span>
              <span id="quick-font-val" style="font-size: 13px; font-weight: 800; color: var(--gold);">17.0 pt</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <button type="button" class="btn btn-outline" onclick="changeGeneratorFontSize(-1)" style="padding: 4px 12px; font-size: 16px; font-weight: 800; line-height: 1;" title="Decrease Font Size">-</button>
              <input type="range" id="gen-font-slider" min="10" max="24" step="0.5" value="17.0" oninput="onGeneratorFontSlider(this.value)" style="flex: 1; accent-color: var(--gold); cursor: pointer;">
              <button type="button" class="btn btn-outline" onclick="changeGeneratorFontSize(1)" style="padding: 4px 12px; font-size: 16px; font-weight: 800; line-height: 1;" title="Increase Font Size">+</button>
            </div>
            <div style="display: flex; gap: 4px; margin-top: 6px;">
              <button type="button" class="btn btn-outline" onclick="setGeneratorFontSize(14)" style="flex: 1; padding: 2px 4px; font-size: 10px;">14pt (Compact)</button>
              <button type="button" class="btn btn-outline" onclick="setGeneratorFontSize(17)" style="flex: 1; padding: 2px 4px; font-size: 10px; border-color: var(--gold); color: var(--gold);">17pt (Default)</button>
              <button type="button" class="btn btn-outline" onclick="setGeneratorFontSize(19)" style="flex: 1; padding: 2px 4px; font-size: 10px;">19pt (Large)</button>
              <button type="button" class="btn btn-outline" onclick="setGeneratorFontSize(22)" style="flex: 1; padding: 2px 4px; font-size: 10px;">22pt (Huge)</button>
            </div>
          </div>

          <button class="btn" style="width: 100%; padding: 12px; font-size: 13px; font-weight: bold;" onclick="generateTickets()">✨ GENERATE & ARCHIVE HOUSIE TICKETS</button>

          <div style="display: flex; gap: 8px; margin-top: 10px;">
            <button class="btn btn-gold" style="flex: 1; padding: 8px; font-size: 12px;" onclick="openLatestBatchInBrowser()">🌐 Open in Browser</button>
            <a href="/api/export/pdf" target="_blank" class="btn btn-outline" style="flex: 1; padding: 8px; font-size: 12px; text-decoration: none; justify-content: center;">📄 Export PDF</a>
          </div>
        </div>

        <div>
          <!-- Dedicated Archive Registry Table (tickets_archive/) -->
          <div class="card" style="margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div style="font-size: 14px; font-weight: 800; color: var(--gold);">📁 TICKETS ARCHIVE REPOSITORY (tickets_archive/)</div>
              <button class="btn btn-outline" style="padding: 4px 10px; font-size: 11px;" onclick="loadArchivedBatchesTable()">🔄 Refresh</button>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px; margin-bottom: 8px;">
              Batches stored systematically weeks in advance with exact layout registries for claim verification on game day.
            </div>
            <div style="max-height: 220px; overflow-y: auto;">
              <table class="data-table" id="table-archives">
                <thead><tr><th>Batch Name</th><th>Format</th><th>Sheets</th><th>Generated</th><th>Actions</th></tr></thead>
                <tbody></tbody>
              </table>
            </div>
          </div>

          <!-- Active Registered Tickets in Database Table -->
          <div class="card">
            <div style="font-size: 14px; font-weight: 800; color: var(--text-primary);">📋 REGISTERED TICKETS IN ACTIVE DATABASE</div>
            <div style="max-height: 240px; overflow-y: auto;">
              <table class="data-table" id="table-registered-tickets">
                <thead><tr><th>Ticket ID</th><th>Mode</th><th>Songs</th><th>Created</th></tr></thead>
                <tbody></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: LIVE GAME HOST -->
    <div id="tab-host" class="tab-pane">
      <div class="grid-host">
        <div>
          <!-- Header Bar with Stats & Draw Buttons -->
          <div class="card" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
              <span id="stats-text" style="font-size: 16px; font-weight: 800; color: var(--gold);">Called: 0 / 90</span>
              <span id="remaining-text" style="font-size: 12px; color: var(--text-muted); margin-left: 10px;">(90 Remaining)</span>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-gold" onclick="drawNextRandom()" style="font-size: 14px; padding: 10px 20px;">🎲 DRAW NEXT SONG</button>
              <button class="btn btn-outline" onclick="undoCall()">↩️ Undo</button>
              <button class="btn btn-outline" onclick="resetGame()" style="color: var(--crimson);">🔄 Reset</button>
            </div>
          </div>

          <!-- 90 Master Calling Grid -->
          <div class="card" style="margin-top: 14px;">
            <div style="font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">
              Master 90-Number Calling Board (Click any cell to manually call or replay)
            </div>
            <div class="board-grid" id="board-grid"></div>
          </div>

          <!-- Audio Player Bar with Real-time Scrubber -->
          <div class="audio-player-bar">
            <div class="audio-meta">
              <span id="audio-title">🎵 No track playing</span>
              <label style="font-size: 11px; color: var(--text-secondary); cursor: pointer;">
                <input type="checkbox" id="chk-autoplay" checked> Auto-play on draw
              </label>
            </div>
            <div class="scrubber-row">
              <span id="audio-time-curr" style="font-family: monospace; font-size: 12px; color: var(--text-muted);">00:00</span>
              <input type="range" id="audio-scrubber" min="0" max="100" value="0">
              <span id="audio-time-total" style="font-family: monospace; font-size: 12px; color: var(--text-muted);">00:00</span>
            </div>
            <div class="audio-controls-row">
              <button class="btn btn-gold" id="btn-play-pause" onclick="togglePlayPause()">▶ Play</button>
              <button class="btn btn-outline" onclick="replayAudio()">↺ Replay</button>
              <button class="btn btn-outline" onclick="stopAudio()">⏹ Stop</button>
              <span style="font-size: 14px; margin-left: 10px;">🔊</span>
              <input type="range" id="vol-slider" min="0" max="1" step="0.05" value="0.8" style="width: 80px;" onchange="changeVolume(this.value)">
            </div>
            <audio id="main-audio" preload="auto"></audio>
          </div>
        </div>

        <!-- Sidebar Spotlight & Feed -->
        <div>
          <div class="spotlight-card">
            <div style="font-size: 11px; font-weight: 800; color: var(--gold); letter-spacing: 2px;">CURRENT CALL</div>
            <div class="spotlight-num" id="spotlight-num">--</div>
            <div class="spotlight-title" id="spotlight-title">No call yet</div>
            <div class="spotlight-artist" id="spotlight-artist">Ready for game</div>
          </div>

          <div class="card" style="margin-top: 14px;">
            <div style="font-size: 12px; font-weight: 700; color: var(--text-secondary);">📜 RECENT CALL HISTORY</div>
            <div class="history-feed" id="history-feed"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: CLAIM VERIFIER -->
    <div id="tab-verifier" class="tab-pane">
      <!-- Game Day Batch Archive Selector -->
      <div class="card" style="margin-bottom: 14px; display: flex; align-items: center; justify-content: space-between; gap: 12px;">
        <div style="display: flex; align-items: center; gap: 10px; flex: 1;">
          <span style="font-size: 13px; font-weight: bold; color: var(--gold);">📁 Game Day Batch Archive:</span>
          <select id="ver-batch-select" onchange="onVerifierBatchChanged(this.value)" style="background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 8px 12px; border-radius: 6px; flex: 1; font-weight: bold;">
            <option value="">-- Active SQLite Database (Default) --</option>
          </select>
          <button class="btn btn-outline" style="padding: 6px 12px; font-size: 11px;" onclick="loadVerifierBatchOptions()">🔄 Refresh</button>
        </div>
        <div id="ver-batch-status" style="font-size: 12px; font-weight: bold; color: var(--emerald);">Source: Active SQLite Database</div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 380px; gap: 20px;">
        <div class="card">
          <div style="display: flex; gap: 10px; align-items: center;">
            <input type="text" id="ver-ticket-input" placeholder="Enter Ticket ID (e.g. 001, 15)" style="background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 8px 12px; border-radius: 6px; font-size: 14px; font-weight: bold; width: 220px;">
            <select id="ver-ticket-select" onchange="document.getElementById('ver-ticket-input').value = this.value; checkTicket();" style="background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 8px 12px; border-radius: 6px; flex: 1;">
              <option value="">-- Or Pick from Batch --</option>
            </select>
            <button class="btn" onclick="checkTicket()">🔍 Verify Ticket</button>
          </div>
          <div id="ticket-visual-container" style="margin-top: 16px;"></div>
        </div>

        <div class="card">
          <div style="font-size: 14px; font-weight: 800; color: var(--gold); margin-bottom: 12px;">⚖️ AUTO-VERDICT ENGINE</div>
          <div id="verdict-main-badge" style="padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 14px; background: var(--bg-subtle); color: var(--text-muted);">
            NO TICKET LOADED
          </div>
          <div id="verdict-list"></div>
          
          <div style="margin-top: 20px; border-top: 1px solid var(--border); padding-top: 14px;">
            <input type="text" id="winner-name-input" placeholder="Winner Name" style="width: 100%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-bottom: 8px;">
            <button class="btn btn-gold" style="width: 100%;" onclick="recordClaim()">🏆 Award & Record Claim</button>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: LUCKY DRAW -->
    <div id="tab-lucky" class="tab-pane">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div class="card">
          <div style="font-size: 16px; font-weight: 800; color: var(--gold); margin-bottom: 14px;">🎁 LUCKY DRAW & TIE-BREAKER</div>
          <div style="margin-bottom: 10px;">
            <label style="font-size: 12px; color: var(--text-secondary);">Prize Label:</label>
            <input type="text" id="lucky-prize" value="Tie-Breaker Bumper Prize" style="width: 100%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-top: 4px;">
          </div>
          <div style="display: flex; gap: 10px; margin-bottom: 10px;">
            <div style="flex: 2;">
              <label style="font-size: 12px; color: var(--text-secondary);">Draw Pool:</label>
              <select id="lucky-pool" style="width: 100%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-top: 4px;">
                <option value="Active Called Songs">Active Called Songs/Numbers</option>
                <option value="Registered Ticket IDs">Registered Ticket IDs</option>
                <option value="Custom Range">Custom Range (1-100)</option>
              </select>
            </div>
            <div style="flex: 1;">
              <label style="font-size: 12px; color: var(--text-secondary);">Winners:</label>
              <input type="number" id="lucky-count" value="1" min="1" max="10" style="width: 100%; background: var(--bg-subtle); color: #fff; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-top: 4px;">
            </div>
          </div>
          <button class="btn btn-gold" style="width: 100%; padding: 12px; font-size: 15px;" onclick="spinLuckyDraw()">🎰 SPIN & DRAW WINNER(S)</button>

          <!-- Animated Display Stage -->
          <div id="lucky-stage" style="margin-top: 20px; min-height: 140px; background: var(--bg-subtle); border: 2px dashed var(--gold); border-radius: 12px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 16px;">
            <div id="lucky-stage-msg" style="color: var(--text-secondary); font-size: 14px; font-weight: bold;">Ready to Draw!</div>
            <div id="lucky-winners-cards" style="display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; justify-content: center;"></div>
          </div>
        </div>

        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 14px; font-weight: 800; color: var(--gold);">📋 ROUND AUDIT LOG</div>
            <button class="btn-outline btn" onclick="clearLuckyHistory()" style="font-size: 11px;">Clear Log</button>
          </div>
          <div style="max-height: 520px; overflow-y: auto;">
            <table class="data-table" id="table-lucky-history">
              <thead><tr><th>Round</th><th>Prize</th><th>Winners</th><th>Time</th></tr></thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 5: AUDIO CATALOG -->
    <div id="tab-catalog" class="tab-pane">
      <div class="card" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 10px;">
        <div>
          <span style="font-size: 15px; font-weight: 800; color: var(--gold);">SONG CATALOG & AUDIO MAPPING</span>
          <div style="font-size: 12px; color: var(--text-secondary);">90 Songs mapped with audio in local SQLite database</div>
        </div>
        <div style="display: flex; gap: 8px;">
          <input type="file" id="file-catalog-upload" style="display: none;" onchange="uploadCatalogFile(this.files[0])">
          <button class="btn" onclick="document.getElementById('file-catalog-upload').click()">📂 Import Excel/CSV/Word/TXT</button>
          <button class="btn btn-outline" onclick="resetDefaultCatalog()">🔄 Reset 90 Bollywood Hits</button>
        </div>
      </div>

      <div class="card" style="max-height: 580px; overflow-y: auto;">
        <table class="data-table" id="table-catalog">
          <thead><tr><th>ID</th><th>Song Title</th><th>Artist / Movie</th><th>Year</th><th>Audio File</th><th>Preview</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </div>
  </main>

  <script>
    let gameState = {};
    let audioElement = document.getElementById('main-audio');
    let scrubber = document.getElementById('audio-scrubber');
    let isScrubbing = false;

    // Tab Switching
    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      if (window.event && window.event.currentTarget) {
        window.event.currentTarget.classList.add('active');
      } else {
        const btn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick')?.includes(tabId));
        if (btn) btn.classList.add('active');
      }
      const pane = document.getElementById('tab-' + tabId);
      if (pane) pane.classList.add('active');

      if (tabId === 'tickets') {
        loadArchivedBatchesTable();
        loadRegisteredTicketsTable();
      }
      if (tabId === 'verifier') {
        loadVerifierBatchOptions();
        loadRegisteredTicketsDropdown();
      }
      if (tabId === 'lucky') loadLuckyHistory();
      if (tabId === 'catalog') loadCatalogTable();
    }

    // Refresh Live State
    async function fetchState() {
      try {
        const res = await fetch('/api/state');
        gameState = await res.json();
        renderBoard();
        renderSpotlight();
        renderHistory();
      } catch (err) {
        console.error(err);
      }
    }

    // Render 90 Grid
    function renderBoard() {
      const grid = document.getElementById('board-grid');
      grid.innerHTML = '';
      const calledSet = new Set(gameState.called_numbers || []);
      const activeId = gameState.last_call ? gameState.last_call.song_id : null;

      for (let i = 1; i <= 90; i++) {
        const cell = document.createElement('div');
        cell.className = 'board-cell';
        const isCalled = calledSet.has(i);
        if (isCalled) cell.classList.add('called');
        if (i === activeId) cell.classList.add('active-playing');

        const song = (gameState.all_songs && gameState.all_songs[i]) ? gameState.all_songs[i] : {};
        const title = song.title || `Song #${i}`;

        cell.innerHTML = `
          <div class="num">${i}</div>
          <div class="sub" title="${title}">${title}</div>
        `;

        cell.onclick = () => {
          if (isCalled) {
            playAudioForSong(i);
          } else {
            if (confirm(`Manually call Song #${i} (${title})?`)) {
              manualCall(i);
            }
          }
        };

        grid.appendChild(cell);
      }

      document.getElementById('stats-text').innerText = `Called: ${gameState.called_count || 0} / 90`;
      document.getElementById('remaining-text').innerText = `(${gameState.remaining_count || 90} Remaining)`;
    }

    // Render Spotlight & Feed
    function renderSpotlight() {
      if (gameState.last_call) {
        document.getElementById('spotlight-num').innerText = String(gameState.last_call.song_id).padStart(2, '0');
        document.getElementById('spotlight-title').innerText = gameState.last_call.title || `Track #${gameState.last_call.song_id}`;
        document.getElementById('spotlight-artist').innerText = gameState.last_call.artist || '';
      } else {
        document.getElementById('spotlight-num').innerText = '--';
        document.getElementById('spotlight-title').innerText = 'No call yet';
        document.getElementById('spotlight-artist').innerText = 'Ready for game';
      }
    }

    function renderHistory() {
      const feed = document.getElementById('history-feed');
      feed.innerHTML = '';
      (gameState.history || []).forEach(item => {
        const chip = document.createElement('div');
        chip.className = 'history-chip';
        chip.innerHTML = `
          <div>
            <strong style="color: var(--gold)">#${item.call_order}</strong> &bull;
            <span>[${item.song_id}] ${item.title}</span>
          </div>
          <button class="btn btn-outline" style="padding: 2px 8px; font-size: 11px;" onclick="playAudioForSong(${item.song_id})">▶</button>
        `;
        feed.appendChild(chip);
      });
    }

    // Calling Actions
    async function drawNextRandom() {
      try {
        const res = await fetch('/api/call/random', { method: 'POST' });
        if (!res.ok) {
          const err = await res.json();
          alert(err.detail || 'Draw error');
          return;
        }
        const data = await res.json();
        await fetchState();
        if (document.getElementById('chk-autoplay').checked) {
          playAudioForSong(data.song_id);
        }
      } catch (err) {
        alert(err);
      }
    }

    async function manualCall(songId) {
      await fetch(`/api/call/${songId}`, { method: 'POST' });
      await fetchState();
      if (document.getElementById('chk-autoplay').checked) {
        playAudioForSong(songId);
      }
    }

    async function undoCall() {
      const res = await fetch('/api/call/undo', { method: 'POST' });
      if (res.ok) {
        stopAudio();
        await fetchState();
      } else {
        const err = await res.json();
        alert(err.detail);
      }
    }

    async function resetGame() {
      if (confirm('Are you sure you want to reset and start a fresh session?')) {
        stopAudio();
        await fetch('/api/reset', { method: 'POST' });
        await fetchState();
      }
    }

    // Audio Player Controls
    function playAudioForSong(songId) {
      const song = gameState.all_songs ? gameState.all_songs[songId] : {};
      document.getElementById('audio-title').innerText = `🎵 #${songId} - ${song.title || 'Track'}`;
      audioElement.src = `/api/audio/${songId}`;
      audioElement.play().catch(e => console.log('Audio autoplay prevented'));
      document.getElementById('btn-play-pause').innerText = '⏸ Pause';
    }

    function togglePlayPause() {
      if (!audioElement.src) return;
      if (audioElement.paused) {
        audioElement.play();
        document.getElementById('btn-play-pause').innerText = '⏸ Pause';
      } else {
        audioElement.pause();
        document.getElementById('btn-play-pause').innerText = '▶ Play';
      }
    }

    function replayAudio() {
      if (!audioElement.src) return;
      audioElement.currentTime = 0;
      audioElement.play();
      document.getElementById('btn-play-pause').innerText = '⏸ Pause';
    }

    function stopAudio() {
      if (!audioElement.src) return;
      audioElement.pause();
      audioElement.currentTime = 0;
      document.getElementById('btn-play-pause').innerText = '▶ Play';
    }

    function changeVolume(val) {
      audioElement.volume = parseFloat(val);
    }

    // Audio Scrubber Tracking
    audioElement.ontimeupdate = () => {
      if (!isScrubbing && audioElement.duration) {
        const curr = audioElement.currentTime;
        const total = audioElement.duration;
        scrubber.value = (curr / total) * 100;
        document.getElementById('audio-time-curr').innerText = formatTime(curr);
        document.getElementById('audio-time-total').innerText = formatTime(total);
      }
    };

    scrubber.oninput = () => {
      isScrubbing = true;
      if (audioElement.duration) {
        const target = (scrubber.value / 100) * audioElement.duration;
        document.getElementById('audio-time-curr').innerText = formatTime(target);
      }
    };

    scrubber.onchange = () => {
      isScrubbing = false;
      if (audioElement.duration) {
        audioElement.currentTime = (scrubber.value / 100) * audioElement.duration;
      }
    };

    function formatTime(sec) {
      const m = Math.floor(sec / 60);
      const s = Math.floor(sec % 60);
      return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    }

    // Template Studio & Ticket Generator
    let currentUploadedTemplateFile = null;
    let latestBatchName = 'garba_night_batch1';
    let currentTemplatePreset = 'garba_night';

    async function onPresetSelected(presetId) {
      currentTemplatePreset = presetId;
      try {
        const res = await fetch(`/api/template-presets/${presetId}`);
        if (!res.ok) return;
        const preset = await res.json();
        
        // Update thumbnail preview
        const img = document.getElementById('tpl-preview-img');
        img.src = `/api/template-image/${presetId}?t=` + Date.now();
        document.getElementById('tpl-info').innerText = 'Preset: ' + preset.name;
        document.getElementById('tpl-res-badge').innerText = `Resolution: ${preset.width_px || 2400} × ${preset.height_px || 1792} px • Direct Grid Aligned`;

        // Update calibration fields
        if (preset.strip_1) {
          document.getElementById('cal-s1-top').value = preset.strip_1.top_pct;
          document.getElementById('cal-s1-left').value = preset.strip_1.left_pct;
          document.getElementById('cal-s1-w').value = preset.strip_1.width_pct;
          document.getElementById('cal-s1-h').value = preset.strip_1.height_pct;
        }
        if (preset.strip_2) {
          document.getElementById('cal-s2-top').value = preset.strip_2.top_pct;
          document.getElementById('cal-s2-left').value = preset.strip_2.left_pct;
          document.getElementById('cal-s2-w').value = preset.strip_2.width_pct;
          document.getElementById('cal-s2-h').value = preset.strip_2.height_pct;
        }
        if (preset.font_number) {
          document.getElementById('cal-f-num-sz').value = preset.font_number.size_pt || 16;
          document.getElementById('cal-f-num-col').value = preset.font_number.color || '#800020';
        }
        if (preset.font_title) {
          const sz = preset.font_title.size_pt || 17.0;
          document.getElementById('cal-f-tit-sz').value = sz;
          document.getElementById('cal-f-tit-col').value = preset.font_title.color || '#1e293b';
          const slider = document.getElementById('gen-font-slider');
          if (slider) slider.value = sz;
          const qVal = document.getElementById('quick-font-val');
          if (qVal) qVal.innerText = parseFloat(sz).toFixed(1) + ' pt';
        }
      } catch (e) {
        console.error(e);
      }
    }

    function onGeneratorFontSlider(val) {
      val = parseFloat(val);
      document.getElementById('quick-font-val').innerText = val.toFixed(1) + ' pt';
      const calEl = document.getElementById('cal-f-tit-sz');
      if (calEl) calEl.value = val;
    }

    function changeGeneratorFontSize(delta) {
      const slider = document.getElementById('gen-font-slider');
      let current = parseFloat(slider.value) || 17.0;
      let next = Math.max(10, Math.min(24, Math.round((current + delta) * 10) / 10));
      slider.value = next;
      onGeneratorFontSlider(next);
    }

    function setGeneratorFontSize(val) {
      const slider = document.getElementById('gen-font-slider');
      slider.value = val;
      onGeneratorFontSlider(val);
    }

    function onPrintModeChanged(mode) {
      const infoEl = document.querySelector('#gen-print-mode + div');
      if (infoEl) {
        if (mode === 'direct_in_cell') {
          infoEl.innerText = '✓ Zero overlap: Numbers & songs align directly into pre-printed boxes.';
          infoEl.style.color = 'var(--emerald)';
        } else {
          infoEl.innerText = 'ℹ️ Card Mode: Renders bordered tables and banners over template.';
          infoEl.style.color = 'var(--gold)';
        }
      }
    }

    function toggleNameMode(mode) {
      const container = document.getElementById('container-names-list');
      if (mode === 'personalized') {
        container.style.display = 'block';
      } else {
        container.style.display = 'none';
      }
    }

    function toggleCalibrationPanel() {
      const panel = document.getElementById('panel-calibration');
      panel.style.display = (panel.style.display === 'none' || !panel.style.display) ? 'block' : 'none';
    }

    async function saveCurrentCalibration() {
      const calData = {
        id: "custom",
        name: "🛠️ Custom Calibrated Preset",
        print_mode: document.getElementById('gen-print-mode').value,
        strip_1: {
          top_pct: parseFloat(document.getElementById('cal-s1-top').value),
          left_pct: parseFloat(document.getElementById('cal-s1-left').value),
          width_pct: parseFloat(document.getElementById('cal-s1-w').value),
          height_pct: parseFloat(document.getElementById('cal-s1-h').value)
        },
        strip_2: {
          top_pct: parseFloat(document.getElementById('cal-s2-top').value),
          left_pct: parseFloat(document.getElementById('cal-s2-left').value),
          width_pct: parseFloat(document.getElementById('cal-s2-w').value),
          height_pct: parseFloat(document.getElementById('cal-s2-h').value)
        },
        font_number: {
          size_pt: parseFloat(document.getElementById('cal-f-num-sz').value),
          weight: 900,
          color: document.getElementById('cal-f-num-col').value
        },
        font_title: {
          size_pt: parseFloat(document.getElementById('cal-f-tit-sz').value),
          weight: 700,
          color: document.getElementById('cal-f-tit-col').value
        }
      };

      await fetch('/api/template-presets/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(calData)
      });
      alert('Custom calibration preset saved!');
      document.getElementById('gen-preset-select').value = 'custom';
    }

    function previewSelectedTemplate(event) {
      const file = event.target.files[0];
      if (!file) return;
      currentUploadedTemplateFile = file;
      document.getElementById('tpl-info').innerText = 'Selected: ' + file.name;
      document.getElementById('gen-preset-select').value = 'custom';
      const reader = new FileReader();
      reader.onload = function(e) {
        const img = document.getElementById('tpl-preview-img');
        img.src = e.target.result;
        const tempImg = new Image();
        tempImg.onload = function() {
          document.getElementById('tpl-res-badge').innerText = `Resolution: ${this.naturalWidth} × ${this.naturalHeight} px`;
        };
        tempImg.src = e.target.result;
      };
      reader.readAsDataURL(file);
    }

    async function generateTickets() {
      const batchInput = document.getElementById('gen-batch-name');
      const batchName = (batchInput ? batchInput.value.trim() : '') || 'garba_night_batch1';
      const count = document.getElementById('gen-count').value || 100;
      const mode = document.getElementById('gen-mode').value || '2-strip';
      const presetId = document.getElementById('gen-preset-select').value || 'garba_night';
      const printMode = document.getElementById('gen-print-mode').value || 'direct_in_cell';
      const nameMode = document.getElementById('gen-name-mode').value || 'blank';
      const namesText = (nameMode === 'personalized') ? (document.getElementById('gen-names-text').value || '') : '';

      // Pack active calibration
      const calibrationObj = {
        print_mode: printMode,
        strip_1: {
          top_pct: parseFloat(document.getElementById('cal-s1-top')?.value || 14.45),
          left_pct: parseFloat(document.getElementById('cal-s1-left')?.value || 2.0),
          width_pct: parseFloat(document.getElementById('cal-s1-w')?.value || 96.0),
          height_pct: parseFloat(document.getElementById('cal-s1-h')?.value || 28.07)
        },
        strip_2: {
          top_pct: parseFloat(document.getElementById('cal-s2-top')?.value || 60.49),
          left_pct: parseFloat(document.getElementById('cal-s2-left')?.value || 2.0),
          width_pct: parseFloat(document.getElementById('cal-s2-w')?.value || 96.0),
          height_pct: parseFloat(document.getElementById('cal-s2-h')?.value || 28.18)
        },
        font_number: {
          size_pt: parseFloat(document.getElementById('cal-f-num-sz')?.value || 16),
          weight: 900,
          color: document.getElementById('cal-f-num-col')?.value || '#800020'
        },
        font_title: {
          size_pt: parseFloat(document.getElementById('gen-font-slider')?.value || document.getElementById('cal-f-tit-sz')?.value || 17.0),
          weight: 800,
          color: document.getElementById('cal-f-tit-col')?.value || '#1e293b'
        }
      };
      const showSongNumber = document.getElementById('gen-show-song-number')?.checked || false;
      calibrationObj.show_song_number = showSongNumber;

      const formData = new FormData();
      formData.append('batch_name', batchName);
      formData.append('count', count);
      formData.append('mode', mode);
      formData.append('preset_id', presetId);
      formData.append('print_mode', printMode);
      formData.append('show_song_number', showSongNumber ? 'true' : 'false');
      formData.append('calibration_json', JSON.stringify(calibrationObj));
      if (namesText) {
        formData.append('participants_text', namesText);
      }
      if (currentUploadedTemplateFile) {
        formData.append('template_file', currentUploadedTemplateFile);
      }

      const btn = window.event ? window.event.currentTarget : document.querySelector("button[onclick='generateTickets()']");
      const origText = btn ? btn.innerText : '';
      if (btn) {
        btn.disabled = true;
        btn.innerText = '⏳ Generating In-Cell Sheets...';
      }

      try {
        const res = await fetch('/api/generate-tickets', { method: 'POST', body: formData });
        if (!res.ok) {
          const err = await res.json();
          alert('Generation Error: ' + (err.detail || 'Failed to generate'));
          return;
        }
        const data = await res.json();
        latestBatchName = data.batch_name || batchName;
        alert(`🎉 Successfully generated & archived ${count} tickets directly in cells into tickets_archive/${latestBatchName}.html!`);
        loadArchivedBatchesTable();
        loadRegisteredTicketsTable();
        loadVerifierBatchOptions();
      } catch (err) {
        alert('Error generating tickets: ' + err);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerText = origText;
        }
      }
    }

    function openLatestBatchInBrowser() {
      const batchInput = document.getElementById('gen-batch-name');
      const batch = (batchInput ? batchInput.value.trim() : '') || latestBatchName;
      window.open(`/archive/${encodeURIComponent(batch)}`, '_blank');
    }

    async function loadArchivedBatchesTable() {
      try {
        const res = await fetch('/api/archives');
        const archives = await res.json();
        const tbody = document.querySelector('#table-archives tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!archives || archives.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No archived batches found yet</td></tr>';
          return;
        }
        archives.forEach(a => {
          tbody.innerHTML += `
            <tr>
              <td><strong style="color:var(--gold);">${a.batch_name}</strong></td>
              <td>${a.format_mode || '2-strip'}</td>
              <td>${a.total_sheets || a.total_tickets || '--'} Sheets</td>
              <td style="font-size:11px; color:var(--text-secondary);">${a.generated_at || ''}</td>
              <td>
                <a href="/archive/${encodeURIComponent(a.batch_name)}" target="_blank" class="btn btn-outline" style="padding:2px 8px; font-size:11px; text-decoration:none;">🌐 View HTML</a>
              </td>
            </tr>
          `;
        });
      } catch (err) {
        console.error('Failed to load archives', err);
      }
    }

    async function loadRegisteredTicketsTable() {
      const res = await fetch('/api/tickets');
      const tickets = await res.json();
      const tbody = document.querySelector('#table-registered-tickets tbody');
      if (!tbody) return;
      tbody.innerHTML = '';
      tickets.forEach(t => {
        const numSongs = t.strips.reduce((acc, strip) => acc + strip.flat().filter(x => x > 0).length, 0);
        tbody.innerHTML += `
          <tr>
            <td><strong>#${t.ticket_id}</strong></td>
            <td>${t.mode}</td>
            <td>${numSongs} Songs</td>
            <td>${t.created_at || ''}</td>
          </tr>
        `;
      });
    }

    // Claim Verifier & Game Day Batch Archive Selector
    async function loadVerifierBatchOptions() {
      try {
        const res = await fetch('/api/archives');
        const archives = await res.json();
        const sel = document.getElementById('ver-batch-select');
        if (!sel) return;
        const currentVal = sel.value;
        sel.innerHTML = '<option value="">-- Active SQLite Database (Default) --</option>';
        (archives || []).forEach(a => {
          sel.innerHTML += `<option value="${a.batch_name}">${a.batch_name} (${a.total_tickets || a.total_sheets || '?'} tickets)</option>`;
        });
        if (currentVal) sel.value = currentVal;
      } catch (e) {
        console.error('Error loading verifier batches:', e);
      }
    }

    async function onVerifierBatchChanged(batchName) {
      const statusEl = document.getElementById('ver-batch-status');
      const selTickets = document.getElementById('ver-ticket-select');
      selTickets.innerHTML = '<option value="">-- Or Pick from Batch --</option>';

      if (!batchName) {
        statusEl.innerText = 'Source: Active SQLite Database';
        statusEl.style.color = 'var(--emerald)';
        loadRegisteredTicketsDropdown();
        return;
      }

      statusEl.innerText = `Loading batch: ${batchName}...`;
      statusEl.style.color = 'var(--gold)';

      try {
        const res = await fetch(`/api/archive/${encodeURIComponent(batchName)}/registry`);
        if (!res.ok) {
          alert(`Could not load registry for batch: ${batchName}`);
          return;
        }
        const registryData = await res.json();
        const ticketsList = registryData.tickets || [];
        ticketsList.forEach(t => {
          selTickets.innerHTML += `<option value="${t.ticket_id}">Ticket #${t.ticket_id} (${t.mode || '2-strip'})</option>`;
        });
        statusEl.innerText = `Loaded Batch: ${batchName} (${ticketsList.length} tickets)`;
        statusEl.style.color = 'var(--gold)';
      } catch (e) {
        alert('Failed to load registry: ' + e);
      }
    }

    async function loadRegisteredTicketsDropdown() {
      const res = await fetch('/api/tickets');
      const tickets = await res.json();
      const sel = document.getElementById('ver-ticket-select');
      sel.innerHTML = '<option value="">-- Or Pick from Batch --</option>';
      tickets.forEach(t => {
        sel.innerHTML += `<option value="${t.ticket_id}">Ticket #${t.ticket_id} (${t.mode})</option>`;
      });
    }

    async function checkTicket() {
      const tid = document.getElementById('ver-ticket-input').value.trim();
      if (!tid) return;

      const selectedBatch = document.getElementById('ver-batch-select')?.value;
      let url = `/api/ticket/${tid}`;
      if (selectedBatch) {
        url = `/api/archive/${encodeURIComponent(selectedBatch)}/ticket/${tid}`;
      }

      const res = await fetch(url);
      if (!res.ok) {
        alert(`Ticket #${tid} not found in ${selectedBatch ? 'batch ' + selectedBatch : 'active database'}!`);
        return;
      }
      const data = await res.json();
      renderVisualTicket(data);
    }

    function renderVisualTicket(data) {
      const container = document.getElementById('ticket-visual-container');
      const batchLabel = data.batch_name ? ` &bull; Batch: ${data.batch_name}` : '';
      container.innerHTML = `<h4>Ticket #${data.ticket.ticket_id} (${data.ticket.mode || '2-strip'})${batchLabel}</h4>`;
      const calledSet = new Set(data.called_numbers || []);

      data.ticket.strips.forEach((strip, sIdx) => {
        let tableHtml = `<div style="margin-top:12px;"><strong style="color:var(--gold)">Strip ${sIdx + 1}</strong>`;
        tableHtml += '<table class="ticket-table-preview"><tbody>';
        strip.forEach(row => {
          tableHtml += '<tr>';
          row.forEach(cell => {
            if (cell > 0) {
              const isCalled = calledSet.has(cell);
              const song = data.all_songs[cell] || {};
              tableHtml += `
                <td class="ticket-cell-filled ${isCalled ? 'marked' : ''}">
                  <div><strong>${cell}</strong></div>
                  <div style="font-size:9px;">${song.title || ''}</div>
                </td>
              `;
            } else {
              tableHtml += '<td class="ticket-cell-blank"></td>';
            }
          });
          tableHtml += '</tr>';
        });
        tableHtml += '</tbody></table></div>';
        container.innerHTML += tableHtml;
      });

      // Render Verdict Badges
      const vBadge = document.getElementById('verdict-main-badge');
      if (data.is_valid_claim) {
        vBadge.innerText = '✅ AT LEAST 1 PRIZE CLAIM VALID!';
        vBadge.style.background = 'var(--emerald)';
        vBadge.style.color = '#fff';
      } else {
        vBadge.innerText = '❌ BOGEY / NO CLAIM VALID YET';
        vBadge.style.background = 'var(--crimson)';
        vBadge.style.color = '#fff';
      }

      const vList = document.getElementById('verdict-list');
      vList.innerHTML = '';
      data.verdicts.forEach(v => {
        const item = document.createElement('div');
        item.className = 'verdict-badge ' + (v.complete ? 'complete' : '');
        item.innerHTML = `
          <span>${v.complete ? '✓' : '⏳'} ${v.pattern}</span>
          <span style="font-size:11px; color:var(--text-muted);">${v.detail}</span>
        `;
        vList.appendChild(item);
      });
    }

    async function recordClaim() {
      const tid = document.getElementById('ver-ticket-input').value.trim();
      const winner = document.getElementById('winner-name-input').value.trim();
      if (!tid) return alert('No ticket verified');
      const formData = new FormData();
      formData.append('ticket_id', tid);
      formData.append('winner_name', winner || 'Anonymous');
      await fetch('/api/claim/record', { method: 'POST', body: formData });
      alert(`Winning claim recorded for Ticket #${tid}!`);
    }

    // Lucky Draw
    async function spinLuckyDraw() {
      const prize = document.getElementById('lucky-prize').value;
      const pool = document.getElementById('lucky-pool').value;
      const count = document.getElementById('lucky-count').value;
      const formData = new FormData();
      formData.append('prize_name', prize);
      formData.append('pool_type', pool);
      formData.append('winner_count', count);

      document.getElementById('lucky-stage-msg').innerText = '🎰 Spinning Roulette...';
      const res = await fetch('/api/lucky-draw', { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail);
        return;
      }
      const data = await res.json();
      document.getElementById('lucky-stage-msg').innerText = '🎉 WINNER(S) DRAWN!';
      document.getElementById('lucky-stage-msg').style.color = 'var(--emerald)';

      const cardsContainer = document.getElementById('lucky-winners-cards');
      cardsContainer.innerHTML = '';
      data.winners.forEach((w, idx) => {
        cardsContainer.innerHTML += `
          <div style="background:var(--bg-card); border:2px solid var(--emerald); padding:12px 18px; border-radius:8px; text-align:center;">
            <div style="font-size:10px; color:var(--gold); font-weight:bold;">WINNER #${idx+1}</div>
            <div style="font-size:20px; font-weight:800; color:#fff; margin-top:4px;">${w}</div>
          </div>
        `;
      });
      loadLuckyHistory();
    }

    async function loadLuckyHistory() {
      const res = await fetch('/api/lucky-draw/history');
      const records = await res.json();
      const tbody = document.querySelector('#table-lucky-history tbody');
      tbody.innerHTML = '';
      records.forEach(r => {
        tbody.innerHTML += `
          <tr>
            <td>#${r.round_id}</td>
            <td>${r.prize_name}</td>
            <td><strong>${(r.winner_ids || []).join(', ')}</strong></td>
            <td>${r.drawn_at || ''}</td>
          </tr>
        `;
      });
    }

    async function clearLuckyHistory() {
      if (confirm('Clear lucky draw audit records?')) {
        await fetch('/api/lucky-draw/history', { method: 'DELETE' });
        loadLuckyHistory();
      }
    }

    // Catalog & Upload
    async function loadCatalogTable() {
      const res = await fetch('/api/catalog');
      const songs = await res.json();
      const tbody = document.querySelector('#table-catalog tbody');
      tbody.innerHTML = '';
      songs.forEach(s => {
        const hasAudio = s.has_audio;
        tbody.innerHTML += `
          <tr>
            <td><strong>#${s.id}</strong></td>
            <td>${s.title}</td>
            <td>${s.artist || ''}</td>
            <td>${s.year || ''}</td>
            <td><span style="color:${hasAudio ? 'var(--emerald)' : 'var(--crimson)'}">${hasAudio ? '✓ Mapped' : '⚠️ Missing'}</span></td>
            <td><button class="btn btn-outline" style="padding:2px 8px; font-size:11px;" onclick="playAudioForSong(${s.id})">▶ Play</button></td>
          </tr>
        `;
      });
    }

    async function uploadCatalogFile(file) {
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/catalog/import', { method: 'POST', body: formData });
      const data = await res.json();
      alert(`Imported ${data.imported} songs, mapped ${data.mapped} audio files!`);
      loadCatalogTable();
      fetchState();
    }

    async function resetDefaultCatalog() {
      if (confirm('Reset catalog to 90 evergreen Bollywood hits?')) {
        await fetch('/api/catalog/seed-default', { method: 'POST' });
        loadCatalogTable();
        fetchState();
      }
    }

    // Expose functions globally to window
    window.switchTab = switchTab;
    window.drawNextRandom = drawNextRandom;
    window.drawNextSong = drawNextRandom;
    window.manualCall = manualCall;
    window.undoCall = undoCall;
    window.resetGame = resetGame;
    window.confirmResetGame = resetGame;
    window.togglePlayPause = togglePlayPause;
    window.replayAudio = replayAudio;
    window.replaySong = replayAudio;
    window.stopAudio = stopAudio;
    window.stopSong = stopAudio;
    window.checkTicket = checkTicket;
    window.verifyTicket = checkTicket;
    window.verifyTicketSearch = checkTicket;
    window.spinLuckyDraw = spinLuckyDraw;
    window.spinSlotMachine = spinLuckyDraw;
    window.generateTickets = generateTickets;
    window.recordClaim = recordClaim;
    window.clearLuckyHistory = clearLuckyHistory;
    window.uploadCatalogFile = uploadCatalogFile;
    window.resetDefaultCatalog = resetDefaultCatalog;

    // Init
    fetchState();
    loadArchivedBatchesTable();
    loadRegisteredTicketsTable();
    loadVerifierBatchOptions();
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    print("Starting Musical Tambola Localhost Server at http://localhost:8000")
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=False)
