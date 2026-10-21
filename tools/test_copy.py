r"""Check КОПИРАЊЕ (copy a booked shipment into the current one) against a throwaway copy.

Usage:  python -I tools\test_copy.py <settings.ini pointing at a throwaway copy>
"""
import datetime as dt
import sys
from pathlib import Path

import wx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402
import shipment  # noqa: E402

db.SETTINGS = Path(sys.argv[1])


def check(name, condition):
    print(("OK   " if condition else "FAIL ") + name)
    assert condition, name


con = db.connect()
cur = con.cursor()
# Target: an unbooked shipment of account 02 that already has orders.
cur.execute("select first 1 p.pratka, p.datkniz from promet p where p.sifsmet='02' and not exists "
            "(select 1 from kniz k where k.pratka=p.pratka and k.datkniz=p.datkniz) group by 1,2 order by 2 desc")
dst_pratka, dst_day = db._first(cur)
dst_day = dst_day.date()
# Source: a booked shipment of account 02 with several orders and no 62 orders.
cur.execute("select k.pratka, k.datkniz, count(p.rbr), sum(case when p.vidobr='62' then 1 else 0 end) "
            "from kniz k join promet p on p.pratka=k.pratka and p.datkniz=k.datkniz "
            "where k.sifsmet='02' group by 1,2 order by 2 desc")
src_pratka, src_day = next((r[0], r[1].date()) for r in cur.fetchall() if 3 <= r[2] <= 30 and r[3] == 0)
# A booked shipment of another account, for the refusal.
cur.execute("select first 1 pratka, datkniz from kniz where sifsmet<>'02' order by datkniz desc")
other_pratka, other_day = db._first(cur)
con.close()

source = db.shipment_orders(src_pratka, src_day)
before = db.shipment_orders(dst_pratka, dst_day)
last = max(int(o["rbr"]) for o in before)

app = wx.App()
frame = wx.Frame(None)
panel = shipment.ShipmentPanel(frame)
panel.account = db.get_account("02")
panel.shipment = (dst_pratka, dst_day)
panel.orders = before
check("refused: shipment that does not exist", panel.copy_refusal("Z", dt.date(2001, 1, 1)) == "НЕ ПОСТОИ ТАКВА ПРАТКА!")
check("refused: shipment of another account", panel.copy_refusal(other_pratka.strip(), other_day.date()) == "ОВАА ПРАТКА Е ОД ДРУГА СМЕТКА")
check("allowed: booked shipment of the same account", panel.copy_refusal(src_pratka.strip(), src_day) is None)
frame.Destroy()

today = dt.date(2026, 10, 21)
copied = db.copy_shipment(src_pratka.strip(), src_day, dst_pratka, dst_day, today=today)
after = db.shipment_orders(dst_pratka, dst_day)
new = after[len(before):]
check(f"all {len(source)} source orders copied", copied == len(source) == len(new))
# (Old data can already contain duplicate numbers — e.g. old 73 orders all numbered 000001 — so only the copies are checked.)
check("copies numbered after the existing orders, unique and not clashing with existing numbers",
      [int(o["rbr"]) for o in new] == list(range(last + 1, last + 1 + copied))
      and not {o["rbr"] for o in new} & {o["rbr"] for o in before})
check("copies belong to the current shipment, valuta = shipment date",
      all(o["pratka"] == dst_pratka.strip() and o["datkniz"].date() == dst_day and o["valdat"].date() == dst_day for o in new))
check("submission date = today, booking number cleared", all(o["datpod"].date() == today and not o["brkniz"] for o in new))
same = ("vidobr", "sifprim", "smetprim", "nazprim1", "nazprim2", "celdoz1", "celdoz2", "konzadolz", "progzadolz",
        "podsmetprim", "konprim", "progprim", "povik1", "edb", "nacin", "sifsmet", "smetzadolz", "podsmetzadolz")
check("everything else copied unchanged (amount, recipient, codes, texts)",
      all(all(n[k] == s[k] for k in same) and abs(n["iznos"] - s["iznos"]) < 1e-9 for n, s in zip(new, source)))
check("source shipment unchanged", len(db.shipment_orders(src_pratka.strip(), src_day)) == len(source))
print("all checks passed")
