r"""Check Налог 73 (non-cash refund) by driving the form without showing it, against a throwaway copy.

Usage:  python -I tools\test_nal73_form.py <settings.ini pointing at a throwaway copy>
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
pratka, day = "3", dt.date(2026, 12, 25)  # an empty test shipment
init = db.get_init()
account = db.get_account("02")
context = {"pratka": pratka, "day": day, "account": account, "init": init}

dlg = orders.Nal73Dialog(frame, context)
check("new form: value date = next working day, submission today", orders._get_date(dlg.f_valdat) == orders.workdays.next_working_day(dt.date.today())
      and orders._get_date(dlg.f_datpod) == dt.date.today())
check("payer block shows treasury and budget accounts", (dlg.f_trezsmet.GetValue(), dlg.f_smetbukor.GetValue())
      == (init["trezsmet"], account["smetbukor"]))
messages.clear()
orders._set_date(dlg.f_datdos, dt.date(2027, 1, 5))
check("empty required fields are refused with ВНЕСЕТЕ ВРЕДНОСТИ", dlg.values() is None and messages == ["ВНЕСЕТЕ ВРЕДНОСТИ"])
dlg.f_prihsif.SetValue("723011")
dlg.f_progprim.SetValue("n2")
dlg.f_cel1.SetValue("поврат на погрешно уплатени сред.")
dlg.f_smprim.SetValue("210000000000001")
dlg.f_nazprim1.SetValue("Петар Петровски")
dlg.f_nazprim2.SetValue("Битола")
dlg.f_edb.SetValue("4000000000001")
dlg.f_smbukorprim.SetValue("100000000000002")
dlg.f_rasprihkon.SetValue("723019")
dlg.f_prograsprim.SetValue("a1")
dlg.f_denari.SetValue("500")
orders._set_date(dlg.f_valdat, dt.date(2026, 12, 27))
messages.clear()
check("complete form saves without messages", dlg.insert() and messages == [])
dlg.Destroy()

saved = db.shipment_orders(pratka, day)
check("the order is in its shipment (datkniz = shipment date; the old app filed it under the value date)",
      len(saved) == 1 and saved[0]["datkniz"].date() == day)
o = saved[0]
check("value date from the form in valdat", o["valdat"].date() == dt.date(2026, 12, 27))
check("type 73, nacin 2, no recipient code", (o["vidobr"], o["nacin"], o["sifprim"]) == ("73", "2", ""))
check("payer codes: приходно конто -> konzadolz, потпрограма -> progzadolz (upper)", (o["konzadolz"], o["progzadolz"]) == ("723011", "N2"))
check("payer accounts: treasury -> smetzadolz, budget account -> podsmetzadolz",
      (o["smetzadolz"], o["podsmetzadolz"]) == (init["trezsmet"], account["smetbukor"]))
check("recipient typed in: account, name, place, tax number",
      (o["smetprim"], o["nazprim1"], o["nazprim2"], o["edb"]) == ("210000000000001", "Петар Петровски", "Битола", "4000000000001"))
check("recipient budget block: podsmetprim, konprim, progprim",
      (o["podsmetprim"], o["konprim"], o["progprim"]) == ("100000000000002", "723019", "A1"))
check("amount 500,00 and due date 20270105", abs(o["iznos"] - 500) < 1e-9 and o["dosdat"] == "20270105")

dlg = orders.Nal73Dialog(frame, context, order=o)
check("edit form shows the typed recipient", (dlg.f_nazprim1.GetValue(), dlg.f_edb.GetValue()) == ("Петар Петровски", "4000000000001"))
dlg.f_denari.SetValue("650")
edited = dlg.values()
db.update_order(o, edited)
dlg.Destroy()
after = db.shipment_orders(pratka, day)
check("edit saves 650,00 and the order stays in its shipment", len(after) == 1 and abs(after[0]["iznos"] - 650) < 1e-9)

frame.Destroy()
print("all checks passed")
