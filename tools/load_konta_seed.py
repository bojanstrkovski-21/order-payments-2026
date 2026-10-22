r"""One-time load of the ministry konta (extracted/ministry/konta_seed.csv) into the NEW app's database.

Adds the konta that are missing and never touches an existing one (the old program's own konta stay as they are).
Refuses to run against the old program's database (D:\nalozi).

Usage:  python -X utf8 tools\load_konta_seed.py [settings.ini]      (default: app\settings.ini)
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

db.ensure_schema()   # adds KONTA.OPISFULL when missing
with open(ROOT / "extracted" / "ministry" / "konta_seed.csv", encoding="utf8", newline="") as f:
    rows = [{"konto": r["konto"], "opis": r["opis30"], "opisfull": r["opis_full"]}
            for r in csv.DictReader(f, delimiter=";")]
added, existing = db.load_konta(rows)
print(f"{db._database_path()}: {added} konta added, {existing} already there (left unchanged)")
