r"""One-time load of the ministry payment accounts (extracted/ministry/uplatni_seed.csv)
into the NEW app's database.

Adds the uplatni that are missing and never touches an existing one.
Refuses to run against the old program's database (D:\nalozi).

Usage:  PYTHONPATH=app python -X utf8 tools\load_uplatni_seed.py [settings.ini]
        (use PYTHONPATH=app, not -I: the script imports the app modules)
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import db  # noqa: E402

if len(sys.argv) > 1:
    db.SETTINGS = Path(sys.argv[1])
if str(db._database_path()).lower() == str(db.LIVE_DATABASE).lower():
    sys.exit("Refusing to write to the old program's database.")

db.ensure_schema()
with open(ROOT / "extracted" / "ministry" / "uplatni_seed.csv", encoding="utf-8", newline="") as f:
    rows = [
        {
            "banka": (r.get("banka") or "").strip(),
            "kod": (r.get("kod") or "").strip(),
            "naziv": (r.get("naziv") or "").strip(),
            "konto": (r.get("konto") or "").strip(),
        }
        for r in csv.DictReader(f, delimiter=";")
    ]
added, existing = db.load_uplatni(rows)
print(f"{db._database_path()}: {added} uplatni added, {existing} already there (left unchanged)")
