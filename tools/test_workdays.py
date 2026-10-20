r"""Check the default Датум на валута: next working day after Датум на поднесување.

Usage:  python -I tools\test_workdays.py <settings.ini pointing at a throwaway copy>
"""
import datetime as dt
import sys
import tempfile
from pathlib import Path

import wx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402
import orders  # noqa: E402
import workdays  # noqa: E402

db.SETTINGS = Path(sys.argv[1])
D = dt.date
nwd = workdays.next_working_day


def check(name, condition):
    print(("OK   " if condition else "FAIL ") + name)
    assert condition, name


# Weekends.
check("Monday -> Tuesday", nwd(D(2026, 10, 19)) == D(2026, 10, 20))
check("Friday -> Monday", nwd(D(2026, 10, 16)) == D(2026, 10, 19))
check("Saturday -> Monday", nwd(D(2026, 10, 17)) == D(2026, 10, 19))
check("Sunday -> Monday", nwd(D(2026, 10, 18)) == D(2026, 10, 19))

# The user's 2026 list: every non-working weekday of 2026.
expected_2026 = {D(2026, m, d) for d, m in [
    (1, 1), (6, 1), (7, 1), (31, 12),                 # Нова Година, Бадник, Божик, Стара Година
    (20, 3),                                          # Рамазан Бајрам (holidays.txt)
    (10, 4), (13, 4), (29, 5),                        # Велики Петок, Велигден Monday, Духовден (calculated)
    (1, 5), (25, 5), (3, 8), (28, 8), (8, 9), (12, 10), (23, 10), (8, 12),  # incl. Mondays after Sunday holidays
]}
actual_2026 = {d for d in workdays.non_working_days(2026) if d.year == 2026 and d.weekday() < 5}
check("2026: exactly the non-working weekdays of the user's list", actual_2026 == expected_2026)
check("2026: Водици 19.01 is a working day", workdays.is_working_day(D(2026, 1, 19)))
check("2026: Курбан Бајрам 27.05 is a working day", workdays.is_working_day(D(2026, 5, 27)))
check("Велигден calculated: 12.04.2026, 02.05.2027, 20.04.2025", [workdays.orthodox_easter(y) for y in (2026, 2027, 2025)]
      == [D(2026, 4, 12), D(2027, 5, 2), D(2025, 4, 20)])
check("2027 calculated: Велики Петок 30.04, Велигден Monday 03.05, Духовден 18.06",
      set(workdays.easter_holidays(2027)) == {D(2027, 4, 30), D(2027, 5, 3), D(2027, 6, 18)})

# Examples of the default value date.
check("Thursday 09.04.2026 -> Tuesday 14.04 (Велики Петок, weekend, Велигден Monday)", nwd(D(2026, 4, 9)) == D(2026, 4, 14))
check("Thursday 28.05.2026 -> Monday 01.06 (Духовден 29.05)", nwd(D(2026, 5, 28)) == D(2026, 6, 1))
check("Thursday 27.08.2026 -> Monday 31.08 (Голема Богородица 28.08)", nwd(D(2026, 8, 27)) == D(2026, 8, 31))
check("Friday 22.05.2026 -> Tuesday 26.05 (24.05 Sunday holiday -> Monday 25.05 off)", nwd(D(2026, 5, 22)) == D(2026, 5, 26))
check("Thursday 19.03.2026 -> Monday 23.03 (Рамазан Бајрам 20.03)", nwd(D(2026, 3, 19)) == D(2026, 3, 23))
check("Wednesday 30.12.2026 -> Monday 04.01.2027 (31.12, 01.01, weekend)", nwd(D(2026, 12, 30)) == D(2027, 1, 4))
check("Tuesday 05.01.2027 -> Friday 08.01.2027 (Бадник 06.01, Божик 07.01)", nwd(D(2027, 1, 5)) == D(2027, 1, 8))
check("Friday 29.12.2028 -> Tuesday 02.01.2029 (31.12 on Sunday, Monday 01.01 off)", nwd(D(2028, 12, 29)) == D(2029, 1, 2))

# holidays.txt: Рамазан Бајрам and extra days, checked with a temporary file.
real_file = workdays.HOLIDAYS_FILE
with tempfile.TemporaryDirectory() as tmp:
    workdays.HOLIDAYS_FILE = Path(tmp) / "holidays.txt"
    check("without the file Рамазан Бајрам is unknown: Thursday 19.03.2026 -> Friday 20.03", nwd(D(2026, 3, 19)) == D(2026, 3, 20))
    workdays.HOLIDAYS_FILE.write_text("# test\n20.03.2026   # Рамазан Бајрам\n\n", encoding="utf-8")
    check("listed day skipped: Thursday 19.03.2026 -> Monday 23.03", nwd(D(2026, 3, 19)) == D(2026, 3, 23))
    workdays.HOLIDAYS_FILE.write_text("07.03.2027\n", encoding="utf-8")  # a Sunday
    check("listed day on a Sunday makes Monday non-working: Friday 05.03.2027 -> Tuesday 09.03",
          nwd(D(2027, 3, 5)) == D(2027, 3, 9))
    workdays.HOLIDAYS_FILE.write_text("23/10/2026\n", encoding="utf-8")
    try:
        workdays.listed_days()
        check("a wrongly written date is reported", False)
    except ValueError as error:
        check("a wrongly written date is reported with its line", "ред 1" in str(error))
workdays.HOLIDAYS_FILE = real_file

# The form follows the submission date until the user picks a value date.
app = wx.App()
frame = wx.Frame(None)
context = {"pratka": "2", "day": D(2026, 12, 24), "account": db.get_account("02"), "init": db.get_init()}
for form in (orders.Nal60Dialog, orders.Nal73Dialog):
    dlg = form(frame, context)
    get, put = orders._get_date, orders._set_date
    check(f"{form.VIDOBR}: new order valuta = next working day after today", get(dlg.f_valdat) == nwd(D.today()))
    put(dlg.f_datpod, D(2026, 10, 16))
    dlg.on_datpod_changed(wx.CommandEvent())
    check(f"{form.VIDOBR}: submission Friday 16.10 -> valuta Monday 19.10", get(dlg.f_valdat) == D(2026, 10, 19))
    put(dlg.f_valdat, D(2026, 10, 21))  # the user picks another value date
    put(dlg.f_datpod, D(2026, 10, 19))
    dlg.on_datpod_changed(wx.CommandEvent())
    check(f"{form.VIDOBR}: a value date chosen by the user is not overwritten", get(dlg.f_valdat) == D(2026, 10, 21))
    dlg.clear()
    check(f"{form.VIDOBR}: next order (ПОНАТАМУ) gets the default from the kept submission date",
          get(dlg.f_valdat) == D(2026, 10, 20))
    dlg.Destroy()

frame.Destroy()
print("all checks passed")
