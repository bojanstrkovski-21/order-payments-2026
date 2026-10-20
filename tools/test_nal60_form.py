r"""Check the Налог 60 form rules (required due date, deni fixed at 00, old deni kept on edit)
by driving the form without showing it, against a throwaway database copy.

Usage:  python -I tools\test_nal60_form.py <settings.ini pointing at a throwaway copy>
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

app = wx.App()
frame = wx.Frame(None)
pratka, day = "8", dt.date(2026, 12, 30)  # an empty test shipment
context = {"pratka": pratka, "day": day, "account": db.get_account("02"), "init": db.get_init()}
partner = next(p for p in db.search_partners("") if p["sifra"] and p["ziro"])  # the register has a blank-code row


def filled_form(order=None):
    dlg = orders.Nal60Dialog(frame, context, order=order)
    if order is None:
        dlg.f_code.SetValue(partner["sifra"])
        dlg.recipient = partner
        dlg.f_raskon.SetValue("425911")
        dlg.f_prog.SetValue("n2")
        dlg.f_cel1.SetValue("плаќање по фактура")
        dlg.f_denari.SetValue("1.500")
        orders._set_date(dlg.f_datdos, dt.date(2027, 1, 15))
    return dlg


def check(name, condition):
    print(("OK   " if condition else "FAIL ") + name)
    assert condition, name


# 1. Датум на доспевање is required.
dlg = filled_form()
orders._set_date(dlg.f_datdos, None)
messages.clear()
check("empty due date is refused with ВНЕСЕТЕ ДАТУМ", dlg.values() is None and messages == ["ВНЕСЕТЕ ДАТУМ"])
dlg.Destroy()

# 2. Deni is fixed at 00 and read-only; the amount is required.
dlg = filled_form()
check("deni shows 00 and cannot be typed into", dlg.f_deni.GetValue() == "00" and not dlg.f_deni.IsEditable())
dlg.f_denari.SetValue("")
messages.clear()
check("empty amount is refused with ВНЕСЕТЕ ИЗНОС", dlg.values() is None and messages == ["ВНЕСЕТЕ ИЗНОС"])
dlg.f_denari.SetValue("0")
messages.clear()
check("zero amount is refused with ВНЕСЕТЕ ИЗНОС", dlg.values() is None and messages == ["ВНЕСЕТЕ ИЗНОС"])
dlg.Destroy()

# 3. A complete form saves the row the old app would have written.
dlg = filled_form()
messages.clear()
check("complete form saves without messages", dlg.insert() and messages == [])
dlg.Destroy()
saved = db.shipment_orders(pratka, day)
check("one order stored with rbr 000001", [o["rbr"] for o in saved] == ["000001"])
o = saved[0]
check("amount 1500,00", abs(o["iznos"] - 1500.0) < 1e-9)
check("due date stored as datdos and dosdat 20270115", o["datdos"].date() == dt.date(2027, 1, 15) and o["dosdat"] == "20270115")
check("programa upper-cased, purpose stored in MAC C",
      o["progzadolz"] == "N2" and o["_raw"]["celdoz1"].rstrip() == "pla}awe po faktura")
check("fixed columns as in the old app",
      (o["vidobr"], o["slvid"], o["nacin"], o["sifra"], o["sifsmet"]) == ("60", "2", "2", "000000", "02"))

# 4. Editing an old order with 50 deni keeps them.
values = {k: o["_raw"][k] for k in db.PROMET_COLUMNS if k in o["_raw"] and k != "rbr"}
values.update(iznos=730.5, celdoz1=o["celdoz1"])
db.insert_order(values)
old = db.shipment_orders(pratka, day)[1]
dlg = filled_form(order=old)
check("old order shows its 50 deni", dlg.f_deni.GetValue() == "50" and dlg.f_denari.GetValue() == "730")
messages.clear()
edited = dlg.values()  # what АЖУРИРАЈ saves (on_update itself ends a modal loop)
check("edit keeps 730,50", edited is not None and abs(edited["iznos"] - 730.5) < 1e-9)
db.update_order(old, edited)
dlg.Destroy()
after = db.shipment_orders(pratka, day)
check("after update: first order unchanged, second still 730,50",
      abs(after[0]["iznos"] - 1500.0) < 1e-9 and abs(after[1]["iznos"] - 730.5) < 1e-9)

frame.Destroy()
print("all checks passed")
