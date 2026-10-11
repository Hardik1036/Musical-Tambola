"""
Musical Tambola - Configuration & Application Constants
"""
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
SONGS_DIR = ASSETS_DIR / "songs"
BRANDING_DIR = ASSETS_DIR / "branding"
GENERATOR_DIR = BASE_DIR / "generator"
DATABASE_PATH = BASE_DIR / "tambola.db"
TICKETS_JSON_PATH = BASE_DIR / "tickets.json"
TICKETS_ARCHIVE_DIR = BASE_DIR / "tickets_archive"
TICKETS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# Audio Settings
SUPPORTED_AUDIO_EXTENSIONS = [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"]
DEFAULT_SAMPLE_RATE = 44100

# Tambola Specifications
TOTAL_NUMBERS = 90
STRIP_ROWS = 3
STRIP_COLS = 9
NUMBERS_PER_ROW = 5
NUMBERS_PER_STRIP = 15
TWO_STRIP_NUMBERS = 30

# UI Theme Color Palette (Royal Dark Slate, Crimson & Gold)
THEME = {
    "bg_dark": "#0B1120",
    "bg_card": "#1E293B",
    "bg_card_hover": "#334155",
    "bg_subtle": "#0F172A",
    "border": "#334155",
    "border_highlight": "#F59E0B",
    
    "crimson": "#E11D48",
    "crimson_hover": "#BE123C",
    "crimson_light": "#FFE4E6",
    
    "gold": "#F59E0B",
    "gold_hover": "#D97706",
    "gold_light": "#FEF3C7",
    
    "emerald": "#10B981",
    "emerald_hover": "#059669",
    "emerald_light": "#D1FAE5",
    
    "blue": "#3B82F6",
    "blue_hover": "#2563EB",
    
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    "text_dark": "#0F172A",
    
    "number_uncalled_bg": "#1E293B",
    "number_uncalled_text": "#94A3B8",
    "number_called_bg": "#BE123C",
    "number_called_text": "#FFFFFF",
    "number_active_bg": "#F59E0B",
    "number_active_text": "#0F172A",
}

# 90 Default Indian & Bollywood Evergreen Hit Songs for instant catalog seeding
DEFAULT_90_SONGS = [
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
    (35, "Kala Chashma", "Baar Baar Dekho", "2016"),
    (36, "Kar Gayi Chull", "Kapoor & Sons", "2016"),
    (37, "London Thumakda", "Queen", "2014"),
    (38, "Nashe Si Chadh Gayi", "Befikre", "2016"),
    (39, "Apna Bana Le", "Bhediya", "2022"),
    (40, "Kesariya", "Brahmastra", "2022"),
    (41, "Jhoome Jo Pathaan", "Pathaan", "2023"),
    (42, "Chaleya", "Jawan", "2023"),
    (43, "Tauba Tauba", "Bad Newz", "2024"),
    (44, "Ilahi", "Yeh Jawaani Hai Deewani", "2013"),
    (45, "Subhanallah", "Yeh Jawaani Hai Deewani", "2013"),
    (46, "Khairiyat", "Chhichhore", "2019"),
    (47, "Shayad", "Love Aaj Kal", "2020"),
    (48, "Agar Tum Saath Ho", "Tamasha", "2015"),
    (49, "Matargashti", "Tamasha", "2015"),
    (50, "Sooraj Dooba Hain", "Roy", "2015"),
    (51, "Jeena Jeena", "Badlapur", "2015"),
    (52, "Mast Magan", "2 States", "2014"),
    (53, "Mitwa", "Kabhi Alvida Naa Kehna", "2006"),
    (54, "Main Agar Kahoon", "Om Shanti Om", "2007"),
    (55, "Deewangi Deewangi", "Om Shanti Om", "2007"),
    (56, "Dard-e-Dil", "Karz", "1980"),
    (57, "Inteha Ho Gayi", "Sharaabi", "1984"),
    (58, "Pyaar Hua Iqraar Hua", "Shree 420", "1955"),
    (59, "Awaara Hoon", "Awaara", "1951"),
    (60, "O Saathi Re", "Muqaddar Ka Sikandar", "1978"),
    (61, "Khaike Paan Banaraswala", "Don", "1978"),
    (62, "Yeh Jawani Hai Deewani", "Jawani Diwani", "1972"),
    (63, "Bachna Ae Haseeno", "Hum Kisise Kum Naheen", "1977"),
    (64, "Kya Hua Tera Wada", "Hum Kisise Kum Naheen", "1977"),
    (65, "Chura Liya Hai Tumne", "Yaadon Ki Baaraat", "1973"),
    (66, "Yaadon Ki Baaraat", "Yaadon Ki Baaraat", "1973"),
    (67, "Dum Bhar Jo Udhar", "Awaara", "1951"),
    (68, "Bole Chudiyan", "K3G", "2001"),
    (69, "Suraj Hua Maddham", "K3G", "2001"),
    (70, "Say Shava Shava", "K3G", "2001"),
    (71, "Maahi Ve", "Kal Ho Naa Ho", "2003"),
    (72, "Pretty Woman", "Kal Ho Naa Ho", "2003"),
    (73, "Dus Bahane", "Dus", "2005"),
    (74, "Right Here Right Now", "Bluffmaster", "2005"),
    (75, "Mauja Hi Mauja", "Jab We Met", "2007"),
    (76, "Tum Se Hi", "Jab We Met", "2007"),
    (77, "Nagada Sang Dhol", "Ram-Leela", "2013"),
    (78, "Dhol Baje", "Hum Dil De Chuke Sanam", "1999"),
    (79, "Nimbooda Nimbooda", "Hum Dil De Chuke Sanam", "1999"),
    (80, "Chand Chupa Badal Mein", "Hum Dil De Chuke Sanam", "1999"),
    (81, "Woh Ladki Hai Kahan", "Dil Chahta Hai", "2001"),
    (82, "Koi Kahe Kehta Rahe", "Dil Chahta Hai", "2001"),
    (83, "Desi Girl", "Dostana", "2008"),
    (84, "Maa Da Laadla", "Dostana", "2008"),
    (85, "Uff Teri Adaa", "Karthik Calling Karthik", "2010"),
    (86, "Pee Loon", "Once Upon a Time in Mumbaai", "2010"),
    (87, "Subah Hone Na De", "Desi Boyz", "2011"),
    (88, "Balam Pichkari", "Yeh Jawaani Hai Deewani", "2013"),
    (89, "Dilliwali Girlfriend", "Yeh Jawaani Hai Deewani", "2013"),
    (90, "Lut Gaye", "Lut Gaye Single", "2021")
]
