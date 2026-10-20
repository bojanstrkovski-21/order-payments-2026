r"""Look-and-feel demo for the NOVNAL rewrite: Office 2010 style ribbon,
order grid and entry panel, reading real orders from the working copy of the
database (read-only; see app\settings.ini).

Run:  .venv\Scripts\python.exe demo.py
      .venv\Scripts\python.exe demo.py --screenshot out.png   (saves and exits)
"""
import sys
from pathlib import Path

import wx
import wx.adv
import wx.grid
import wx.ribbon as RB

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402

COLUMNS = [
    ("Пратка", 55),
    ("Бр.", 60),
    ("Датум", 85),
    ("Примач", 230),
    ("Сметка на примач", 140),
    ("Износ", 100),
    ("Шифра", 55),
    ("Цел на дознака", 250),
]

ID_NEW, ID_EDIT, ID_DELETE, ID_FIND, ID_FILTER, ID_PRINT, ID_PREVIEW, ID_PDF = (wx.NewIdRef() for _ in range(8))


def art(art_id, size):
    return wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR, wx.Size(size, size))


def money(value):
    """1500.1 -> '1.500,10' (Macedonian format, rounded to denars and deni)."""
    text = f"{round(value or 0, 2):,.2f}"
    return text.replace(",", " ").replace(".", ",").replace(" ", ".")


def date(value):
    return value.strftime("%d.%m.%Y") if value else ""


class MainFrame(wx.Frame):
    def __init__(self, orders):
        super().__init__(None, title="NOVNAL - Налози (демо)", size=(1080, 680))
        self.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Segoe UI"))
        self.orders = orders

        ribbon = self._build_ribbon()
        self.body = wx.Panel(self)
        self.grid = self._build_grid()
        entry = self._build_entry()

        body_sizer = wx.BoxSizer(wx.VERTICAL)
        body_sizer.Add(self.grid, 1, wx.EXPAND | wx.ALL, 6)
        body_sizer.Add(entry, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self.body.SetSizer(body_sizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ribbon, 0, wx.EXPAND)
        sizer.Add(self.body, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.CreateStatusBar()
        self.SetStatusText(f"Последни {len(orders)} налози од работната копија на базата")
        self.Centre()
        if orders:
            self.grid.SelectRow(0)
            self.show_order(0)

    def _build_ribbon(self):
        ribbon = RB.RibbonBar(self, style=RB.RIBBON_BAR_DEFAULT_STYLE)
        ribbon.SetArtProvider(RB.RibbonMSWArtProvider())

        home = RB.RibbonPage(ribbon, wx.ID_ANY, "Налози")
        bar = RB.RibbonButtonBar(RB.RibbonPanel(home, wx.ID_ANY, "Налог"))
        bar.AddButton(ID_NEW, "Нов", art(wx.ART_NEW, 32))
        bar.AddButton(ID_EDIT, "Измени", art(wx.ART_EDIT, 32))
        bar.AddButton(ID_DELETE, "Бриши", art(wx.ART_DELETE, 32))

        bar = RB.RibbonButtonBar(RB.RibbonPanel(home, wx.ID_ANY, "Пребарај"))
        bar.AddButton(ID_FIND, "Најди", art(wx.ART_FIND, 32))
        bar.AddButton(ID_FILTER, "Филтер", art(wx.ART_LIST_VIEW, 32))

        bar = RB.RibbonButtonBar(RB.RibbonPanel(home, wx.ID_ANY, "Печатење"))
        bar.AddButton(ID_PRINT, "Печати", art(wx.ART_PRINT, 32))
        bar.AddButton(ID_PREVIEW, "Преглед", art(wx.ART_REPORT_VIEW, 32))
        bar.AddButton(ID_PDF, "PDF", art(wx.ART_FILE_SAVE_AS, 32))

        RB.RibbonPage(ribbon, wx.ID_ANY, "Шифрарници")
        RB.RibbonPage(ribbon, wx.ID_ANY, "Подесување")

        ribbon.Realize()
        ribbon.Bind(RB.EVT_RIBBONBUTTONBAR_CLICKED, self.on_ribbon_button)
        return ribbon

    def _build_grid(self):
        grid = wx.grid.Grid(self.body)
        grid.CreateGrid(len(self.orders), len(COLUMNS))
        grid.GetGridWindow().SetBackgroundColour(wx.WHITE)
        grid.SetRowLabelSize(0)
        grid.SetSelectionMode(wx.grid.Grid.SelectRows)
        grid.EnableEditing(False)
        for col, (label, width) in enumerate(COLUMNS):
            grid.SetColLabelValue(col, label)
            grid.SetColSize(col, width)
        for row, o in enumerate(self.orders):
            values = [o["pratka"], o["rbr"], date(o["datkniz"]), o["nazprim1"], o["smetprim"], money(o["iznos"]), o["sifra"], o["celdoz1"]]
            for col, value in enumerate(values):
                grid.SetCellValue(row, col, value)
            grid.SetCellAlignment(row, 5, wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
        grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, lambda e: (self.show_order(e.GetRow()), e.Skip()))
        return grid

    def _build_entry(self):
        box = wx.StaticBoxSizer(wx.VERTICAL, self.body, "Налог")
        parent = box.GetStaticBox()

        form = wx.FlexGridSizer(cols=4, vgap=6, hgap=8)
        form.AddGrowableCol(1, 2)
        form.AddGrowableCol(3, 1)

        def field(label):
            form.Add(wx.StaticText(parent, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = wx.TextCtrl(parent)
            form.Add(ctrl, 1, wx.EXPAND)
            return ctrl

        self.f_primac = field("Примач:")
        self.f_iznos = field("Износ:")
        self.f_smetka = field("Сметка на примач:")
        self.f_sifra = field("Шифра:")
        self.f_cel = field("Цел на дознака:")
        form.Add(wx.StaticText(parent, label="Датум:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.f_datum = wx.adv.DatePickerCtrl(parent, style=wx.adv.DP_DROPDOWN)
        form.Add(self.f_datum, 0)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        buttons.Add(wx.Button(parent, wx.ID_SAVE, "Зачувај"), 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(parent, wx.ID_CANCEL, "Откажи"), 0)

        box.Add(form, 0, wx.EXPAND | wx.ALL, 6)
        box.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        return box

    def show_order(self, row):
        o = self.orders[row]
        self.f_primac.SetValue(" ".join(filter(None, [o["nazprim1"], o["nazprim2"]])))
        self.f_iznos.SetValue(money(o["iznos"]))
        self.f_smetka.SetValue(o["smetprim"])
        self.f_sifra.SetValue(o["sifra"])
        self.f_cel.SetValue(" ".join(filter(None, [o["celdoz1"], o["celdoz2"]])))
        if o["datkniz"]:
            d = o["datkniz"]
            self.f_datum.SetValue(wx.DateTime.FromDMY(d.day, d.month - 1, d.year))

    def on_ribbon_button(self, event):
        self.SetStatusText(f"Кликнато: {event.GetBar().GetItemLabel(event.GetButton())}")


def save_screenshot(frame, path):
    rect = frame.GetScreenRect()
    bmp = wx.Bitmap(rect.width, rect.height)
    mem = wx.MemoryDC(bmp)
    mem.Blit(0, 0, rect.width, rect.height, wx.ScreenDC(), rect.x, rect.y)
    mem.SelectObject(wx.NullBitmap)
    bmp.SaveFile(path, wx.BITMAP_TYPE_PNG)
    frame.Close()


if __name__ == "__main__":
    app = wx.App()
    frame = MainFrame(db.recent_orders())
    frame.Show()
    frame.Raise()
    if len(sys.argv) == 3 and sys.argv[1] == "--screenshot":
        wx.CallLater(1500, save_screenshot, frame, sys.argv[2])
    app.MainLoop()
