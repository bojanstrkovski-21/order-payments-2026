r"""Check Налог 76 (Treasury ↔ Fund's treasury) by driving the form without showing it, against a throwaway copy.

Usage:  python -I tools\test_nal76_form.py <settings.ini pointing at a throwaway copy>
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
pratka, day = "2", dt.date(2026, 12, 23)  # an empty test shipment
init = db.get_init()
account = db.get_account("02")
context = {"pratka": pratka, "day": day, "account": account, "init": init}
partner = next(p for p in db.search_partners("") if p["sifra"] and p["ziro"])

dlg = orders.Nal76Dialog(frame, context)
check("layout: transaction account, tax number, Fund account shown; no Повикување",
      dlg.f_trezsmet.GetValue() == init["trezsmet"] and dlg.f_edb.GetValue() == init["edb"]
      and dlg.f_fund.GetValue() == "100000000066005" and dlg.f_povik is None)
dlg.f_code.SetValue(partner["sifra"])
dlg.f_raskon.SetValue("464111")
dlg.f_prog.SetValue("a1")
dlg.f_cel1.SetValue("трансфер до фондот")
dlg.f_prihsif.SetValue("741111")
dlg.f_progprim.SetValue("b1")
dlg.f_denari.SetValue("25.000")
orders._set_date(dlg.f_datdos, dt.date(2026, 12, 31))
messages.clear()
check("complete form saves without messages", dlg.insert() and messages == [])
check("form shows the partner's budget account", dlg.f_smprim.GetValue() == partner["ziro"])
dlg.Destroy()

o = db.shipment_orders(pratka, day)[0]
check("stored as type 76, nacin 3", (o["vidobr"], o["nacin"]) == ("76", "3"))
check("recipient account = fixed Fund account", o["smetprim"] == "100000000066005")
check("partner budget account in podsmetprim", o["podsmetprim"] == partner["ziro"])
check("приходно конто -> konprim, потпрограма -> progprim", (o["konprim"], o["progprim"]) == ("741111", "B1"))
check("payer: treasury account, budget account, tax number",
      (o["smetzadolz"], o["podsmetzadolz"], o["edb"]) == (init["trezsmet"], account["smetbukor"], init["edb"]))
check("recipient name and place from the partner", (o["nazprim1"], o["nazprim2"]) == (partner["naziv"], partner["mesto"]))
check("order in its shipment, valuta from the form", o["datkniz"].date() == day and o["valdat"] is not None)

dlg = orders.Nal76Dialog(frame, context, order=o)
check("edit form shows the partner budget account (not the Fund account)", dlg.f_smprim.GetValue() == partner["ziro"])
check("edit form shows приходно конто and потпрограма", (dlg.f_prihsif.GetValue(), dlg.f_progprim.GetValue()) == ("741111", "B1"))
dlg.f_denari.SetValue("26.000")
edited = dlg.values()
check("update keeps Fund account and partner account, leaves edb alone",
      edited["smetprim"] == "100000000066005" and edited["podsmetprim"] == partner["ziro"] and "edb" not in edited)
db.update_order(o, edited)
dlg.Destroy()
check("edited amount saved", abs(db.shipment_orders(pratka, day)[0]["iznos"] - 26000) < 1e-9)

frame.Destroy()
print("all checks passed")
