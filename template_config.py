"""
Template Configuration & Calibration Engine for Musical Tambola.
Supports pixel-perfect Direct In-Cell printing on pre-designed ticket templates,
custom coordinate alignment for Strip 1 & Strip 2, and participant name printing.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "templates_config.json"

DEFAULT_PRESETS: Dict[str, Dict[str, Any]] = {
    "garba_night": {
        "id": "garba_night",
        "name": "🎪 Garba Night Musical Housie (Pre-Designed Grid)",
        "template_file": "assets/branding/Garba_Night_Musical_Housie_Template.png",
        "print_mode": "direct_in_cell",  # "direct_in_cell" (transparent) or "overlay_box"
        "width_px": 2400,
        "height_px": 1792,
        "strip_1": {
            "top_pct": 14.45,
            "left_pct": 1.96,
            "width_pct": 96.04,
            "height_pct": 28.07
        },
        "strip_2": {
            "top_pct": 60.49,
            "left_pct": 1.96,
            "width_pct": 96.04,
            "height_pct": 28.18
        },
        "badge_1": {
            "enabled": True,
            "top_pct": 4.91,
            "left_pct": 7.08,
            "width_pct": 13.42,
            "height_pct": 6.25,
            "color": "#ffffff",
            "bg_color": "#7d143d",
            "format": "टिकट क्रमांक : {ticket_id}"
        },
        "badge_2": {
            "enabled": True,
            "top_pct": 51.78,
            "left_pct": 7.08,
            "width_pct": 13.42,
            "height_pct": 6.03,
            "color": "#ffffff",
            "bg_color": "#7d143d",
            "format": "टिकट क्रमांक : {ticket_id}"
        },
        "participant_name": {
            "enabled": True,
            "top_pct": 91.5,
            "left_pct": 19.2,
            "width_pct": 27.0,
            "font_size_pt": 12,
            "color": "#800020"
        },
        "participant_mobile": {
            "enabled": True,
            "top_pct": 91.5,
            "left_pct": 61.5,
            "width_pct": 27.0,
            "font_size_pt": 12,
            "color": "#800020"
        },
        "show_song_number": False,
        "font_number": {
            "size_pt": 16,
            "weight": 900,
            "color": "#800020"
        },
        "font_title": {
            "size_pt": 15.5,
            "weight": 800,
            "color": "#1e293b"
        }
    },
    "festive_gold": {
        "id": "festive_gold",
        "name": "✨ Festive Musical Housie (Gold / Crimson)",
        "template_file": "assets/branding/Festive_Musical_Housie_Template.png",
        "print_mode": "direct_in_cell",
        "width_px": 2400,
        "height_px": 1600,
        "strip_1": {
            "top_pct": 16.0,
            "left_pct": 3.5,
            "width_pct": 93.0,
            "height_pct": 27.5
        },
        "strip_2": {
            "top_pct": 59.0,
            "left_pct": 3.5,
            "width_pct": 93.0,
            "height_pct": 27.5
        },
        "badge_1": {
            "enabled": True,
            "top_pct": 7.0,
            "left_pct": 82.0,
            "width_pct": 14.0,
            "height_pct": 4.5,
            "color": "#ffffff",
            "bg_color": "#be123c",
            "format": "TICKET #{ticket_id}"
        },
        "badge_2": {
            "enabled": True,
            "top_pct": 50.0,
            "left_pct": 82.0,
            "width_pct": 14.0,
            "height_pct": 4.5,
            "color": "#ffffff",
            "bg_color": "#be123c",
            "format": "TICKET #{ticket_id}"
        },
        "participant_name": {
            "enabled": True,
            "top_pct": 92.0,
            "left_pct": 22.0,
            "width_pct": 26.0,
            "font_size_pt": 11,
            "color": "#be123c"
        },
        "participant_mobile": {
            "enabled": True,
            "top_pct": 92.0,
            "left_pct": 65.0,
            "width_pct": 24.0,
            "font_size_pt": 11,
            "color": "#be123c"
        },
        "show_song_number": False,
        "font_number": {
            "size_pt": 15,
            "weight": 900,
            "color": "#be123c"
        },
        "font_title": {
            "size_pt": 15.0,
            "weight": 800,
            "color": "#0f172a"
        }
    }
}


def load_template_configs() -> Dict[str, Dict[str, Any]]:
    """Load template configurations from file or initialize with defaults."""
    if not CONFIG_FILE.exists():
        save_template_configs(DEFAULT_PRESETS)
        return DEFAULT_PRESETS

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure defaults are merged in
            for k, v in DEFAULT_PRESETS.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return DEFAULT_PRESETS


def save_template_configs(configs: Dict[str, Dict[str, Any]]) -> None:
    """Save template configurations to JSON."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(configs, f, indent=2)


def get_template_config(preset_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve specific template configuration, defaulting to garba_night."""
    configs = load_template_configs()
    if preset_id and preset_id in configs:
        return configs[preset_id]
    return configs.get("garba_night", DEFAULT_PRESETS["garba_night"])


def save_custom_preset(preset_id: str, preset_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save or update a template preset."""
    configs = load_template_configs()
    configs[preset_id] = preset_data
    save_template_configs(configs)
    return preset_data
