r"""Check СНИМИ (the *.TDB treasury file) with invented data and a booked shipment of a throwaway copy.
The byte-for-byte check against the old program's real files is tools\compare_tdb.py (files stay local).

Usage:  python -I tools\test_tdb.py <settings.ini pointing at a throwaway copy>
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402
import tdb  # noqa: E402

db.SETTINGS = Path(sys.argv[1])


def check(name, condition):
    print(("OK   " if condition else "FAIL ") + name)
    assert condition, name


init = {"trzkodkor": "TDB", "trzinskod": "TRZ"}
booking = {"pratka": "1", "ddd": "20251212", "vkupnal": 1, "iznos": 5198.0}
row = {"slvid": "2", "smetzadolz": "100000000000001", "podsmetzadolz": "703000000000002", "konzadolz": "480190",
       "progzadolz": "N2", "celdoz1": "kupuvawe na oprema", "celdoz2": "", "sifra": "000000", "iznos": 5198.0,
       "smetprim": "210000000000003", "nazprim1": "Primer DOOEL", "nazprim2": "Skopje", "podsmetprim": None,
       "konprim": None, "progprim": None, "povik1": "f-ra 1/25", "vidobr": "60", "nacin": "2", "edb": None,
       "dosdat": "20251231"}

head = tdb.header(init, booking)
check("header: 41 characters + 250 spaces = 291", len(head) == 291 and head.rstrip() == head[:41] and head[41:] == " " * 250)
check("header core", head[:41] == "1TDBTRZ202512121000001+000000000005198,00")

line = tdb.order_line(1, row)
expected = ("2" + "000001" + "100000000000001" + "703000000000002" + "480190" + "N2"
            + "kupuvawe na oprema".ljust(70) + "000000" + "+" + "000000000005198,00" + "000210000000000003"
            + ("Primer DOOEL".ljust(35) + " " + "Skopje").ljust(70) + " " * 15 + "000000" + "00"
            + "f-ra 1/25".ljust(24) + "60" + "2" + "0" * 13 + "20251231")
check("order line: exact layout, 299 characters", line == expected and len(line) == 299)
check("empty due date: line ends after the tax number (291 characters)",
      len(tdb.order_line(1, {**row, "dosdat": ""})) == 291)
check("negative amount: '-' sign, absolute value", tdb.order_line(1, {**row, "iznos": -12.5})[121:140] == "-000000000000012,50")
check("purpose: line 1 padded to 35, space, line 2, cut to 70",
      tdb.order_line(1, {**row, "celdoz2": "vtor red " * 6})[45:115] == ("kupuvawe na oprema".ljust(35) + " " + "vtor red " * 6)[:70])
check("purpose line 1 empty (NULL): line 2 starts right after one space",
      tdb.order_line(1, {**row, "celdoz1": None, "celdoz2": "abc"})[45:50] == " abc ")
# CHAR columns are read with their trailing spaces, so only an empty (NULL) code becomes zeros.
check("empty codes become zeros: konprim 6, progprim 2, edb 13", line[243:251] == "0" * 8 and line[278:291] == "0" * 13)
filled = tdb.order_line(1, {**row, "konprim": "723019", "progprim": "A1", "edb": "4000000000001"})
check("filled codes are written as stored", filled[243:251] == "723019A1" and filled[278:291] == "4000000000001")
check("Unicode Cyrillic is written in the MAC C encoding (USB file stays MAC C)",
      tdb.order_line(1, {**row, "celdoz1": "плаќање за жиро"})[45:60] == "pla}awe za `iro")
check("file name: N + ddmmyy + shipment + treasury code", tdb.file_name("6", dt.date(2026, 10, 5), "TDB") == "N0510266.TDB")
data = tdb.build(init, booking, [row])
check("file: ASCII, every line ends CRLF", data.isascii() and data.count(b"\r\n") == 2 and data.endswith(b"\r\n"))

# A shipment booked in the throwaway database.
con = db.connect()
cur = con.cursor()
cur.execute("select first 1 p.pratka, p.datkniz, p.sifsmet, count(*), sum(p.iznos) from promet p where not exists "
            "(select 1 from kniz k where k.pratka=p.pratka and k.datkniz=p.datkniz) group by 1,2,3 order by 2 desc")
pratka, day, sifsmet, n, total = db._first(cur)
con.close()
valuta = dt.date(2026, 12, 21)
db.book_shipment(pratka, day.date(), sifsmet.strip(), dt.date(2026, 12, 18), valuta, False, n, total)
orders = db.shipment_orders(pratka, valuta)
init_db = db.get_init()
data = tdb.build(init_db, db.get_booking(pratka, valuta), [o["_raw"] for o in orders])
lines = data.decode("ascii").split("\r\n")[:-1]
check(f"booked shipment: header + {n} order lines", len(lines) == n + 1)
check("header: date = new value date, shipment, count", lines[0][7:22] == f"{valuta:%Y%m%d}{pratka.strip()}{n:06d}")
check("header total = sum of the order lines",
      abs(float(lines[0][23:41].replace(",", ".")) - sum(float(l[122:140].replace(",", ".")) for l in lines[1:])) < 0.005)
check("order lines numbered 1..n, 291 or 299 characters",
      [int(l[1:7]) for l in lines[1:]] == list(range(1, n + 1)) and all(len(l) in (291, 299) for l in lines[1:]))
print("all checks passed")
