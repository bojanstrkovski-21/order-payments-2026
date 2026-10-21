r"""Render page 1 of a shipment print-out to a PNG in memory (works while the screen is locked).

Usage:  python -I tools\render_print.py <kind: orders|specification|list> <out.png>
Uses app\settings.ini; picks the newest suitable shipment. Nothing is printed or saved to the database.
"""
import sys
from pathlib import Path

import wx
import wx.html

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
html, landscape = reports.build(ctx, db.shipment_orders(s[0], s[1].date()), kind)

app = wx.App()
width, height = (1123, 794) if landscape else (794, 1123)  # A4 at 96 dpi
bmp = wx.Bitmap(width, height)
dc = wx.MemoryDC(bmp)
dc.SetBackground(wx.WHITE_BRUSH)
dc.Clear()
renderer = wx.html.HtmlDCRenderer()
renderer.SetDC(dc)
renderer.SetFonts("Segoe UI", "Consolas", [7, 8, 9, 10, 12, 14, 16])
renderer.SetSize(width - 80, height - 80)
renderer.SetHtmlText(html)
dc.SetDeviceOrigin(40, 40)
renderer.Render(0, 0)
dc.SelectObject(wx.NullBitmap)
bmp.SaveFile(out, wx.BITMAP_TYPE_PNG)
print("rendered", kind, "shipment", ctx["pratka"], ctx["day"])
