r"""Insert and update a Налог 60 through the db layer on a throwaway database copy,
and check the stored row matches what the old app wrote.

Usage:  python -I tools\test_nal60.py <settings.ini pointing at a throwaway copy>
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402

db.SETTINGS = Path(sys.argv[1])

init = db.get_init()
account = db.get_account("02")
partner = db.search_partners("")[0]
pratka, day = "9", dt.date(2026, 12, 31)  # an empty test shipment

values = {
    "konzadolz": "425911", "progzadolz": "N2", "celdoz1": "плаќање по фактура 15/2026", "celdoz2": "",
    "smetprim": partner["ziro"], "nazprim1": partner["naziv"], "nazprim2": partner["mesto"], "iznos": 1500.5,
    "povik1": "", "datpod": dt.date(2026, 12, 30), "mespod": init["mesto"], "valdat": dt.date(2026, 12, 31),
    "sifprim": partner["sifra"], "datdos": None, "dosdat": "",
    "slvid": "2", "nacin": "2", "sifra": "000000", "vidobr": "60", "pratka": pratka, "datkniz": day,
    "smetzadolz": init["trezsmet"], "podsmetzadolz": account["smetbukor"], "sifsmet": account["sifra"],
}
first = db.insert_order(dict(values))
second = db.insert_order(dict(values, iznos=200.0))
assert (first, second) == ("000001", "000002"), (first, second)

orders = db.shipment_orders(pratka, day)
assert [o["rbr"] for o in orders] == ["000001", "000002"]
o = orders[0]
raw = o["_raw"]
print("stored celdoz1:", repr(raw["celdoz1"].rstrip()), "->", o["celdoz1"])
assert o["celdoz1"] == "плаќање по фактура 15/2026"
assert raw["celdoz1"].rstrip() == "pla}awe po faktura 15/2026"
assert abs(o["iznos"] - 1500.5) < 1e-6 and o["vidobr"] == "60" and o["dosdat"] == "" and o["datdos"] is None

db.update_order(o, {"iznos": 1600.0, "datdos": dt.date(2027, 1, 15), "dosdat": "20270115"})
orders = db.shipment_orders(pratka, day)
assert abs(orders[0]["iznos"] - 1600.0) < 1e-6 and orders[0]["dosdat"] == "20270115"
assert abs(orders[1]["iznos"] - 200.0) < 1e-6, "update must touch only one row"
print(f"insert rbr {first}, {second}; update changed only the selected order")
print("all checks passed")
