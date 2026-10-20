r"""Check Налог 61 (contributions to the funds) by driving the form without showing it,
against a throwaway copy. There are no real 61 orders, so the expected row follows TNAL61.dodaj.

Usage:  python -I tools\test_nal61_form.py <settings.ini pointing at a throwaway copy>
"""
import datetime as dt
import sys
from pathlib import Path

import wx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402
import orders  # noqa: E402

db.SETTINGS = Path(sys.argv[1])
messages = []
orders.ui.info = lambda parent, text: messages.append(text)


def check(name, condition):
    print(("OK   " if condition else "FAIL ") + name)
    assert condition, name


app = wx.App()
frame = wx.Frame(None)
pratka, day = "4", dt.date(2026, 12, 26)  # an empty test shipment
init = db.get_init()
context = {"pratka": pratka, "day": day, "account": db.get_account("02"), "init": init}
fund = next(p for p in db.search_partners("") if p["sifra"] and p["ziro"])

dlg = orders.Nal61Dialog(frame, context)
check("layout: Трезорска сметка, tax number and optional due date shown; no Повикување, no recipient programme",
      dlg.f_trezsmet is not None and dlg.f_edb.GetValue() == init["edb"] and dlg.f_datdos is not None
      and dlg.f_povik is None and dlg.f_progprim is None)
dlg.f_code.SetValue(fund["sifra"])
dlg.f_raskon.SetValue("401200")
dlg.f_prog.SetValue("a1")
dlg.f_cel1.SetValue("придонеси за октомври")
dlg.f_uplsmet.SetValue("840012345678901")
dlg.f_prihsif.SetValue("713111")
dlg.f_denari.SetValue("9.150")
messages.clear()
check("complete form saves without a due date", dlg.insert() and messages == [])
dlg.Destroy()

o = db.shipment_orders(pratka, day)[0]
check("stored as type 61, nacin 3", (o["vidobr"], o["nacin"]) == ("61", "3"))
check("recipient account, name, place from the partner",
      (o["smetprim"], o["nazprim1"], o["nazprim2"]) == (fund["ziro"], fund["naziv"], fund["mesto"]))
check("Уплатна сметка -> podsmetprim, Приходна шифра -> konprim", (o["podsmetprim"], o["konprim"]) == ("840012345678901", "713111"))
check("company tax number in edb, treasury account in smetzadolz", (o["edb"], o["smetzadolz"]) == (init["edb"], init["trezsmet"]))
check("no due date, no Повикување, no recipient programme written",
      o["datdos"] is None and not o["dosdat"] and not o["povik1"] and not o["progprim"])

dlg = orders.Nal61Dialog(frame, context, order=o)
dlg.f_prihsif.SetValue("713222")
orders._set_date(dlg.f_datdos, dt.date(2027, 1, 20))
edited = dlg.values()
check("update leaves edb alone", edited is not None and "edb" not in edited)
db.update_order(o, edited)
dlg.Destroy()
after = db.shipment_orders(pratka, day)[0]
check("edited Приходна шифра and the now-filled due date saved",
      after["konprim"] == "713222" and after["datdos"].date() == dt.date(2027, 1, 20) and after["dosdat"] == "20270120")

frame.Destroy()
print("all checks passed")
