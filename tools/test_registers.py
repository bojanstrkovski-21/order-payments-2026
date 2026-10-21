r"""Check ШИФРАРНИК — ГЕНЕРАЛИИ and СМЕТКИ (with the new fields) against a throwaway copy.

Usage:  python -I tools\test_registers.py <settings.ini pointing at a throwaway copy>
"""
import sys
from pathlib import Path

import wx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402
import registers  # noqa: E402
import reports  # noqa: E402
import shipment  # noqa: E402

db.SETTINGS = Path(sys.argv[1])


def check(name, condition):
    print(("OK   " if condition else "FAIL ") + name)
    assert condition, name


# --- guard and schema ---------------------------------------------------------------------------------------
real_path = db._database_path
db._database_path = lambda: Path(r"d:\NALOZI\novnal.fdb")
try:
    db.ensure_schema()
    check("ensure_schema refuses the old program's database", False)
except RuntimeError:
    check("ensure_schema refuses the old program's database", True)
db._database_path = real_path

added = db.ensure_schema()
check("new columns added once", set(added) <= {"INIT.EMBS", "INIT.EMAIL1", "INIT.EMAIL2", "INIT.EMAIL_FIN",
                                               "SMETKI.NAZIV"})
check("ensure_schema is idempotent", db.ensure_schema() == [])

# --- ГЕНЕРАЛИИ ----------------------------------------------------------------------------------------------
before = db.get_init()
check("institution row exists", bool(before.get("naziv")))
new = dict(before)
new.update(embs="1234567", email1="info@example.org", email2="school@example.org", email_fin="finance@example.org",
           adresa="ул. Тест бр. 1")
for key in ("naziv", "adresa", "mesto", "telefon", "edb", "trezsmet", "trzkan", "trzkodkor", "trzinskod"):
    new[key] = (new.get(key) or "").strip()
db.save_init({k: new[k] for k in ("naziv", "adresa", "mesto", "telefon", "edb", "trezsmet", "trzkan", "trzkodkor",
                                  "trzinskod", "embs", "email1", "email2", "email_fin")})
after = db.get_init()
check("ЕМБС saved", after["embs"] == "1234567")
check("e-mails saved as typed", (after["email1"], after["email2"], after["email_fin"]) ==
      ("info@example.org", "school@example.org", "finance@example.org"))
check("Cyrillic address round-trips through MAC C", after["adresa"].strip() == "ул. Тест бр. 1")
check("other fields unchanged", after["edb"].strip() == before["edb"].strip()
      and after["trezsmet"].strip() == before["trezsmet"].strip())
con = db.connect()
cur = con.cursor()
cur.execute("select count(*) from init")
check("still one institution row", db._first(cur)[0] == 1)
con.close()

app = wx.App()
frame = wx.Frame(None)
dlg = registers.GeneralDialog(frame)
check("ГЕНЕРАЛИИ shows ЕМБС", dlg.f["embs"].GetValue() == "1234567")
check("ГЕНЕРАЛИИ shows the finance e-mail", dlg.f["email_fin"].GetValue() == "finance@example.org")
v = dlg.values()
check("valid values pass", dlg.check(v) is None)
check("wrong e-mail refused", dlg.check(dict(v, email2="no-at-sign")) is not None)
check("letters in ЕДБ refused", dlg.check(dict(v, edb="40A")) is not None)
check("empty name refused", dlg.check(dict(v, naziv="")) is not None)
dlg.Destroy()

# --- СМЕТКИ -------------------------------------------------------------------------------------------------
accounts = db.list_accounts()
check("accounts listed in code order", [a["sifra"] for a in accounts] == sorted(a["sifra"] for a in accounts))
used = next(a for a in accounts if db.account_in_use(a["sifra"]))
free_code = next(f"{n:02d}" for n in range(99, 0, -1) if all(a["sifra"] != f"{n:02d}" for a in accounts))

db.save_account({"sifra": free_code, "naziv": "Тест сметка џепарац", "smetbukor": "999999999999999",
                 "podsbukor": "888888888888888"})
acc = db.get_account(free_code)
check("new account with a Cyrillic name", acc and acc["naziv"].strip() == "Тест сметка џепарац")
try:
    db.save_account({"sifra": free_code, "naziv": "", "smetbukor": "1", "podsbukor": ""})
    check("duplicate code refused", False)
except ValueError:
    check("duplicate code refused", True)
db.save_account({"sifra": free_code, "naziv": "Преименувана", "smetbukor": "999999999999999", "podsbukor": ""},
                old_code=free_code)
check("account renamed", db.get_account(free_code)["naziv"].strip() == "Преименувана")
try:
    db.save_account(dict(used, sifra=free_code), old_code=used["sifra"])
    check("code change of a used account refused", False)
except ValueError:
    check("code change of a used account refused", True)
check("used account untouched", db.get_account(used["sifra"]) is not None)

db.save_account({"sifra": used["sifra"], "naziv": "Главна сметка", "smetbukor": used["smetbukor"],
                 "podsbukor": used["podsbukor"]}, old_code=used["sifra"])
check("label shows account and name", shipment.account_label(db.get_account(used["sifra"])).endswith("—  Главна сметка"))
ctx = {"init": db.get_init(), "account": db.get_account(used["sifra"]), "pratka": "1",
       "day": __import__("datetime").date(2026, 10, 1)}
report = reports._shipment_report(ctx, "НАЛОЗИ")
check("print-out shows the account name", any("Главна сметка" in str(v) for _, v in report.details))

check("used account counted", db.account_in_use(used["sifra"]) > 0)
check("new account not in use", db.account_in_use(free_code) == 0)
db.delete_account(free_code)
check("account deleted", db.get_account(free_code) is None)

dlg = registers.AccountsDialog(frame)
check("register lists every account", dlg.list.GetItemCount() == len(db.list_accounts()))
dlg.search.SetValue("Главна")
dlg.fill()
check("search by name", dlg.list.GetItemCount() == 1 and dlg.selected()["sifra"] == used["sifra"])
r = dlg.report()
check("account list report has all rows", len(r.rows) == len(dlg.accounts))
pdf = Path(sys.argv[1]).with_name("accounts_test.pdf")
reports.to_pdf(r, pdf)
check("account list PDF written", pdf.stat().st_size > 1000)
html = reports.to_html(r)
check("account list HTML has the name", "Главна сметка" in html)
pdf.unlink()
dlg.Destroy()
frame.Destroy()

print("all checks passed")
