"""Firebird access for the NOVNAL app. Text columns are converted from the old
MAC C encoding to Unicode on the way out (see macc.py) and back on the way in.

The old schema has no primary keys and duplicate rows exist, so single-row
changes go through RDB$DB_KEY inside one transaction (see extracted/vnnal_spec.md).
"""
import configparser
import datetime as dt
from pathlib import Path

import firebirdsql

import macc

SETTINGS = Path(__file__).with_name("settings.ini")

PROMET_COLUMNS = [
    "slvid", "rbr", "smetzadolz", "podsmetzadolz", "konzadolz", "progzadolz", "celdoz1", "celdoz2", "sifra",
    "iznos", "smetprim", "nazprim1", "nazprim2", "podsmetprim", "konprim", "progprim", "povik1", "vidobr",
    "nacin", "edb", "valdat", "datpod", "mespod", "pratka", "datkniz", "sifprim", "brkniz", "sifsmet",
    "datdos", "dosdat",
]
# Free-text columns typed in MAC C; everything else is digits, codes or dates.
TEXT_COLUMNS = {"celdoz1", "celdoz2", "nazprim1", "nazprim2", "mespod", "povik1"}
# MAC C text in the partner and employee registers (brlk: ID card number, shown in the MAC C font like povik1).
REGISTER_TEXT = ("naziv", "adresa", "mesto", "brlk")


def connect():
    cfg = configparser.ConfigParser()
    cfg.read(SETTINGS, encoding="utf-8")
    db = cfg["database"]
    return firebirdsql.connect(
        host=db["host"], database=db["path"], user=db["user"], password=db["password"], charset="WIN1251"
    )


def _first(cur):
    """First row of a result, reading the result to the end.

    firebirdsql can leave the rest of a result pending after fetchone(); running the next statement on the
    same connection then fails intermittently ("op_code = 66"). Always drain before the next statement.
    """
    rows = cur.fetchall()
    return rows[0] if rows else None


def _rows(cur):
    names = [d[0].lower() for d in cur.description]
    return [dict(zip(names, values)) for values in cur.fetchall()]


def _clean(value):
    return value.rstrip() if isinstance(value, str) else value


def _order_from_row(row):
    """Raw promet row -> order dict with Unicode text; the raw row is kept for exact matching."""
    order = {k: _clean(v) for k, v in row.items()}
    for key in TEXT_COLUMNS:
        order[key] = macc.decode(row.get(key))
    order["_raw"] = row
    return order


def yyyymmdd(day: dt.date) -> str:
    return day.strftime("%Y%m%d")


def recent_orders(limit=200):
    """Newest orders first (used by the look-and-feel demo)."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute(f"select first {int(limit)} * from promet order by datkniz desc, pratka, rbr")
        return [_order_from_row(r) for r in _rows(cur)]
    finally:
        con.close()


def get_account(sifra: str):
    """smetki row for a 2-digit account code, or None."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from smetki where sifra=?", (sifra,))
        rows = _rows(cur)
        return _decoded(rows[0], SMETKI_TEXT) if rows else None
    finally:
        con.close()


def get_booking(pratka: str, day: dt.date):
    """kniz row if the shipment is already booked, else None."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from kniz where (pratka=?) and (datkniz=?)", (pratka, day))
        rows = _rows(cur)
        return {k: _clean(v) for k, v in rows[0].items()} if rows else None
    finally:
        con.close()


def shipment_orders(pratka: str, day: dt.date):
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from promet where (pratka=?) and (datkniz=?) order by rbr", (pratka, day))
        return [_order_from_row(r) for r in _rows(cur)]
    finally:
        con.close()


def _decoded(row, text_keys):
    out = {k: _clean(v) for k, v in row.items()}
    for key in text_keys:
        out[key] = macc.decode(row.get(key))
    return out


# Columns the old program did not have, added to the NEW app's database only (user decisions, CLAUDE.md).
NEW_COLUMNS = {
    "INIT": [("EMBS", "VARCHAR(10)"), ("EMAIL1", "VARCHAR(100)"), ("EMAIL2", "VARCHAR(100)"), ("EMAIL_FIN", "VARCHAR(100)"), ("OPSTINA", "VARCHAR(3)")],
    "SMETKI": [("NAZIV", "VARCHAR(60)")],
    "KONTA": [("OPISFULL", "VARCHAR(400)")],   # full official name; OPIS stays the old 30-character short form
}
LIVE_DATABASE = Path(r"D:\nalozi\NOVNAL.FDB")
INIT_TEXT = ("naziv", "adresa", "mesto", "trzkan")
SMETKI_TEXT = ("naziv",)
KONTA_TEXT = ("opis", "opisfull")
OPSTINI_TEXT = ("naziv",)
UPLATNI_TEXT = ("naziv",)
DEFAULT_OPSTINA = "103"  # Битола


def _database_path():
    cfg = configparser.ConfigParser()
    cfg.read(SETTINGS, encoding="utf-8")
    return Path(cfg["database"]["path"])


def ensure_schema():
    """Add the new columns if missing. Never touches the old program's live database."""
    if str(_database_path()).lower() == str(LIVE_DATABASE).lower():
        raise RuntimeError("Новата програма не смее да ја менува базата на старата програма (D:\\nalozi).")
    con = connect()
    try:
        cur = con.cursor()
        added = []
        for table, columns in NEW_COLUMNS.items():
            cur.execute("select trim(rdb$field_name) from rdb$relation_fields where rdb$relation_name=?", (table,))
            existing = {r[0].strip() for r in cur.fetchall()}
            for name, sql_type in columns:
                if name not in existing:
                    cur.execute(f"alter table {table} add {name} {sql_type}")
                    added.append(f"{table}.{name}")
        cur.execute("select 1 from rdb$relations where rdb$relation_name=?", ("OPSTINI",))
        if not cur.fetchone():
            cur.execute("create table OPSTINI (SIFRA CHAR(3) not null, NAZIV VARCHAR(40) not null)")
            added.append("OPSTINI")
        cur.execute("select 1 from rdb$relations where rdb$relation_name=?", ("UPLATNI",))
        if not cur.fetchone():
            cur.execute(
                "create table UPLATNI ("
                "BANKA CHAR(3) not null, "
                "KOD CHAR(5) not null, "
                "NAZIV VARCHAR(400), "
                "KONTO CHAR(6)"
                ")"
            )
            added.append("UPLATNI")
        con.commit()
        return added
    finally:
        con.close()


def get_init():
    """Institution (single row): naziv, adresa, mesto, telefon, edb, trezsmet, trzkan, trzkodkor, trzinskod
    and — in the new database — embs, email1, email2, email_fin, opstina (default municipality)."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from init")
        rows = _rows(cur)
        return _decoded(rows[0], INIT_TEXT) if rows else {}
    finally:
        con.close()


def save_init(values: dict) -> None:
    """ГЕНЕРАЛИИ — ПАМТИ: update the single institution row, or insert it when there is none."""
    values = {k: macc.encode(v) if k in INIT_TEXT and isinstance(v, str) else v for k, v in values.items()}
    cols = list(values)
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select count(*) from init")
        if _first(cur)[0]:
            cur.execute(f"update init p set {','.join(c + '=?' for c in cols)} "
                        "where p.rdb$db_key = (select first 1 q.rdb$db_key from init q)", [values[c] for c in cols])
        else:
            cur.execute(f"insert into init ({','.join(cols)}) values ({','.join('?' * len(cols))})",
                        [values[c] for c in cols])
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def list_accounts():
    """СМЕТКИ ordered by code: sifra, smetbukor, podsbukor, naziv (new)."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from smetki order by sifra")
        return [_decoded(r, SMETKI_TEXT) for r in _rows(cur)]
    finally:
        con.close()


def save_account(values: dict, old_code=None) -> None:
    """Insert a new account (old_code None) or update the account with code old_code. A code must be unique."""
    values = {k: macc.encode(v) if k in SMETKI_TEXT and isinstance(v, str) else v for k, v in values.items()}
    cols = list(values)
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select count(*) from smetki where sifra=?", (values["sifra"],))
        taken = _first(cur)[0]
        if taken and values["sifra"] != old_code:
            raise ValueError("ДУПЛИРАН ЗАПИС !")
        if old_code is not None and values["sifra"] != old_code:
            cur.execute("select (select count(*) from promet where sifsmet=?) + (select count(*) from kniz where sifsmet=?) "
                        "from rdb$database", (old_code, old_code))
            if _first(cur)[0]:
                raise ValueError("ШИФРАТА НЕ МОЖЕ ДА СЕ ПРОМЕНИ — СМЕТКАТА СЕ КОРИСТИ ВО НАЛОЗИ")
        if old_code is None:
            cur.execute(f"insert into smetki ({','.join(cols)}) values ({','.join('?' * len(cols))})",
                        [values[c] for c in cols])
        else:
            cur.execute(f"update smetki set {','.join(c + '=?' for c in cols)} where sifra=?",
                        [values[c] for c in cols] + [old_code])
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def account_in_use(sifra: str) -> int:
    """How many orders and bookings use the account (deleting it would orphan them)."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select (select count(*) from promet where sifsmet=?) + (select count(*) from kniz where sifsmet=?) "
                    "from rdb$database", (sifra, sifra))
        return _first(cur)[0]
    finally:
        con.close()


def delete_account(sifra: str) -> None:
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("delete from smetki where sifra=?", (sifra,))
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def get_partner(sifra: str):
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from partneri where sifra=?", (sifra,))
        rows = _rows(cur)
        return _decoded(rows[0], REGISTER_TEXT) if rows else None
    finally:
        con.close()


def search_partners(text: str = ""):
    """Partner register for the picker; matches code or name (typed in Cyrillic)."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from partneri order by sifra")
        partners = [_decoded(r, REGISTER_TEXT) for r in _rows(cur)]
    finally:
        con.close()
    needle = text.strip().lower()
    return [p for p in partners if not needle or needle in p["sifra"].lower() or needle in p["naziv"].lower()]


def get_employee(sifra: str):
    """lica row (employee) by code, or None."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from lica where sifra=?", (sifra,))
        rows = _rows(cur)
        return _decoded(rows[0], REGISTER_TEXT) if rows else None
    finally:
        con.close()


def search_employees(text: str = ""):
    """Employee register for the picker; matches code, name or EMBG."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from lica order by sifra")
        people = [_decoded(r, REGISTER_TEXT) for r in _rows(cur)]
    finally:
        con.close()
    needle = text.strip().lower()
    return [p for p in people
            if not needle or needle in p["sifra"].lower() or needle in p["naziv"].lower() or needle in (p["embg"] or "")]


def konta_descriptions():
    """konta: ledger account -> description (Unicode)."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select konto, opis from konta")
        return {_clean(r["konto"]): macc.decode(r["opis"]) for r in _rows(cur)}
    finally:
        con.close()


def _konto_row(row):
    """konta row -> konto, opis (30-character short form), opisfull as stored, naziv (full name, else the short one)."""
    out = _decoded(row, KONTA_TEXT)
    out["konto"] = (out["konto"] or "").strip()
    out["naziv"] = out["opisfull"].strip() or out["opis"].strip()
    return out


def list_konta():
    """КОНТА ordered by konto."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from konta order by konto")
        return [_konto_row(r) for r in _rows(cur)]
    finally:
        con.close()


def get_konto(konto: str):
    for k in list_konta():
        if k["konto"] == konto:
            return k
    return None


def _encodable(text: str) -> bool:
    """False when the old MAC C encoding cannot hold the text exactly: an unknown character would become '?' and a
    Latin letter would be shown as a Cyrillic one."""
    return macc.decode(macc.encode(text)) == text.rstrip()


def save_konto(values: dict, old_code=None) -> None:
    """Insert a new konto (old_code None) or update the konto old_code. values: konto, opis (<= 30), opisfull.
    A konto must be unique; the code of a konto used on orders cannot change."""
    for key, limit in (("opis", 30), ("opisfull", 400)):
        if len(values[key]) > limit:
            raise ValueError(f"ТЕКСТОТ Е ПРЕДОЛГ (најмногу {limit} знаци)")
        if not _encodable(values[key]):
            raise ValueError("ТЕКСТОТ СОДРЖИ ЗНАК КОЈ НЕ МОЖЕ ДА СЕ ЗАЧУВА")
    values = {k: macc.encode(v) if k in KONTA_TEXT else v for k, v in values.items()}
    cols = list(values)
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select count(*) from konta where konto=?", (values["konto"],))
        taken = _first(cur)[0]
        if taken and values["konto"] != old_code:
            raise ValueError("ДУПЛИРАН ЗАПИС !")
        if old_code is not None and values["konto"] != old_code:
            cur.execute("select (select count(*) from promet where konzadolz=?) + (select count(*) from promet "
                        "where konprim=?) from rdb$database", (old_code, old_code))
            if _first(cur)[0]:
                raise ValueError("КОНТОТО НЕ МОЖЕ ДА СЕ ПРОМЕНИ — СЕ КОРИСТИ ВО НАЛОЗИ")
        if old_code is None:
            cur.execute(f"insert into konta ({','.join(cols)}) values ({','.join('?' * len(cols))})",
                        [values[c] for c in cols])
        else:
            cur.execute(f"update konta set {','.join(c + '=?' for c in cols)} where konto=?",
                        [values[c] for c in cols] + [old_code])
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def konto_in_use(konto: str) -> int:
    """How many orders use the konto as expense or revenue code."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select (select count(*) from promet where konzadolz=?) + (select count(*) from promet "
                    "where konprim=?) from rdb$database", (konto, konto))
        return _first(cur)[0]
    finally:
        con.close()


def delete_konto(konto: str) -> None:
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("delete from konta where konto=?", (konto,))
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def load_konta(rows):
    """One-time load of the ministry list: add the konta that are missing, never touch an existing one.
    rows: dicts with konto, opis, opisfull. Returns (added, already_there)."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select konto from konta")
        have = {_clean(r[0]) for r in cur.fetchall()}
        added = 0
        for r in rows:
            if r["konto"] in have:
                continue
            cur.execute("insert into konta (konto, opis, opisfull) values (?,?,?)",
                        (r["konto"], macc.encode(r["opis"]), macc.encode(r["opisfull"])))
            have.add(r["konto"])
            added += 1
        con.commit()
        return added, len(rows) - added
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()




def list_opstini():
    """ОПШТИНИ ordered by code."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from opstini order by sifra")
        return [_decoded(r, OPSTINI_TEXT) for r in _rows(cur)]
    finally:
        con.close()


def get_opstina(sifra: str):
    sifra = (sifra or "").strip()
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from opstini where sifra=?", (sifra,))
        rows = _rows(cur)
        return _decoded(rows[0], OPSTINI_TEXT) if rows else None
    finally:
        con.close()


def opstina_in_use(sifra: str) -> bool:
    """True when the municipality is the institution default in ГЕНЕРАЛИИ."""
    init = get_init() or {}
    return (init.get("opstina") or "").strip() == (sifra or "").strip()


def save_opstina(values: dict, old_code=None) -> None:
    """Insert or update one municipality. Code change refused when it is the INIT default."""
    sifra = (values.get("sifra") or "").strip()
    naziv = (values.get("naziv") or "").strip()
    if not (len(sifra) == 3 and sifra.isdigit()):
        raise ValueError("Шифрата на општината мора да биде точно 3 цифри.")
    if not naziv:
        raise ValueError("Називот на општината е задолжителен.")
    if len(naziv) > 40:
        raise ValueError("ТЕКСТОТ Е ПРЕДОЛГ (најмногу 40 знаци)")
    if not _encodable(naziv):
        raise ValueError("ТЕКСТОТ СОДРЖИ ЗНАК КОЈ НЕ МОЖЕ ДА СЕ ЗАЧУВА")
    old = (old_code or sifra).strip()
    con = connect()
    try:
        cur = con.cursor()
        if old != sifra:
            # Check INIT default without nesting another connection while we hold this one:
            cur.execute("select opstina from init")
            row = cur.fetchone()
            current = _clean(row[0]) if row else ""
            if current == old:
                raise ValueError("Шифрата се користи како основна општина во Генералии и не може да се смени.")
            cur.execute("select count(*) from opstini where sifra=?", (sifra,))
            if _first(cur)[0]:
                raise ValueError(f"Општина со шифра {sifra} веќе постои.")
            cur.execute("update opstini set sifra=?, naziv=? where sifra=?",
                        (sifra, macc.encode(naziv), old))
            if cur.rowcount == 0:
                raise ValueError("Општината не е пронајдена.")
        else:
            cur.execute("select count(*) from opstini where sifra=?", (sifra,))
            if _first(cur)[0]:
                cur.execute("update opstini set naziv=? where sifra=?", (macc.encode(naziv), sifra))
            else:
                cur.execute("insert into opstini (sifra, naziv) values (?, ?)",
                            (sifra, macc.encode(naziv)))
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def delete_opstina(sifra: str) -> None:
    sifra = (sifra or "").strip()
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select opstina from init")
        row = cur.fetchone()
        current = _clean(row[0]) if row else ""
        if current == sifra:
            raise ValueError("Општината е основна во Генералии и не може да се избрише.")
        cur.execute("delete from opstini where sifra=?", (sifra,))
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def load_opstini(rows):
    """Add missing municipalities only; never change existing ones. Returns (added, already_there)."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select sifra from opstini")
        have = {_clean(r[0]) for r in cur.fetchall()}
        added = 0
        for r in rows:
            sifra = (r.get("sifra") or "").strip()
            naziv = (r.get("naziv") or "").strip()
            if not sifra or sifra in have:
                continue
            if not (len(sifra) == 3 and sifra.isdigit() and naziv and len(naziv) <= 40 and _encodable(naziv)):
                continue
            cur.execute("insert into opstini (sifra, naziv) values (?, ?)",
                        (sifra, macc.encode(naziv)))
            have.add(sifra)
            added += 1
        con.commit()
        return added, len(rows) - added
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()



def list_uplatni(search: str = ""):
    """УПЛАТНИ СМЕТКИ ordered by banka, kod. Optional filter on code/name/konto."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select banka, kod, naziv, konto from uplatni order by banka, kod")
        rows = [_decoded(r, UPLATNI_TEXT) for r in _rows(cur)]
    finally:
        con.close()
    for r in rows:
        r["banka"] = (r.get("banka") or "").strip()
        r["kod"] = (r.get("kod") or "").strip()
        r["konto"] = (r.get("konto") or "").strip()
        r["naziv"] = (r.get("naziv") or "").strip()
    needle = (search or "").strip().casefold()
    if not needle:
        return rows
    out = []
    for r in rows:
        code = f"{r['banka']}-{r['kod']}"
        blob = " ".join([code, r["banka"], r["kod"], r["naziv"], r["konto"]]).casefold()
        if needle in blob:
            out.append(r)
    return out


def get_uplatna(banka: str, kod: str):
    banka = (banka or "").strip()
    kod = (kod or "").strip()
    for r in list_uplatni():
        if r["banka"] == banka and r["kod"] == kod:
            return r
    return None


def uplatna_in_use(banka: str, kod: str) -> bool:
    """True if any PROMET.podsmetprim is 11 digits = banka + any 3-digit opstina + kod."""
    b = (banka or "").strip()
    k = (kod or "").strip()
    con = connect()
    try:
        cur = con.cursor()
        # Positions 1-3 = banka, 7-11 = kod; middle 3 = municipality.
        # TRIM handles CHAR padding on podsmetprim.
        cur.execute(
            "select first 1 1 from promet "
            "where char_length(trim(trailing from podsmetprim)) = 11 "
            "and substring(trim(trailing from podsmetprim) from 1 for 3) = ? "
            "and substring(trim(trailing from podsmetprim) from 7 for 5) = ?",
            (b, k),
        )
        return _first(cur) is not None
    finally:
        con.close()


def save_uplatna(values: dict, old_banka: str | None = None, old_kod: str | None = None) -> None:
    banka = (values.get("banka") or "").strip()
    kod = (values.get("kod") or "").strip()
    naziv = (values.get("naziv") or "").strip()
    konto = (values.get("konto") or "").strip()
    if not (len(banka) == 3 and banka.isdigit()):
        raise ValueError("Банката мора да има 3 цифри (840 или 843).")
    if not (len(kod) == 5 and kod.isdigit()):
        raise ValueError("Кодот мора да има 5 цифри.")
    if not naziv:
        raise ValueError("Називот е задолжителен.")
    if len(naziv) > 400:
        raise ValueError("Називот е предолг (најмногу 400 знаци).")
    if not _encodable(naziv):
        raise ValueError("Називот содржи знаци што не можат да се зачуваат во базата.")
    if konto and not (len(konto) == 6 and konto.isdigit()):
        raise ValueError("Контото мора да биде празно или 6 цифри.")

    old_b = (old_banka or "").strip() or None
    old_k = (old_kod or "").strip() or None
    con = connect()
    try:
        cur = con.cursor()
        if old_b and old_k and (old_b != banka or old_k != kod):
            cur.execute(
                "select first 1 1 from promet "
                "where char_length(trim(trailing from podsmetprim)) = 11 "
                "and substring(trim(trailing from podsmetprim) from 1 for 3) = ? "
                "and substring(trim(trailing from podsmetprim) from 7 for 5) = ?",
                (old_b, old_k),
            )
            if _first(cur) is not None:
                raise ValueError("Шифрата се користи на налог и не може да се смени.")
            cur.execute(
                "select count(*) from uplatni where banka=? and kod=?",
                (banka, kod),
            )
            if _first(cur)[0]:
                raise ValueError(f"Уплатна сметка {banka}-{kod} веќе постои.")
            cur.execute(
                "update uplatni set banka=?, kod=?, naziv=?, konto=? where banka=? and kod=?",
                (banka, kod, macc.encode(naziv), konto or None, old_b, old_k),
            )
        elif old_b and old_k:
            cur.execute(
                "update uplatni set naziv=?, konto=? where banka=? and kod=?",
                (macc.encode(naziv), konto or None, banka, kod),
            )
        else:
            cur.execute(
                "select count(*) from uplatni where banka=? and kod=?",
                (banka, kod),
            )
            if _first(cur)[0]:
                raise ValueError(f"Уплатна сметка {banka}-{kod} веќе постои.")
            cur.execute(
                "insert into uplatni (banka, kod, naziv, konto) values (?,?,?,?)",
                (banka, kod, macc.encode(naziv), konto or None),
            )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def delete_uplatna(banka: str, kod: str) -> None:
    b = (banka or "").strip()
    k = (kod or "").strip()
    if uplatna_in_use(b, k):
        raise ValueError("Уплатната сметка се користи на налог и не може да се избрише.")
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("delete from uplatni where banka=? and kod=?", (b, k))
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def load_uplatni(rows):
    """Add missing uplatni (banka+kod) only; never change existing ones. Returns (added, already_there)."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select banka, kod from uplatni")
        have = {((r[0] or "").strip(), (r[1] or "").strip()) for r in cur.fetchall()}
        added = 0
        for r in rows:
            banka = (r.get("banka") or "").strip()
            kod = (r.get("kod") or "").strip()
            naziv = (r.get("naziv") or "").strip()
            konto = (r.get("konto") or "").strip()
            if not banka or not kod or (banka, kod) in have:
                continue
            if not (len(banka) == 3 and banka.isdigit() and len(kod) == 5 and kod.isdigit()):
                continue
            if not naziv or len(naziv) > 400 or not _encodable(naziv):
                continue
            if konto and not (len(konto) == 6 and konto.isdigit()):
                konto = ""
            cur.execute(
                "insert into uplatni (banka, kod, naziv, konto) values (?,?,?,?)",
                (banka, kod, macc.encode(naziv), konto or None),
            )
            have.add((banka, kod))
            added += 1
        con.commit()
        return added, len(rows) - added
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()



def specification(orders):
    """СПЕЦИФИКАЦИЈА of a salary shipment: totals per order type, ledger account, programme and bank (first three
    digits of the recipient account), as the old stored procedure SPECIF — but computed from the shipment's own orders.
    SPECIF selected by valdat = shipment date and missed orders whose value date differs (61 unbooked 62 orders)."""
    descriptions = konta_descriptions()
    groups = {}
    for o in orders:
        key = (o["vidobr"], o["konzadolz"] or "", o["progzadolz"] or "", (o["smetprim"] or "")[:3])
        broj, vkupno = groups.get(key, (0, 0.0))
        groups[key] = (broj + 1, vkupno + (o["iznos"] or 0))
    return [{"vidobr": v, "cel": descriptions.get(k, ""), "konz": k, "progz": p, "banka": b, "broj": n, "vkupno": s}
            for (v, k, p, b), (n, s) in sorted(groups.items())]


def shipment_has_type(pratka: str, day: dt.date, vidobr: str) -> bool:
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select count(*) from promet where pratka=? and datkniz=? and vidobr=?", (pratka, day, vidobr))
        return _first(cur)[0] > 0
    finally:
        con.close()


def _next_rbr(cur, pratka, day) -> str:
    """Last rbr of the shipment + 1, zero-padded to 6 (the old app used the last row ordered by rbr)."""
    cur.execute("select max(rbr) from promet where pratka=? and datkniz=?", (pratka, day))
    last = (_first(cur)[0] or "").strip()
    return f"{int(last) + 1 if last.isdigit() else 1:06d}"


def next_rbr(pratka, day) -> str:
    con = connect()
    try:
        return _next_rbr(con.cursor(), pratka, day)
    finally:
        con.close()


def _encode_values(values: dict) -> dict:
    return {k: macc.encode(v) if k in TEXT_COLUMNS and isinstance(v, str) else v for k, v in values.items()}


def insert_order(values: dict) -> str:
    """Insert one promet row (Unicode text is encoded to MAC C). rbr is assigned here; returns it."""
    con = connect()
    try:
        cur = con.cursor()
        values = _encode_values(values)
        values["rbr"] = _next_rbr(cur, values["pratka"], values["datkniz"])
        cols = list(values)
        cur.execute(
            f"insert into promet ({','.join(cols)}) values ({','.join('?' * len(cols))})", [values[c] for c in cols]
        )
        con.commit()
        return values["rbr"]
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def copy_shipment(src_pratka, src_day, dst_pratka, dst_day, today=None) -> int:
    """КОПИРАЊЕ: copy every order of a booked shipment into the current one (one transaction).

    As the old program: all columns copied unchanged except pratka/datkniz/valdat (the current shipment),
    datpod = today and brkniz cleared; datdos/dosdat were not copied. Unlike the old program the copies are
    numbered after the current shipment's last order (it copied rbr, creating duplicates). Returns the count.
    """
    today = today or dt.date.today()
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from promet where (pratka=?) and (datkniz=?) order by rbr", (src_pratka, src_day))
        source = _rows(cur)
        next_number = int(_next_rbr(cur, dst_pratka, dst_day))
        cols = [c for c in PROMET_COLUMNS if c not in ("datdos", "dosdat")]
        sql = f"insert into promet ({','.join(cols)}) values ({','.join('?' * len(cols))})"
        for offset, row in enumerate(source):
            values = dict(row)
            values.update(pratka=dst_pratka, datkniz=dst_day, valdat=dst_day, datpod=today, brkniz="",
                          rbr=f"{next_number + offset:06d}")
            cur.execute(sql, [values.get(c) for c in cols])
        con.commit()
        return len(source)
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _one_row(order):
    """SQL condition + parameters picking exactly one promet row equal to the order (all stored columns).

    Done inside the changing statement itself: a separate SELECT before the UPDATE/DELETE on the same
    connection let firebirdsql receive a late fetch answer ("op_code = 66") and fail intermittently.
    """
    raw = order["_raw"]
    stored = [c for c in PROMET_COLUMNS if c in raw]
    where = " and ".join(f"(q.{c} is null)" if raw[c] is None else f"(q.{c}=?)" for c in stored)
    params = [raw[c] for c in stored if raw[c] is not None]
    # The changing statement aliases promet as p; the lookup uses q (same table twice).
    return f"p.rdb$db_key = (select first 1 q.rdb$db_key from promet q where {where})", params


def _changed_one(cur):
    if cur.rowcount != 1:
        raise LookupError("Налогот веќе не постои во базата.")


def update_order(order, changes: dict) -> None:
    """Update exactly the given promet row with the changed columns."""
    con = connect()
    try:
        cur = con.cursor()
        changes = _encode_values(changes)
        cols = list(changes)
        where, params = _one_row(order)
        cur.execute(f"update promet p set {','.join(c + '=?' for c in cols)} where {where}",
                    [changes[c] for c in cols] + params)
        _changed_one(cur)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def delete_order(order) -> None:
    """Delete exactly one promet row equal to the given order (all columns)."""
    con = connect()
    try:
        cur = con.cursor()
        where, params = _one_row(order)
        cur.execute(f"delete from promet p where {where}", params)
        _changed_one(cur)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def next_booking_number(cur, today: dt.date) -> str:
    """knizbr = 4-digit yearly sequence + 2-digit year of today, as the old app did."""
    yy = f"{today.year % 100:02d}"
    cur.execute("select knizbr from kniz where knizbr like ? order by knizbr", ("%%%%" + yy,))
    rows = cur.fetchall()
    last = (rows[-1][0] or "").strip() if rows else ""
    seq = int(last[:4]) + 1 if len(last) == 6 and last[4:6] == yy and last[:4].isdigit() else 1
    return f"{seq:04d}{yy}"


def book_shipment(pratka, shipment_day, sifsmet, podnes_day, valuta_day, plata: bool, count, total, today=None):
    """Book a shipment: insert kniz, stamp its orders. Returns knizbr. One transaction."""
    today = today or dt.date.today()
    con = connect()
    try:
        cur = con.cursor()
        knizbr = next_booking_number(cur, today)
        cur.execute(
            "insert into kniz (pratka,datkniz,ddd,vkupnal,iznos,knizbr,sifsmet) values (?,?,?,?,?,?,?)",
            (pratka, valuta_day, yyyymmdd(valuta_day), count, round(total, 2), knizbr, sifsmet),
        )
        if plata:
            cur.execute(
                "update promet set brkniz=?,valdat=?,datpod=?,datkniz=?,datdos=?,dosdat=? "
                "where (pratka=?) and (datkniz=?)",
                (knizbr, valuta_day, podnes_day, valuta_day, valuta_day, yyyymmdd(valuta_day), pratka, shipment_day),
            )
        else:
            cur.execute(
                "update promet set brkniz=?,valdat=?,datpod=?,datkniz=? where (pratka=?) and (datkniz=?)",
                (knizbr, valuta_day, podnes_day, valuta_day, pratka, shipment_day),
            )
        con.commit()
        return knizbr
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
