"""
Root alias for generator/generate_housie_tickets.py
"""
import sys
from pathlib import Path

# Add generator directory to path
gen_dir = Path(__file__).resolve().parent / "generator"
if str(gen_dir) not in sys.path:
    sys.path.insert(0, str(gen_dir))

from generator.generate_housie_tickets import (
    generate_housie_tickets,
    HousieTicketGenerator,
    image_to_base64_uri
)

if __name__ == "__main__":
    from generator.generate_housie_tickets import main as _main
    # If run directly as script
    import subprocess
    subprocess.run([sys.executable, str(gen_dir / "generate_housie_tickets.py")] + sys.argv[1:])
