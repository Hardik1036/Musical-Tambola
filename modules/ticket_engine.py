"""
Module 2.2: Ticket Generation Engine
Implements Housie/Tambola constraint solver for 1-Strip and 2-Strip tickets,
global song frequency balancing, SQLite/JSON registry persistence,
and high-resolution PDF and HTML multi-page export.
"""
import os
import random
import base64
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter

from jinja2 import Template
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from config import (
    TOTAL_NUMBERS, STRIP_ROWS, STRIP_COLS, NUMBERS_PER_ROW,
    NUMBERS_PER_STRIP, GENERATOR_DIR, BRANDING_DIR
)
import database

logger = logging.getLogger("tambola.ticket_engine")

# Decade boundaries for 9 columns
COLUMN_RANGES = [
    (1, 9),    # Col 0: 9 numbers
    (10, 19),  # Col 1: 10 numbers
    (20, 29),  # Col 2: 10 numbers
    (30, 39),  # Col 3: 10 numbers
    (40, 49),  # Col 4: 10 numbers
    (50, 59),  # Col 5: 10 numbers
    (60, 69),  # Col 6: 10 numbers
    (70, 79),  # Col 7: 10 numbers
    (80, 90),  # Col 8: 11 numbers
]


class TicketEngine:
    """Tambola strip generator and export manager."""

    def __init__(self):
        self.song_catalog = {s["id"]: s for s in database.get_all_songs()}
        self.frequencies = Counter()

    def refresh_catalog(self):
        self.song_catalog = {s["id"]: s for s in database.get_all_songs()}

    def _generate_valid_strip_mask(self) -> List[List[int]]:
        """Generate a 3x9 binary grid mask such that:
        - Each row has exactly 5 ones (5 numbers).
        - Each col has between 1 and 3 ones (15 ones total).
        """
        while True:
            # Random column allocation summing to 15:
            # Start with 1 in each column (9 ones)
            col_counts = [1] * STRIP_COLS
            # Distribute remaining 6 ones randomly, ensuring no col exceeds 3
            rem = NUMBERS_PER_STRIP - STRIP_COLS
            cols_avail = list(range(STRIP_COLS))
            random.shuffle(cols_avail)
            
            for _ in range(rem):
                valid_cols = [c for c in cols_avail if col_counts[c] < 3]
                if not valid_cols:
                    break
                c = random.choice(valid_cols)
                col_counts[c] += 1

            if sum(col_counts) != 15:
                continue

            # Backtracking or greedy row assignment for the 3 rows
            mask = [[0] * STRIP_COLS for _ in range(STRIP_ROWS)]
            row_counts = [0] * STRIP_ROWS
            success = True

            # Sort columns descending by count to place heavily loaded cols first
            cols_sorted = sorted(range(STRIP_COLS), key=lambda c: col_counts[c], reverse=True)

            for col in cols_sorted:
                needed = col_counts[col]
                # Available rows that currently have room (< 5)
                avail_rows = [r for r in range(STRIP_ROWS) if row_counts[r] < 5]
                if len(avail_rows) < needed:
                    success = False
                    break
                # Prefer rows with fewest items
                avail_rows.sort(key=lambda r: row_counts[r])
                chosen_rows = avail_rows[:needed]
                for r in chosen_rows:
                    mask[r][col] = 1
                    row_counts[r] += 1

            if success and row_counts == [5, 5, 5]:
                return mask

    def _sample_balanced_numbers(self, col_idx: int, count: int, exclude: set) -> List[int]:
        """Sample 'count' numbers from column's range with global frequency balancing."""
        start, end = COLUMN_RANGES[col_idx]
        candidates = [num for num in range(start, end + 1) if num not in exclude]
        if len(candidates) < count:
            raise ValueError(f"Insufficient numbers in column {col_idx} range ({start}-{end})")

        # Sort candidate pool by lowest frequency first, with randomized tie-break
        random.shuffle(candidates)
        candidates.sort(key=lambda n: self.frequencies[n])
        selected = candidates[:count]
        return sorted(selected)

    def generate_single_strip(self, exclude_songs: Optional[set] = None) -> List[List[int]]:
        """Generate one 3x9 strip (matrix of song IDs and zeros)."""
        if exclude_songs is None:
            exclude_songs = set()

        mask = self._generate_valid_strip_mask()
        strip_grid = [[0] * STRIP_COLS for _ in range(STRIP_ROWS)]

        for col in range(STRIP_COLS):
            # How many numbers needed in this column
            active_rows = [r for r in range(STRIP_ROWS) if mask[r][col] == 1]
            count = len(active_rows)
            if count == 0:
                continue

            chosen_numbers = self._sample_balanced_numbers(col, count, exclude_songs)
            # Assign in ascending order down the column
            for idx, r in enumerate(active_rows):
                num = chosen_numbers[idx]
                strip_grid[r][col] = num
                self.frequencies[num] += 1

        return strip_grid

    def generate_batch(self, count: int = 20, mode: str = "1-strip", start_id: int = 1) -> List[Dict[str, Any]]:
        """Generate a batch of tickets (1-strip or 2-strip) with frequency balancing."""
        self.refresh_catalog()
        tickets = []

        for i in range(count):
            ticket_id = f"{start_id + i:03d}"
            
            if mode == "1-strip":
                strip1 = self.generate_single_strip()
                strips = [strip1]
            elif mode == "2-strip":
                # Strip 1
                strip1 = self.generate_single_strip()
                used_in_strip1 = {cell for row in strip1 for cell in row if cell > 0}
                # Strip 2 must have zero repetition with strip 1
                strip2 = self.generate_single_strip(exclude_songs=used_in_strip1)
                strips = [strip1, strip2]
            else:
                raise ValueError(f"Unsupported mode: {mode}")

            tickets.append({
                "ticket_id": ticket_id,
                "mode": mode,
                "batch_id": f"batch_{count}_{mode}",
                "strips": strips
            })

        # Save to database and JSON
        database.save_tickets(tickets, sync_json=True)
        return tickets

    def export_html(
        self,
        tickets: List[Dict[str, Any]],
        output_file: str,
        event_title: str = "Musical Tambola Night",
        branding_image_path: Optional[str] = None
    ) -> str:
        """Render tickets using HTML template into a multi-page printable document."""
        self.refresh_catalog()
        template_path = GENERATOR_DIR / "ticket_template.html"
        with open(template_path, "r", encoding="utf-8") as f:
            template = Template(f.read())

        # Load branding image as base64 if provided
        logo_data = None
        if branding_image_path and Path(branding_image_path).exists():
            with open(branding_image_path, "rb") as img_f:
                b64 = base64.b64encode(img_f.read()).decode("utf-8")
                ext = Path(branding_image_path).suffix.replace(".", "").lower()
                logo_data = f"data:image/{ext};base64,{b64}"

        # Enrich tickets with song titles
        enriched_tickets = []
        for t in tickets:
            enriched_strips = []
            for strip in t["strips"]:
                enriched_strip = []
                for row in strip:
                    enriched_row = []
                    for sid in row:
                        if sid > 0:
                            song = self.song_catalog.get(sid, {})
                            enriched_row.append({
                                "id": sid,
                                "title": song.get("title", f"Track #{sid}"),
                                "artist": song.get("artist", "")
                            })
                        else:
                            enriched_row.append({"id": 0, "title": "", "artist": ""})
                    enriched_strip.append(enriched_row)
                enriched_strips.append(enriched_strip)

            enriched_tickets.append({
                "ticket_id": t["ticket_id"],
                "mode": t.get("mode", "1-strip"),
                "strips": enriched_strips
            })

        # Group tickets into pages (2 per page for 1-strip, 1 per page for 2-strip)
        per_page = 1 if enriched_tickets and enriched_tickets[0]["mode"] == "2-strip" else 2
        page_batches = [enriched_tickets[i:i + per_page] for i in range(0, len(enriched_tickets), per_page)]

        html_content = template.render(
            page_batches=page_batches,
            tickets=enriched_tickets,
            event_title=event_title,
            branding_logo_data=logo_data
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return output_file

    def export_pdf(
        self,
        tickets: List[Dict[str, Any]],
        output_file: str,
        event_title: str = "Musical Tambola Night",
        branding_image_path: Optional[str] = None
    ) -> str:
        """Export high-resolution printable PDF using reportlab."""
        self.refresh_catalog()
        is_2_strip = tickets and tickets[0].get("mode") == "2-strip"
        
        # Use Landscape A4 for 2-strip, Portrait A4 for 1-strip
        pagesize = landscape(A4) if is_2_strip else A4
        page_w, page_h = pagesize

        doc = SimpleDocTemplate(
            output_file,
            pagesize=pagesize,
            leftMargin=30,
            rightMargin=30,
            topMargin=30,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#BE123C"),
            alignment=1  # Centered
        )
        badge_style = ParagraphStyle(
            "Badge",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#B45309"),
            alignment=1
        )
        cell_num_style = ParagraphStyle(
            "CellNum",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=11,
            textColor=colors.HexColor("#9F1239"),
            alignment=1
        )
        cell_title_style = ParagraphStyle(
            "CellTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=7.5,
            textColor=colors.HexColor("#0F172A"),
            alignment=1
        )
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#64748B"),
            alignment=1
        )

        elements = []
        tickets_per_page = 1 if is_2_strip else 2

        for t_idx, ticket in enumerate(tickets):
            ticket_flowables = []

            # Header Banner
            header_data = [
                [
                    Paragraph(f"<b>{event_title.upper()}</b>", title_style),
                    Paragraph(f"<b>TICKET #{ticket['ticket_id']}</b>", badge_style)
                ]
            ]
            header_table = Table(header_data, colWidths=[page_w - 200, 140])
            header_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            ticket_flowables.append(header_table)
            ticket_flowables.append(Spacer(1, 4))

            # Strips
            for s_idx, strip in enumerate(ticket["strips"], start=1):
                label_text = f"Strip {s_idx}  •  5 Songs / Row  •  15 Songs Total"
                ticket_flowables.append(Paragraph(f"<font color='#BE123C'><b>{label_text}</b></font>", footer_style))
                ticket_flowables.append(Spacer(1, 2))

                # Grid Table (3x9)
                grid_data = []
                for row in strip:
                    row_cells = []
                    for sid in row:
                        if sid > 0:
                            song = self.song_catalog.get(sid, {})
                            raw_title = song.get("title", f"Track #{sid}")
                            trunc_title = (raw_title[:18] + '..') if len(raw_title) > 20 else raw_title
                            cell_p = [
                                Paragraph(f"<b>{sid}</b>", cell_num_style),
                                Paragraph(trunc_title, cell_title_style)
                            ]
                        else:
                            cell_p = ""
                        row_cells.append(cell_p)
                    grid_data.append(row_cells)

                col_w = (page_w - 70) / 9.0
                row_h = 32 if is_2_strip else 38
                grid_table = Table(grid_data, colWidths=[col_w] * 9, rowHeights=[row_h] * 3)
                
                # Apply Tambola Styling
                t_style = [
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
                    ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#0F172A")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ]
                # Shade blank cells
                for r_i, r in enumerate(strip):
                    for c_i, sid in enumerate(r):
                        if sid == 0:
                            t_style.append(("BACKGROUND", (c_i, r_i), (c_i, r_i), colors.HexColor("#F8FAFC")))
                        else:
                            t_style.append(("BACKGROUND", (c_i, r_i), (c_i, r_i), colors.HexColor("#FFFFFF")))

                grid_table.setStyle(TableStyle(t_style))
                ticket_flowables.append(grid_table)
                ticket_flowables.append(Spacer(1, 4))

            # Footer
            footer_text = "PRIZES: Early 5 • Top, Middle, Bottom Lines • Four Corners • Full House (Bumper)"
            ticket_flowables.append(Paragraph(footer_text, footer_style))
            ticket_flowables.append(Spacer(1, 14))

            elements.append(KeepTogether(ticket_flowables))

            # Page break when page is filled
            if (t_idx + 1) % tickets_per_page == 0 and (t_idx + 1) < len(tickets):
                elements.append(PageBreak())

        doc.build(elements)
        return output_file
