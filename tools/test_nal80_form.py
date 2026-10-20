r"""Check Налог 80 (cash payout) by driving the form without showing it, against a throwaway copy.

Usage:  python -I tools\test_nal80_form.py <settings.ini pointing at a throwaway copy>
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
pratka, day = "5", dt.date(2026, 12, 27)  # an empty test shipment
init = db.get_init()
context = {"pratka": pratka, "day": day, "account": db.get_account("02"), "init": init}
person = next(p for p in db.search_partners("") if p["sifra"] and p["brlk"] and p["embg"])

dlg = orders.Nal80Dialog(frame, context)
check("layout: ID card + EMBG, no recipient account, no Повикување",
      dlg.f_brlk is not None and dlg.f_embg is not None and dlg.f_smprim is None and dlg.f_povik is None)
check("title and purpose label for cash payout",
      dlg.TITLE == "БАРАЊЕ ЗА ИСПЛАТА НА ГОТОВИНА" and dlg.PURPOSE_LABEL == "Цел на исплата")
dlg.f_code.SetValue(person["sifra"])
dlg.f_raskon.SetValue("424110")
dlg.f_prog.SetValue("a1")
dlg.f_cel1.SetValue("патни трошоци")
dlg.f_denari.SetValue("3.000")
orders._set_date(dlg.f_datdos, dt.date(2026, 12, 31))
messages.clear()
check("complete form saves without messages", dlg.insert() and messages == [])
check("form shows ID card and EMBG", (dlg.f_brlk.GetValue(), dlg.f_embg.GetValue()) == (person["brlk"], person["embg"]))
dlg.Destroy()

o = db.shipment_orders(pratka, day)[0]
check("stored as type 80, nacin 3", (o["vidobr"], o["nacin"]) == ("80", "3"))
check("recipient account = treasury account (as all 61 real orders)", o["smetprim"] == init["trezsmet"] == o["smetzadolz"])
check("EMBG in edb, ID card in povik1", (o["edb"], o["povik1"]) == (person["embg"], person["brlk"]))
raw_brlk = db.connect().cursor()
raw_brlk.execute("select brlk from partneri where sifra=?", (person["sifra"],))
check("stored ID card bytes identical to the register", o["_raw"]["povik1"].rstrip() == raw_brlk.fetchone()[0].rstrip())
check("recipient name and place", (o["nazprim1"], o["nazprim2"]) == (person["naziv"], person["mesto"]))
check("amount 3.000,00, due date 20261231", abs(o["iznos"] - 3000) < 1e-9 and o["dosdat"] == "20261231")

dlg = orders.Nal80Dialog(frame, context, order=o)
check("edit form shows stored ID card and EMBG", (dlg.f_brlk.GetValue(), dlg.f_embg.GetValue()) == (person["brlk"], person["embg"]))
dlg.f_denari.SetValue("3.500")
edited = dlg.values()
db.update_order(o, edited)
dlg.Destroy()
after = db.shipment_orders(pratka, day)[0]
check("edit saves 3.500,00 and keeps EMBG / ID card",
      abs(after["iznos"] - 3500) < 1e-9 and (after["edb"], after["povik1"]) == (person["embg"], person["brlk"]))

frame.Destroy()
print("all checks passed")
