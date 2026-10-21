"""СНИМИ — the payment-order file for the treasury („FORMAT ZA TREZOR", *.TDB), byte-identical to the old program.

Recovered from TVNNAL.JvSpeedButton9Click and checked against the files the old program saved (extracted/tdb_spec.md).
ASCII text in the MAC C encoding, CRLF line endings, one header line and one line per order.
"""
import datetime as dt

import macc

# CHAR widths of the database columns: the old program wrote CHAR values with their trailing spaces.
WIDTH = {
    "slvid": 1, "smetzadolz": 15, "podsmetzadolz": 15, "konzadolz": 6, "progzadolz": 2, "celdoz1": 35, "celdoz2": 35,
    "sifra": 6, "nazprim1": 35, "nazprim2": 35, "podsmetprim": 15, "konprim": 6, "progprim": 2, "povik1": 24,
    "vidobr": 2, "nacin": 1, "edb": 13, "dosdat": 8, "pratka": 1, "ddd": 8, "trzkodkor": 3, "trzinskod": 3,
}
SPACES = " " * 250


def _text(value):
    """Database value as the old program read it: NULL → '', CHAR → padded (set by caller), MAC C ASCII."""
    if value is None:
        return ""
    return macc.encode(value) if not value.isascii() else value


def _char(row, key):
    """A CHAR column with its trailing spaces (NULL stays empty, as AsString returned '')."""
    value = row.get(key)
    return "" if value is None else _text(value).ljust(WIDTH[key])


def _zero_left(row, key, width):
    """Copy(Copy('000…', 1, width-len(v)) + v, 1, width): left zero padding, cut to width."""
    value = _char(row, key)
    return (("0" * max(0, width - len(value))) + value)[:width]


def _amount(value):
    """Format('%18.2f', abs(x)) with spaces → '0' and '.' → ','; the sign is written separately."""
    return f"{abs(value or 0):18.2f}".replace(" ", "0").replace(".", ",")


def _sign(value):
    return "-" if (value or 0) < 0 else "+"


def header(init, booking):
    """Line 1: '1' + treasury code + treasury institution code + date (yyyymmdd) + shipment + count + sign + total."""
    count = str(booking["vkupnal"])
    line = ("1" + _char(init, "trzkodkor") + _char(init, "trzinskod") + _char(booking, "ddd") + _char(booking, "pratka")
            + (("0" * max(0, 6 - len(count))) + count)[:6] + _sign(booking["iznos"]) + _amount(booking["iznos"]))
    return line + SPACES


def order_line(number, row):
    """One order: the 20 parts the old program concatenated (row = raw promet columns)."""
    smetprim = row.get("smetprim")
    account = f"{float(smetprim) if smetprim and smetprim.strip() else 0:18.0f}".replace(" ", "0")
    return "".join([
        _char(row, "slvid"),
        f"{number:06d}",
        _char(row, "smetzadolz"),
        _char(row, "podsmetzadolz"),
        _char(row, "konzadolz"),
        _zero_left(row, "progzadolz", 2),
        (_char(row, "celdoz1") + " " + _char(row, "celdoz2") + SPACES)[:70],
        _char(row, "sifra"),
        _sign(row.get("iznos")),
        _amount(row.get("iznos")),
        account,
        (_char(row, "nazprim1") + " " + _char(row, "nazprim2") + SPACES)[:70],
        (_char(row, "podsmetprim") + SPACES)[:15],
        _zero_left(row, "konprim", 6),
        _zero_left(row, "progprim", 2),
        (_char(row, "povik1") + SPACES)[:24],
        _char(row, "vidobr"),
        _char(row, "nacin"),
        _zero_left(row, "edb", 13),
        _text(row.get("dosdat")).rstrip(),
    ])


def build(init, booking, rows) -> bytes:
    """The whole file: header + one line per order (in rbr order), each ending CRLF, ASCII."""
    lines = [header(init, booking)] + [order_line(n, r) for n, r in enumerate(rows, 1)]
    return "".join(line + "\r\n" for line in lines).encode("ascii", errors="replace")


def file_name(pratka: str, day: dt.date, extension: str) -> str:
    """N + dd + mm + yy + shipment + '.' + treasury code (e.g. N0510266.TDB)."""
    return f"N{day:%d%m%y}{pratka}.{extension.strip()}"
