r"""Screenshot an order form filled with the newest order of a given type (nothing is saved).

Usage:  python -I tools\shot_order.py <vidobr> <out.png> [new]
"""
import sys
from pathlib import Path

import wx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402
import orders  # noqa: E402

vidobr, out = sys.argv[1], sys.argv[2]
new = len(sys.argv) > 3

con = db.connect()
cur = con.cursor()
cur.execute("select first 1 * from promet where vidobr=? order by datkniz desc", (vidobr,))
row = cur.fetchone()
if row is None:  # no order of this type yet (e.g. 61): borrow the newest shipment, new mode only
    cur.execute("select first 1 * from promet order by datkniz desc")
    row, new = cur.fetchone(), True
names = [d[0].lower() for d in cur.description]
order = db._order_from_row(dict(zip(names, row)))
con.close()

app = wx.App()
frame = wx.Frame(None)
context = {"pratka": order["pratka"], "day": order["datkniz"].date(),
           "account": db.get_account(order["sifsmet"]), "init": db.get_init()}
dlg = orders.FORMS[vidobr](frame, context, order=None if new else order)
dlg.Show()


def shoot():
    rect = dlg.GetScreenRect()
    bmp = wx.Bitmap(rect.width, rect.height)
    mem = wx.MemoryDC(bmp)
    mem.Blit(0, 0, rect.width, rect.height, wx.ScreenDC(), rect.x, rect.y)
    mem.SelectObject(wx.NullBitmap)
    bmp.SaveFile(out, wx.BITMAP_TYPE_PNG)
    dlg.Destroy()
    frame.Destroy()


wx.CallLater(1500, shoot)
app.MainLoop()
