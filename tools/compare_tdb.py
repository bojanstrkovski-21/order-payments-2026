r"""Compare files saved by the old program („FORMAT ZA TREZOR", *.TDB) with what app/tdb.py generates
from the database, byte for byte. Read-only; prints no personal data, only positions and field names.

Usage:  python -I tools\compare_tdb.py <list-of-tdb-paths.txt>
Uses app\settings.ini (the new app's database). Only files written by NOVNAL (header line of 291 characters).
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402
import tdb  # noqa: E402

FIELDS = [("type", 1), ("seq", 6), ("smetzadolz", 15), ("podsmetzadolz", 15), ("konzadolz", 6), ("progzadolz", 2),
          ("cel", 70), ("sifra", 6), ("sign", 1), ("iznos", 18), ("smetprim", 18), ("nazprim", 70), ("podsmetprim", 15),
          ("konprim", 6), ("progprim", 2), ("povik1", 24), ("vidobr", 2), ("nacin", 1), ("edb", 13), ("dosdat", 8)]


def field_at(pos):
    start = 0
    for name, width in FIELDS:
        if pos < start + width:
            return name
        start += width
    return "after end"


def raw_rows(sql, params):
    con = db.connect()
    try:
        cur = con.cursor()
        cur.execute(sql, params)
        names = [d[0].lower() for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]
    finally:
        con.close()


def main(list_file):
    init = raw_rows("select * from init", ())[0]
    results = {"identical": 0, "different": 0, "not in database": 0, "other producer": 0}
    for path in [p.strip() for p in Path(list_file).read_text(encoding="utf-8-sig").splitlines() if p.strip()]:
        data = Path(path).read_bytes()
        first = data.split(b"\r\n")[0]
        if len(first) != 291:
            results["other producer"] += 1
            continue
        pratka, day = first[15:16].decode("ascii"), dt.datetime.strptime(first[7:15].decode("ascii"), "%Y%m%d").date()
        booking = raw_rows("select * from kniz where pratka=? and datkniz=?", (pratka, day))
        rows = raw_rows("select * from promet where pratka=? and datkniz=? order by rbr", (pratka, day))
        name = Path(path).name
        if not booking or not rows:
            results["not in database"] += 1
            print(f"{name:16} not in the database (shipment {pratka} / {day})")
            continue
        made = tdb.build(init, booking[0], rows)
        if made == data:
            results["identical"] += 1
            print(f"{name:16} IDENTICAL ({len(data)} bytes, {len(rows)} orders)")
            continue
        results["different"] += 1
        old_lines, new_lines = data.split(b"\r\n"), made.split(b"\r\n")
        print(f"{name:16} DIFFERENT: {len(old_lines) - 1} vs {len(new_lines) - 1} lines")
        for i, (a, b) in enumerate(zip(old_lines, new_lines)):
            if a != b:
                pos = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
                where = "header" if i == 0 else f"order line {i}, field {field_at(pos)}"
                print(f"    line {i + 1}: lengths {len(a)} / {len(b)}, first difference at position {pos + 1} ({where})")
                break
    print(results)


if __name__ == "__main__":
    main(sys.argv[1])
