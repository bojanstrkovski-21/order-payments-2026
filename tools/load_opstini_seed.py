r"""One-time load of the ministry municipalities (extracted/ministry/opstini.csv) into the NEW app's database.

Adds the opstini that are missing and never touches an existing one.

Usage:  PYTHONPATH=app python -X utf8 tools\load_opstini_seed.py [settings.ini]
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import db  # noqa: E402

db.SETTINGS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "app" / "settings.ini"
db.ensure_schema()
seed_path = ROOT / "extracted" / "ministry" / "opstini.csv"
with seed_path.open(encoding="utf-8-sig", newline="") as f:
    rows = [{"sifra": r["sifra"].strip(), "naziv": r["naziv"].strip()}
            for r in csv.DictReader(f, delimiter=";")]
added, existing = db.load_opstini(rows)
print(f"opstini: {added} added, {existing} already there (left unchanged)")
