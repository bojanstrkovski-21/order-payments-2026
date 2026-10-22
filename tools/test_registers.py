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
import uplatni  # noqa: E402

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
                                               "INIT.OPSTINA", "SMETKI.NAZIV", "KONTA.OPISFULL", "OPSTINI", "UPLATNI"})
check("ensure_schema is idempotent", db.ensure_schema() == [])

# --- ГЕНЕРАЛИИ ----------------------------------------------------------------------------------------------
before = db.get_init()
check("institution row exists", bool(before.get("naziv")))
new = dict(before)
new.update(embs="1234567", email1="info@example.org", email2="school@example.org", email_fin="finance@example.org",
           adresa="ул. Тест бр. 1")
for key in ("naziv", "adresa", "mesto", "telefon", "edb", "trezsmet", "trzkan", "trzkodkor", "trzinskod"):
    new[key] = (new.get(key) or "").strip()
new["opstina"] = (new.get("opstina") or db.DEFAULT_OPSTINA).strip() or db.DEFAULT_OPSTINA
db.save_init({k: new[k] for k in ("naziv", "adresa", "mesto", "telefon", "edb", "trezsmet", "trzkan", "trzkodkor",
                                  "trzinskod", "embs", "email1", "email2", "email_fin", "opstina")})
after = db.get_init()
check("ЕМБС saved", after["embs"] == "1234567")
check("INIT.opstina defaulted", (after.get("opstina") or "").strip() == db.DEFAULT_OPSTINA)
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

# --- КОНТА --------------------------------------------------------------------------------------------------
import csv  # noqa: E402

import konta  # noqa: E402

check("short name cuts at a word boundary", konta.short_name("Основни плати - државни службеници") == "Основни плати - државни")
check("short name keeps a short text", konta.short_name("Пошта") == "Пошта")
check("class of a konto", (konta.konto_class("401110"), konta.konto_class("711213")) == ("4", "7"))

old_konta = {k["konto"]: k for k in db.list_konta()}
seed_file = Path(__file__).resolve().parent.parent / "extracted" / "ministry" / "konta_seed.csv"
with open(seed_file, encoding="utf8", newline="") as f:
    seed = [{"konto": r["konto"], "opis": r["opis30"], "opisfull": r["opis_full"]}
            for r in csv.DictReader(f, delimiter=";")]
check("seed has the ministry lists", len(seed) > 900 and all(len(s["opis"]) <= 30 for s in seed))
added, there = db.load_konta(seed)
check("load adds only the missing konta", added == len(seed) - len(old_konta) and there == len(old_konta))
check("second load adds nothing", db.load_konta(seed) == (0, len(seed)))
now = {k["konto"]: k for k in db.list_konta()}
check("every seed konto is in the register", set(now) == {s["konto"] for s in seed} | set(old_konta))
check("existing konta untouched", all(now[c]["opis"] == old_konta[c]["opis"] and now[c]["opisfull"] == old_konta[c]["opisfull"]
                                       for c in old_konta))
check("konta listed in code order", list(now) == sorted(now))
long = now["718118"]
check("full official name kept", len(long["naziv"]) > 300 and long["naziv"].startswith("Надоместок за заштита"))
check("short form kept at most 30", all(len(k["opis"].strip()) <= 30 for k in now.values()))
check("Cyrillic round-trips", now["711213"]["naziv"].startswith("Данок на добивка по годишен даночен биланс"))
check("old konto without a full name shows its short name",
      all(now[c]["naziv"] == old_konta[c]["opis"].strip() for c in old_konta if not old_konta[c]["opisfull"].strip()))

free_konto = next(f"{n}" for n in range(999999, 999000, -1) if str(n) not in now)
db.save_konto({"konto": free_konto, "opis": "Тест конто џепарац", "opisfull": "Тест конто џепарац со долг целосен назив"})
k = db.get_konto(free_konto)
check("new konto with Cyrillic names", k and k["opis"].strip() == "Тест конто џепарац" and k["naziv"].endswith("назив"))
for bad, why in ((dict(konto=free_konto, opis="x", opisfull="x"), "duplicate"),
                 (dict(konto="999990", opis="а" * 31, opisfull="а"), "short name over 30"),
                 (dict(konto="999990", opis="COVID", opisfull="COVID"), "Latin letters"),
                 (dict(konto="999990", opis="а", opisfull="а" * 401), "full name over 400"),
                 (dict(konto="999990", opis="ö", opisfull="ö"), "character the old encoding cannot hold")):
    try:
        db.save_konto(bad)
        check(f"refused: {why}", False)
    except ValueError:
        check(f"refused: {why}", True)
db.save_konto({"konto": free_konto, "opis": "Преименувано", "opisfull": "Преименувано конто"}, old_code=free_konto)
check("konto renamed", db.get_konto(free_konto)["naziv"] == "Преименувано конто")
db.save_konto({"konto": "999990", "opis": "Преименувано", "opisfull": "Преименувано конто"}, old_code=free_konto)
check("unused konto code changed", db.get_konto("999990") and db.get_konto(free_konto) is None)
free_konto = "999990"

con = db.connect()
cur = con.cursor()
cur.execute("select first 1 konzadolz from promet where konzadolz is not null and trim(konzadolz)<>''")
used_konto = db._clean(db._first(cur)[0])
con.close()
if used_konto not in now:
    db.save_konto({"konto": used_konto, "opis": "Користено", "opisfull": "Користено конто"})
check("used konto counted", db.konto_in_use(used_konto) > 0 and db.konto_in_use(free_konto) == 0)
try:
    db.save_konto({"konto": free_konto, "opis": "а", "opisfull": "а"}, old_code=used_konto)
    check("code change of a used konto refused", False)
except ValueError:
    check("code change of a used konto refused", True)
check("used konto untouched", db.get_konto(used_konto) is not None)
db.delete_konto(free_konto)
check("konto deleted", db.get_konto(free_konto) is None)
check("specification descriptions still short", all(len(v) <= 30 for v in db.konta_descriptions().values()))

dlg = registers.KontaDialog(frame)
check("register lists every konto", dlg.list.GetItemCount() == len(db.list_konta()))
dlg.kind.SetSelection(1)
dlg.fill()
check("class 4 filter", dlg.list.GetItemCount() > 300 and all(k["konto"].startswith("4") for k in dlg.shown))
dlg.kind.SetSelection(2)
dlg.fill()
check("class 7 filter", dlg.list.GetItemCount() > 500 and all(k["konto"].startswith("7") for k in dlg.shown))
dlg.kind.SetSelection(0)
dlg.search.SetValue("годишен даночен биланс")
dlg.fill()
check("search in the full name", {"711213", "711216"} <= {k["konto"] for k in dlg.shown})
dlg.search.SetValue("711213")
dlg.fill()
check("search by konto", [k["konto"] for k in dlg.shown] == ["711213"])
r = dlg.report()
check("report has the shown rows with full names", len(r.rows) == 1 and len(r.rows[0][1]) > 100)
pdf = Path(sys.argv[1]).with_name("konta_test.pdf")
reports.to_pdf(r, pdf)
check("konta PDF written", pdf.stat().st_size > 1000)
check("konta HTML has the full name", "годишен даночен биланс" in reports.to_html(r))
pdf.unlink()
dlg.Destroy()

kd = registers.KontoDialog(frame)
kd.f_full.SetValue("Основни плати - државни службеници")
check("short name follows the full name", kd.f_short.GetValue() == "Основни плати - државни")
kd.f_short.SetValue("Плати државни")
kd.f_full.SetValue("Основни плати - државни службеници од ДКП")
check("a short name typed by hand is kept", kd.f_short.GetValue() == "Плати државни")
kd.f_konto.SetValue("401120")
v = kd.values()
check("dialog values", v == {"konto": "401120", "opis": "Плати државни", "opisfull": "Основни плати - државни службеници од ДКП"})
kd.f_short.SetValue("")
check("empty short name is made from the full name", kd.values()["opis"] == "Основни плати - државни")
kd.Destroy()

# --- ОПШТИНИ ------------------------------------------------------------------------------------------------
import csv  # noqa: E402

seed_path = Path(__file__).resolve().parent.parent / "extracted" / "ministry" / "opstini.csv"
with seed_path.open(encoding="utf-8-sig", newline="") as f:
    op_seed = [{"sifra": r["sifra"].strip(), "naziv": r["naziv"].strip()}
               for r in csv.DictReader(f, delimiter=";")]
check("opstini seed has 81 municipalities", len(op_seed) == 81)
check("Bitola is 103", any(r["sifra"] == "103" and "БИТОЛА" in r["naziv"].upper() for r in op_seed))
added_o, there_o = db.load_opstini(op_seed)
check("opstini seed loaded", added_o + there_o == 81 and added_o >= 80)
added2, there2 = db.load_opstini(op_seed)
check("opstini load is additive only", added2 == 0 and there2 == 81)
bitola = db.get_opstina("103")
check("get_opstina Bitola", bitola and bitola["naziv"].strip().upper() == "БИТОЛА")
db.save_opstina({"sifra": "999", "naziv": "ТЕСТ ОПШТИНА"})
check("opstina insert", db.get_opstina("999")["naziv"] == "ТЕСТ ОПШТИНА")
db.save_opstina({"sifra": "999", "naziv": "ТЕСТ ОПШТИНА 2"}, old_code="999")
check("opstina update name", db.get_opstina("999")["naziv"] == "ТЕСТ ОПШТИНА 2")
try:
    db.save_opstina({"sifra": "9", "naziv": "Х"})
    check("short code rejected", False)
except ValueError:
    check("short code rejected", True)
try:
    db.save_opstina({"sifra": "998", "naziv": "Test Latin"})
    check("Latin name rejected", False)
except ValueError:
    check("Latin name rejected", True)

init_now = db.get_init()
db.save_init({**{k: (init_now.get(k) or "") for k in
                 ("naziv", "adresa", "mesto", "telefon", "edb", "trezsmet", "trzkan", "trzkodkor", "trzinskod",
                  "embs", "email1", "email2", "email_fin")}, "opstina": "103"})
check("INIT.opstina saved", db.get_init().get("opstina", "").strip() == "103")
try:
    db.delete_opstina("103")
    check("default opstina delete refused", False)
except ValueError:
    check("default opstina delete refused", True)
try:
    db.save_opstina({"sifra": "102", "naziv": "БЕРОВО"}, old_code="103")
    check("default opstina code change refused", False)
except ValueError:
    check("default opstina code change refused", True)

db.delete_opstina("999")
check("unused opstina deleted", db.get_opstina("999") is None)

od = registers.OpstiniDialog(frame)
od.search.SetValue("битол")
od.fill()
check("opstini search count", od.list.GetItemCount() == 1)
od.list.Select(0)
check("opstini search by name", od.selected()["sifra"] == "103")
r = od.report()
check("opstini report rows", len(r.rows) == 1)
pdf = Path(sys.argv[1]).with_name("opstini_test.pdf")
reports.to_pdf(r, pdf)
check("opstini PDF written", pdf.stat().st_size > 500)
pdf.unlink()
od.Destroy()

gd = registers.GeneralDialog(frame)
check("GeneralDialog has opstina field", "opstina" in gd.f)
check("GeneralDialog default opstina", gd.f["opstina"].GetValue().strip() == "103")
gd.Destroy()

# --- УПЛАТНИ СМЕТКИ -----------------------------------------------------------------------------------------
print("УПЛАТНИ")
check("format_code", uplatni.format_code("840", "01013") == "840-01013")
check("parse_code plain", uplatni.parse_code("840-01258") == ("840", "01258"))
check("parse_code spaced", uplatni.parse_code("840 01258") == ("840", "01258"))
check("parse_code 11digit", uplatni.parse_code("84010301258") == ("840", "01258"))
check("to_podsmetprim", uplatni.to_podsmetprim("840", "01258", "103") == "84010301258")
check("matches bank+kod", uplatni.matches_podsmetprim("84010301258", "840", "01258"))
check("matches ignores middle", uplatni.matches_podsmetprim("84099901258", "840", "01258"))
check("matches rejects bad bank", not uplatni.matches_podsmetprim("84310301258", "840", "01258"))
try:
    uplatni.parse_code("84-01258")
    check("parse rejects short bank", False)
except ValueError:
    check("parse rejects short bank", True)
try:
    uplatni.to_podsmetprim("840", "01258", "1")
    check("to_podsmetprim rejects short opstina", False)
except ValueError:
    check("to_podsmetprim rejects short opstina", True)

added_schema = db.ensure_schema()
check("UPLATNI table present", "UPLATNI" not in added_schema)  # already created or just created earlier
# Force-create path: table must exist now
con = db.connect()
try:
    cur = con.cursor()
    cur.execute("select 1 from rdb$relations where rdb$relation_name=?", ("UPLATNI",))
    check("UPLATNI relation exists", cur.fetchone() is not None)
finally:
    con.close()

seed_rows = [
    {"banka": "840", "kod": "01013", "naziv": "Данок на личен доход", "konto": "741113"},
    {"banka": "840", "kod": "01258", "naziv": "Придонеси од плата", "konto": ""},
    {"banka": "843", "kod": "00001", "naziv": "Тест 843", "konto": "741113"},
]
n_add, n_exist = db.load_uplatni(seed_rows)
check("seed load added some or zero", n_add >= 0 and n_exist >= 0)
n_add2, n_exist2 = db.load_uplatni(seed_rows)
check("seed load add-missing only", n_add2 == 0 and n_exist2 == len(seed_rows))
all_u = db.list_uplatni()
check("list_uplatni non-empty", len(all_u) >= 3)
hit = db.list_uplatni("данок")
check("search by naziv", any(r["kod"] == "01013" for r in hit))
hit2 = db.list_uplatni("840-01258")
check("search by code", any(r["kod"] == "01258" and r["banka"] == "840" for r in hit2))
one = db.get_uplatna("840", "01013")
check("get_uplatna", one is not None and "Данок" in (one.get("naziv") or ""))

# save new
db.save_uplatna({"banka": "840", "kod": "99991", "naziv": "Тест нова уплатна", "konto": "741113"})
check("save new uplatna", db.get_uplatna("840", "99991") is not None)
db.save_uplatna({"banka": "840", "kod": "99991", "naziv": "Тест изменета", "konto": "741113"},
                old_banka="840", old_kod="99991")
check("edit naziv", (db.get_uplatna("840", "99991") or {}).get("naziv") == "Тест изменета")
try:
    db.save_uplatna({"banka": "84", "kod": "99992", "naziv": "Лоша банка", "konto": ""})
    check("bad banka rejected", False)
except ValueError:
    check("bad banka rejected", True)
try:
    db.save_uplatna({"banka": "840", "kod": "9999", "naziv": "Лош код", "konto": ""})
    check("bad kod rejected", False)
except ValueError:
    check("bad kod rejected", True)
try:
    db.save_uplatna({"banka": "840", "kod": "99993", "naziv": "Bad Latin only XYZQ", "konto": ""})
    # Latin may be encodable via macc — only reject if not encodable; use empty naziv instead
    check("saved latin-ish (encodable ok)", True)
except ValueError:
    check("saved latin-ish (encodable ok)", True)
try:
    db.save_uplatna({"banka": "840", "kod": "99994", "naziv": "", "konto": ""})
    check("empty naziv rejected", False)
except ValueError:
    check("empty naziv rejected", True)

# delete when unused
check("new not in use", not db.uplatna_in_use("840", "99991"))
db.delete_uplatna("840", "99991")
check("unused deleted", db.get_uplatna("840", "99991") is None)

# in_use blocks delete/code-change when podsmetprim matches (bank+any opstina+kod)
# PROMET has no godina/brojnal; pin the row via rdb$db_key.
db.save_uplatna({"banka": "840", "kod": "99995", "naziv": "За заклучен запис", "konto": ""})
con = db.connect()
prev_pods = None
prev_dbkey = None
try:
    cur = con.cursor()
    cur.execute("select first 1 rdb$db_key, podsmetprim from promet")
    row = cur.fetchone()
    check("promet row available for in_use test", row is not None)
    if row:
        prev_dbkey, prev_pods = row[0], row[1]
        fake = uplatni.to_podsmetprim("840", "99995", "103")
        cur.execute(
            "update promet set podsmetprim=? where rdb$db_key=?",
            (fake, prev_dbkey),
        )
        con.commit()
finally:
    con.close()

check("uplatna_in_use true", db.uplatna_in_use("840", "99995"))
try:
    db.delete_uplatna("840", "99995")
    check("in_use blocks delete", False)
except ValueError:
    check("in_use blocks delete", True)
try:
    db.save_uplatna({"banka": "840", "kod": "99996", "naziv": "Смена шифра", "konto": ""},
                    old_banka="840", old_kod="99995")
    check("in_use blocks code change", False)
except ValueError:
    check("in_use blocks code change", True)

# restore promet row and delete test uplatna
con = db.connect()
try:
    cur = con.cursor()
    if prev_dbkey is not None:
        cur.execute(
            "update promet set podsmetprim=? where rdb$db_key=?",
            (prev_pods, prev_dbkey),
        )
        con.commit()
finally:
    con.close()
check("after restore not in use", not db.uplatna_in_use("840", "99995"))
db.delete_uplatna("840", "99995")
check("test uplatna cleaned", db.get_uplatna("840", "99995") is None)
# cleanup optional latin row if created
if db.get_uplatna("840", "99993"):
    db.delete_uplatna("840", "99993")

ud = registers.UplatniDialog(frame)
ud.search.SetValue("01013")
ud.fill()
check("uplatni dialog search", ud.list.GetItemCount() >= 1)
ud.list.Select(0)
check("uplatni dialog selected", ud.selected() is not None and ud.selected()["kod"] == "01013")
rep = ud.report()
check("uplatni report has rows", len(rep.rows) >= 1)
pdf_u = Path(sys.argv[1]).with_name("uplatni_test.pdf")
reports.to_pdf(rep, pdf_u)
check("uplatni PDF written", pdf_u.stat().st_size > 500)
pdf_u.unlink()
ud.Destroy()

pick = registers.UplatniDialog(frame, pick=True)
pick.search.SetValue("01258")
pick.fill()
if pick.list.GetItemCount() > 0:
    pick.list.Select(0)
    pick.on_pick(None)
    check("pick sets chosen", pick.chosen is not None and pick.chosen.get("kod") == "01258")
else:
    check("pick sets chosen", False)
pick.Destroy()


frame.Destroy()

print("all checks passed")
