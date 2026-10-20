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
        return {k: _clean(v) for k, v in rows[0].items()} if rows else None
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


def get_init():
    """Company settings (single row): naziv, mesto, trezsmet, trzkan, ..."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select * from init")
        rows = _rows(cur)
        return _decoded(rows[0], ("naziv", "adresa", "mesto", "trzkan")) if rows else {}
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


def shipment_has_type(pratka: str, day: dt.date, vidobr: str) -> bool:
    con = connect()
    try:
        cur = con.cursor()
        cur.execute("select count(*) from promet where pratka=? and datkniz=? and vidobr=?", (pratka, day, vidobr))
        return cur.fetchone()[0] > 0
    finally:
        con.close()


def _next_rbr(cur, pratka, day) -> str:
    """Last rbr of the shipment + 1, zero-padded to 6 (the old app used the last row ordered by rbr)."""
    cur.execute("select max(rbr) from promet where pratka=? and datkniz=?", (pratka, day))
    last = (cur.fetchone()[0] or "").strip()
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


def _find_db_key(cur, order):
    raw = order["_raw"]
    stored = [c for c in PROMET_COLUMNS if c in raw]
    where = " and ".join(f"({c} is null)" if raw[c] is None else f"({c}=?)" for c in stored)
    params = [raw[c] for c in stored if raw[c] is not None]
    cur.execute(f"select first 1 rdb$db_key from promet where {where}", params)
    found = cur.fetchone()
    if not found:
        raise LookupError("Налогот веќе не постои во базата.")
    return found[0]


def update_order(order, changes: dict) -> None:
    """Update exactly the given promet row with the changed columns."""
    con = connect()
    try:
        cur = con.cursor()
        key = _find_db_key(cur, order)
        changes = _encode_values(changes)
        cols = list(changes)
        cur.execute(
            f"update promet set {','.join(c + '=?' for c in cols)} where rdb$db_key=?", [changes[c] for c in cols] + [key]
        )
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
        cur.execute("delete from promet where rdb$db_key=?", (_find_db_key(cur, order),))
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
