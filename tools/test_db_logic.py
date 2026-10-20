r"""Check delete_order and book_shipment against a throwaway database copy.

Usage:  python -I tools\test_db_logic.py <settings.ini pointing at a throwaway copy>
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402

db.SETTINGS = Path(sys.argv[1])


def count(sql, params=()):
    con = db.connect()
    cur = con.cursor()
    cur.execute(sql, params)
    n = cur.fetchone()[0]
    con.close()
    return n


# 1. delete_order removes exactly one of several identical rows.
con = db.connect()
cur = con.cursor()
cur.execute(
    "select first 1 pratka, datkniz, vidobr, iznos, sifprim, sifsmet, count(*) from promet "
    "group by 1,2,3,4,5,6 having count(*) > 1"
)
pratka, datkniz, *_ = cur.fetchone()
con.close()
day = datkniz.date()
orders = db.shipment_orders(pratka, day)
before = len(orders)
# pick an order that has an exact twin in the shipment
twin = next(o for o in orders if sum(1 for p in orders if p["_raw"] == o["_raw"]) > 1)
db.delete_order(twin)
after = len(db.shipment_orders(pratka, day))
print(f"delete: shipment {pratka}/{day} had {before} orders, now {after}")
assert after == before - 1

# 2. book_shipment on an unbooked shipment.
con = db.connect()
cur = con.cursor()
cur.execute(
    "select first 1 p.pratka, p.datkniz, p.sifsmet, count(*), sum(p.iznos) from promet p "
    "where not exists (select 1 from kniz k where k.pratka=p.pratka and k.datkniz=p.datkniz) "
    "group by 1,2,3 order by 2 desc"
)
pratka, datkniz, sifsmet, n, total = cur.fetchone()
con.close()
valuta = dt.date(2026, 10, 22)
knizbr = db.book_shipment(pratka, datkniz.date(), sifsmet.strip(), dt.date(2026, 10, 21), valuta, False, n, total)
print(f"book: shipment {pratka}/{datkniz.date()} ({n} orders, {total:.2f}) -> knizbr {knizbr}")
assert db.get_booking(pratka, valuta)["knizbr"] == knizbr
assert count("select count(*) from promet where pratka=? and datkniz=? and brkniz=?", (pratka, valuta, knizbr)) == n
second = db.book_shipment(pratka, valuta, sifsmet.strip(), valuta, dt.date(2026, 10, 23), True, n, total)
assert int(second[:4]) == int(knizbr[:4]) + 1 and second[4:] == knizbr[4:]
assert count("select count(*) from promet where pratka=? and dosdat=?", (pratka, "20261023")) == n
print(f"book again (Плата=Д): knizbr {second}, dosdat set on {n} orders")
print("all checks passed")
