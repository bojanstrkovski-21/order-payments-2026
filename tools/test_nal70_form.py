r"""Check Налог 70 (public duties / payments between budget users) by driving the form
without showing it, against a throwaway database copy.

Usage:  python -I tools\test_nal70_form.py <settings.ini pointing at a throwaway copy>
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
pratka, day = "6", dt.date(2026, 12, 28)  # an empty test shipment
init = db.get_init()
context = {"pratka": pratka, "day": day, "account": db.get_account("02"), "init": init}
partner = next(p for p in db.search_partners("") if p["sifra"] and p["ziro"])

dlg = orders.Nal70Dialog(frame, context)
check("layout: tax number shown, no Трезорска сметка, no Повикување",
      dlg.f_edb.GetValue() == init["edb"] and dlg.f_trezsmet is None and dlg.f_povik is None)
check("Образец 70 and title for public duties", dlg.f_obrazec.GetValue() == "70" and "ЈАВНИ ДАВАЧКИ" in dlg.TITLE)
dlg.f_code.SetValue(partner["sifra"])
dlg.f_raskon.SetValue("423711")
dlg.f_prog.SetValue("a1")
dlg.f_cel1.SetValue("персонален данок")
dlg.f_uplsmet.SetValue("840abc1234567")
dlg.f_prihsif.SetValue("711111")
dlg.f_progprim.SetValue("b2")
dlg.f_denari.SetValue("12.000")
orders._set_date(dlg.f_datdos, dt.date(2026, 12, 31))
messages.clear()
check("complete form saves without messages", dlg.insert() and messages == [])
check("form shows the recipient's budget account", dlg.f_smprim.GetValue() == partner["ziro"])
dlg.Destroy()

o = db.shipment_orders(pratka, day)[0]
check("stored as type 70, nacin 3, rbr 000001", (o["vidobr"], o["nacin"], o["rbr"]) == ("70", "3", "000001"))
check("Уплатна сметка -> podsmetprim (upper case)", o["podsmetprim"] == "840ABC1234567")
check("Приходна шифра -> konprim, programa -> progprim", (o["konprim"], o["progprim"]) == ("711111", "B2"))
check("company tax number saved in edb", o["edb"] == init["edb"])
check("Трезорска сметка still saved in smetzadolz", o["smetzadolz"] == init["trezsmet"])
check("no Повикување written", not o["povik1"])
check("recipient = partner account, name, place",
      (o["smetprim"], o["nazprim1"], o["nazprim2"]) == (partner["ziro"], partner["naziv"], partner["mesto"]))
check("amount 12.000,00, due date 20261231", abs(o["iznos"] - 12000) < 1e-9 and o["dosdat"] == "20261231")

# Editing: the form shows the stored values; АЖУРИРАЈ does not touch edb.
dlg = orders.Nal70Dialog(frame, context, order=o)
check("edit form shows Уплатна сметка, Приходна шифра, програма",
      (dlg.f_uplsmet.GetValue(), dlg.f_prihsif.GetValue(), dlg.f_progprim.GetValue()) == ("840ABC1234567", "711111", "B2"))
dlg.f_prihsif.SetValue("722222")
edited = dlg.values()
check("update values leave edb alone", edited is not None and "edb" not in edited)
db.update_order(o, edited)
dlg.Destroy()
after = db.shipment_orders(pratka, day)[0]
check("edited Приходна шифра saved, edb unchanged", after["konprim"] == "722222" and after["edb"] == init["edb"])

frame.Destroy()
print("all checks passed")
