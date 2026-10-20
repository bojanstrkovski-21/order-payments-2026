r"""Check Налог 62 (employee payment) and the order-type mixing rules,
by driving the form without showing it, against a throwaway database copy.

Usage:  python -I tools\test_nal62_form.py <settings.ini pointing at a throwaway copy>
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


# 1. Mixing rules (old app: 62 never mixed; new app: 62 + 70 allowed).
mix = orders.mixing_error
check("62 into an empty shipment is allowed", mix("62", set()) is None)
check("62 into a shipment with 70 is allowed (new rule)", mix("62", {"70"}) is None)
check("70 into a shipment with 62 is allowed (new rule)", mix("70", {"62"}) is None)
check("62 into a shipment with 60 is refused", mix("62", {"60"}) == "ВО ОВАА ПРАТКА ИМА ДРУГИ НАЛОЗИ")
check("62 into a shipment with 70 and 80 is refused", mix("62", {"70", "80"}) == "ВО ОВАА ПРАТКА ИМА ДРУГИ НАЛОЗИ")
for other in ("60", "61", "73", "76", "80"):
    check(f"{other} into a shipment with 62 is refused", mix(other, {"62"}) == "ВО ОВАА ПРАТКА ИМА НАЛОЗИ 62")
check("60 next to 70 is allowed as before", mix("60", {"70"}) is None)

# 2. The form saves an employee payment like the old app did.
app = wx.App()
frame = wx.Frame(None)
pratka, day = "7", dt.date(2026, 12, 29)  # an empty test shipment
context = {"pratka": pratka, "day": day, "account": db.get_account("02"), "init": db.get_init()}
employee = next(p for p in db.search_employees("") if p["sifra"] and p["transak"] and p["embg"])

dlg = orders.Nal62Dialog(frame, context)
check("labels: employee code and transaction account", dlg.f_embg is not None and dlg.f_obrazec.GetValue() == "62")
dlg.f_code.SetValue("99999"[:4])
messages.clear()
check("unknown employee is refused with НЕМА ТАКОВ ВРАБОТЕН",
      dlg.values() is None and messages == ["НЕМА ТАКОВ ВРАБОТЕН"])
dlg.f_code.SetValue(employee["sifra"])
dlg.recipient = None  # looked up by code on save
dlg.f_raskon.SetValue("401110")
dlg.f_prog.SetValue("a1")
dlg.f_cel1.SetValue("плата за октомври")
dlg.f_denari.SetValue("38.250")
orders._set_date(dlg.f_datdos, dt.date(2026, 11, 10))
messages.clear()
check("complete form saves without messages", dlg.insert() and messages == [])
check("form shows the employee's account and EMBG",
      dlg.f_smprim.GetValue() == employee["transak"] and dlg.f_embg.GetValue() == employee["embg"])
dlg.Destroy()

o = db.shipment_orders(pratka, day)[0]
check("stored as type 62 with rbr 000001", (o["vidobr"], o["rbr"]) == ("62", "000001"))
check("recipient account = employee transaction account", o["smetprim"] == employee["transak"])
check("EMBG stored in edb", o["edb"] == employee["embg"])
check("recipient name and place from the employee register",
      (o["nazprim1"], o["nazprim2"]) == (employee["naziv"], employee["mesto"]))
check("amount 38.250,00 and due date 20261110", abs(o["iznos"] - 38250) < 1e-9 and o["dosdat"] == "20261110")

# 3. Editing keeps the recipient from the order and updates only that row.
dlg = orders.Nal62Dialog(frame, context, order=o)
check("edit form shows stored EMBG", dlg.f_embg.GetValue() == employee["embg"])
dlg.f_denari.SetValue("40.000")
edited = dlg.values()
db.update_order(o, edited)
dlg.Destroy()
after = db.shipment_orders(pratka, day)
check("edited amount 40.000,00, EMBG kept", abs(after[0]["iznos"] - 40000) < 1e-9 and after[0]["edb"] == employee["embg"])

frame.Destroy()
print("all checks passed")
