r"""Screenshot the print preview of a shipment (nothing is printed or saved).

Usage:  python -I tools\shot_print.py <kind: orders|specification|list> <out.png>
Uses app\settings.ini; picks the newest suitable shipment.
"""
import sys
from pathlib import Path

import wx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402
import reports  # noqa: E402

kind, out = sys.argv[1], sys.argv[2]
con = db.connect()
cur = con.cursor()
cur.execute("select p.pratka, p.datkniz, p.sifsmet, count(*), sum(case when p.vidobr='62' then 1 else 0 end) "
            "from promet p group by 1,2,3 order by 2 desc")
rows = cur.fetchall()
con.close()
salary = kind != "orders"
s = next(r for r in rows if (r[4] == r[3] if salary else r[4] == 0) and r[3] >= 3)
ctx = {"pratka": s[0].strip(), "day": s[1].date(), "account": db.get_account(s[2].strip()), "init": db.get_init()}
orders = db.shipment_orders(s[0], s[1].date())

app = wx.App()
frame = wx.Frame(None)
printer = reports.preview(frame, reports.shipment_report(ctx, orders, kind), 1)


def shoot():
    preview = next(w for w in wx.GetTopLevelWindows() if w is not frame and w.IsShown())
    preview.SetSize((1100, 820))
    preview.Raise()
    wx.CallLater(800, grab, preview)


def grab(preview):
    rect = preview.GetScreenRect()
    bmp = wx.Bitmap(rect.width, rect.height)
    mem = wx.MemoryDC(bmp)
    mem.Blit(0, 0, rect.width, rect.height, wx.ScreenDC(), rect.x, rect.y)
    mem.SelectObject(wx.NullBitmap)
    bmp.SaveFile(out, wx.BITMAP_TYPE_PNG)
    preview.Destroy()
    frame.Destroy()


wx.CallLater(1500, shoot)
app.MainLoop()
