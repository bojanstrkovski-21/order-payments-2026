r"""NOVNAL — new main window (old TMEN „ТРЕЗОР") with an Office 2010 style ribbon.

Run:  ..\demo\.venv\Scripts\python.exe main.py
      ... main.py --screenshot out.png [sifsmet pratka dd.mm.yyyy]   (saves a screenshot and exits)
"""
import datetime as dt
import sys

import wx
import wx.adv
import wx.ribbon as RB

import orders
import shipment
import ui

ORDER_TYPES = ["60", "61", "62", "70", "73", "76", "80"]


def art(art_id, size=32):
    return wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR, wx.Size(size, size))


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="ТРЕЗОР — Налози", size=(1280, 760))
        self.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Segoe UI"))
        self.ids = {}

        self.ribbon = self._build_ribbon()
        self.screen = shipment.ShipmentPanel(self, on_state_change=self.update_actions)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ribbon, 0, wx.EXPAND)
        sizer.Add(self.screen, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.CreateStatusBar()
        self.Centre()
        self.update_actions()

    # ----- ribbon ------------------------------------------------------------
    def _button(self, bar, key, label, bitmap, help_text=""):
        self.ids[key] = wx.NewIdRef()
        bar.AddButton(self.ids[key], label, bitmap, help_text)
        self.bars[key] = bar

    def _build_ribbon(self):
        self.bars = {}
        ribbon = RB.RibbonBar(self, style=RB.RIBBON_BAR_DEFAULT_STYLE)
        ribbon.SetArtProvider(RB.RibbonMSWArtProvider())

        page = RB.RibbonPage(ribbon, wx.ID_ANY, "Налози")
        bar = RB.RibbonButtonBar(RB.RibbonPanel(page, wx.ID_ANY, "Нов налог"))
        for code in ORDER_TYPES:
            self._button(bar, f"nal{code}", f"Налог {code}", art(wx.ART_NEW),
                         "" if code in orders.FORMS else "Се изработува")
        bar = RB.RibbonButtonBar(RB.RibbonPanel(page, wx.ID_ANY, "Налог"))
        self._button(bar, "edit", "Ажурирање", art(wx.ART_EDIT))
        self._button(bar, "delete", "Бришење", art(wx.ART_DELETE))
        self._button(bar, "copy", "Копирање", art(wx.ART_COPY))
        bar = RB.RibbonButtonBar(RB.RibbonPanel(page, wx.ID_ANY, "Пратка"))
        self._button(bar, "book", "Книжење", art(wx.ART_TICK_MARK))
        self._button(bar, "print", "Печатење", art(wx.ART_PRINT), "Се изработува")
        self._button(bar, "save", "Сними", art(wx.ART_FILE_SAVE), "Се изработува")
        self._button(bar, "new", "Нова пратка", art(wx.ART_GO_BACK))

        for title in ("Прегледи", "Шифрарник", "Разно"):
            RB.RibbonPage(ribbon, wx.ID_ANY, title)

        ribbon.Realize()
        ribbon.Bind(RB.EVT_RIBBONBUTTONBAR_CLICKED, self.on_ribbon)
        return ribbon

    def update_actions(self):
        s = self.screen
        editable = s.is_open and not s.is_booked
        selected = s.selected_order() if s.is_open else None
        state = {f"nal{c}": editable and c in orders.FORMS for c in ORDER_TYPES}
        state.update(print=False, save=False)  # not built yet
        state.update(copy=editable)
        state.update(edit=editable and bool(selected) and selected["vidobr"] in orders.FORMS,
                     delete=editable and bool(s.orders), book=editable, new=s.is_open)
        for key, enabled in state.items():
            self.bars[key].EnableButton(self.ids[key], enabled)
        if s.is_open:
            pratka, day = s.shipment
            self.SetStatusText(f"Сметка {s.account['sifra']}  •  Пратка {pratka}  •  {ui.date_text(day)}"
                               + ("  •  ПРОКНИЖАНА" if s.is_booked else ""))
        else:
            self.SetStatusText("Работна копија на базата")

    def on_ribbon(self, event):
        key = next(k for k, v in self.ids.items() if v == event.GetId())
        if key.startswith("nal"):
            self.screen.new_order(key[3:])
        elif key == "edit":
            self.screen.edit_selected()
        elif key == "copy":
            self.screen.copy_from()
        elif key == "delete":
            self.screen.delete_selected()
        elif key == "book":
            self.screen.book()
        elif key == "new":
            self.screen.reset()


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
    frame = MainFrame()
    frame.Show()
    frame.Raise()
    if len(sys.argv) >= 3 and sys.argv[1] == "--screenshot":
        if len(sys.argv) == 6:
            s = frame.screen
            s.f_sifsmet.SetValue(sys.argv[3])
            s.f_pratka.SetValue(sys.argv[4])
            ui.set_picker_date(s.f_datum, dt.datetime.strptime(sys.argv[5], "%d.%m.%Y").date())
            wx.CallAfter(s.open_shipment)
        wx.CallLater(2000, save_screenshot, frame, sys.argv[2])
    app.MainLoop()
