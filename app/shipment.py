"""ВНЕСУВАЊЕ НА НАЛОЗИ — shipment screen (old TVNNAL). Behaviour: extracted/vnnal_spec.md."""
import datetime as dt

import wx
import wx.adv
import wx.grid

import db
import macc
import orders
import reports
import tdb
import ui

# (title, column, width) — same columns and order as the old grid.
GRID_COLUMNS = [
    ("Вид на налог", "vidobr", 70),
    ("Шифра на примач", "sifprim", 80),
    ("Назив на примач", "nazprim1", 250),
    ("Седиште на примач", "nazprim2", 200),
    ("Износ", "iznos", 110),
    ("Сметка на примач", "smetprim", 140),
    ("Подсметка на примач", "podsmetprim", 120),
    ("Конто", "konzadolz", 70),
    ("Програма", "progzadolz", 70),
    ("Цел на дознака", "celdoz1", 260),
    ("Конто на примач", "konprim", 80),
    ("Прог. на примач", "progprim", 80),
    ("Датум на валута", "valdat", 90),
    ("Датум на поднес.", "datpod", 90),
    ("Датум на доспевање", "datdos", 90),
]


class BookingDialog(wx.Dialog):
    """КНИЖЕЊЕ: submission date, value date and whether the orders are salary orders."""

    def __init__(self, parent, default_day: dt.date):
        super().__init__(parent, title="Книжење")
        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=10)
        form.Add(wx.StaticText(self, label="Датум на поднесување:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.podnes = ui.date_picker(self)
        form.Add(self.podnes)
        form.Add(wx.StaticText(self, label="Датум на валута:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.valuta = ui.date_picker(self)
        form.Add(self.valuta)
        ui.set_picker_date(self.podnes, default_day)
        ui.set_picker_date(self.valuta, default_day)
        self.plata = wx.RadioBox(self, label="Налози од плата", choices=["Н — други налози", "Д — налози од плата"])

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(form, 0, wx.ALL, 12)
        sizer.Add(self.plata, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self.FindWindowById(wx.ID_OK).SetLabel("Книжи")
        self.FindWindowById(wx.ID_CANCEL).SetLabel("Откажи")
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(sizer)

    def values(self):
        return ui.picker_date(self.podnes), ui.picker_date(self.valuta), self.plata.GetSelection() == 1


class CopyDialog(wx.Dialog):
    """КОПИРАЊЕ: which earlier (booked) shipment to copy into the current one."""

    def __init__(self, parent):
        super().__init__(parent, title="Копирање")
        text = wx.StaticText(self, label="Со оваа акција се врши копирање на налозите\nод пратката која ќе ја наведете!")
        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=10)
        self.pratka = wx.TextCtrl(self, size=(40, -1))
        self.pratka.SetMaxLength(1)
        self.day = ui.date_picker(self)
        form.Add(wx.StaticText(self, label="Пратка бр.:"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.pratka)
        form.Add(wx.StaticText(self, label="Датум на валута:"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.day)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text, 0, wx.ALL, 12)
        sizer.Add(form, 0, wx.LEFT | wx.RIGHT, 12)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 12)
        self.FindWindowById(wx.ID_OK).SetLabel("Копирај")
        self.FindWindowById(wx.ID_CANCEL).SetLabel("Откажи")
        self.SetSizerAndFit(sizer)
        self.pratka.SetFocus()

    def values(self):
        return macc.encode(self.pratka.GetValue().strip().upper()), ui.picker_date(self.day)


class ShipmentPanel(wx.Panel):
    """Header (account, shipment, value date) → list of orders with actions."""

    def __init__(self, parent, on_state_change=None):
        super().__init__(parent)
        self.on_state_change = lambda: None  # connected after the panel is built
        self.orders = []
        self.account = None
        self.booking = None
        self.shipment = None  # (pratka as stored, date)

        header = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Пратка")
        box = header.GetStaticBox()
        self.f_sifsmet = wx.TextCtrl(box, size=(40, -1), style=wx.TE_PROCESS_ENTER)
        self.f_sifsmet.SetMaxLength(2)
        self.l_account = wx.StaticText(box, label="", size=(170, -1))
        self.f_pratka = wx.TextCtrl(box, size=(30, -1), style=wx.TE_PROCESS_ENTER)
        self.f_pratka.SetMaxLength(1)
        self.f_datum = ui.date_picker(box)
        self.b_open = wx.Button(box, label="Отвори пратка")
        for label, ctrl in (("Шифра на сметка:", self.f_sifsmet), ("Пратка бр.:", self.f_pratka), ("Датум на валута:", self.f_datum)):
            header.Add(wx.StaticText(box, label=label), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
            header.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
            if ctrl is self.f_sifsmet:
                header.Add(self.l_account, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
        header.Add(self.b_open, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 16)
        header.AddStretchSpacer()
        self.l_booked = wx.StaticText(box, label="")
        self.l_booked.SetForegroundColour(wx.Colour(192, 0, 0))
        header.Add(self.l_booked, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.grid = wx.grid.Grid(self)
        self.grid.CreateGrid(0, len(GRID_COLUMNS))
        self.grid.GetGridWindow().SetBackgroundColour(wx.WHITE)
        self.grid.SetRowLabelSize(40)
        self.grid.SetColLabelSize(36)
        self.grid.SetSelectionMode(wx.grid.Grid.SelectRows)
        self.grid.EnableEditing(False)
        for col, (title, _, width) in enumerate(GRID_COLUMNS):
            self.grid.SetColLabelValue(col, title.replace(" на ", "\nна ", 1))
            self.grid.SetColSize(col, width)

        footer = wx.BoxSizer(wx.HORIZONTAL)
        self.l_count = wx.StaticText(self, label="")
        self.l_total = wx.StaticText(self, label="")
        self.l_total.SetFont(self.l_total.GetFont().Bold())
        footer.Add(self.l_count, 0, wx.ALIGN_CENTER_VERTICAL)
        footer.AddStretchSpacer()
        footer.Add(wx.StaticText(self, label="Вкупно:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        footer.Add(self.l_total, 0, wx.ALIGN_CENTER_VERTICAL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(header, 0, wx.EXPAND | wx.ALL, 6)
        sizer.Add(self.grid, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        sizer.Add(footer, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(sizer)

        self.f_sifsmet.Bind(wx.EVT_KILL_FOCUS, self.on_account_left)
        self.f_sifsmet.Bind(wx.EVT_TEXT_ENTER, lambda e: self.f_pratka.SetFocus())
        self.f_pratka.Bind(wx.EVT_TEXT_ENTER, lambda e: self.f_datum.SetFocus())
        self.b_open.Bind(wx.EVT_BUTTON, lambda e: self.open_shipment())
        self.grid.Bind(wx.EVT_KEY_DOWN, self.on_grid_key)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, lambda e: self.edit_selected())
        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, lambda e: (e.Skip(), wx.CallAfter(self.on_state_change)))
        self.reset()
        if on_state_change:
            self.on_state_change = on_state_change

    # ----- state -----------------------------------------------------------
    @property
    def is_open(self):
        return self.shipment is not None

    @property
    def is_booked(self):
        return self.booking is not None

    @property
    def total(self):
        return sum(o["iznos"] or 0 for o in self.orders)

    def selected_order(self):
        rows = self.grid.GetSelectedRows() or [self.grid.GetGridCursorRow()]
        row = rows[0] if rows else -1
        return self.orders[row] if 0 <= row < len(self.orders) else None

    def reset(self):
        """Esc / Нова пратка: back to an empty header, like the old grid Esc key."""
        self.shipment = None
        self.booking = None
        self.orders = []
        for ctrl in (self.f_sifsmet, self.f_pratka, self.f_datum, self.b_open):
            ctrl.Enable()
        self.f_pratka.SetValue("")
        self.l_booked.SetLabel("")
        self.fill_grid()
        self.f_sifsmet.SetFocus()
        self.on_state_change()

    # ----- header ----------------------------------------------------------
    def on_account_left(self, event):
        event.Skip()
        code = self.f_sifsmet.GetValue().strip()
        self.account = db.get_account(code) if code else None
        self.l_account.SetLabel(self.account["smetbukor"] if self.account else "")

    def open_shipment(self):
        code = self.f_sifsmet.GetValue().strip()
        self.account = db.get_account(code) if code else None
        if not self.account:
            ui.info(self, "НЕПОСТОЕЧКА ШИФРА НА СМЕТКА")
            self.f_sifsmet.SetFocus()
            return
        self.l_account.SetLabel(self.account["smetbukor"])
        pratka = macc.encode(self.f_pratka.GetValue().strip().upper())
        if not pratka:
            ui.info(self, "ВНЕСЕТЕ БРОЈ НА ПРАТКА")
            self.f_pratka.SetFocus()
            return
        day = ui.picker_date(self.f_datum)

        booking = db.get_booking(pratka, day)
        if booking and booking["sifsmet"] != code:
            ui.info(self, "ОВАА ПРАТКА Е ОД ДРУГА СМЕТКА")
            return
        orders = db.shipment_orders(pratka, day)
        if orders and orders[0]["sifsmet"] != code:
            ui.info(self, "ОВАА ПРАТКА Е ОД ДРУГА СМЕТКА")
            return

        self.shipment = (pratka, day)
        self.booking = booking
        self.orders = orders
        for ctrl in (self.f_sifsmet, self.f_pratka, self.f_datum, self.b_open):
            ctrl.Disable()
        if booking:
            self.l_booked.SetLabel(f"ПРОКНИЖАНА под број {booking['knizbr'][:4]}-{booking['knizbr'][4:]}")
        self.fill_grid()
        self.grid.SetFocus()
        self.on_state_change()
        if booking:
            ui.info(self, "ОВАА ПРАТКА Е ПРОКНИЖАНА. ДОЗВОЛЕН Е САМО ПРЕГЛЕД И ПЕЧАТЕЊЕ!")

    # ----- grid ------------------------------------------------------------
    def fill_grid(self):
        grid = self.grid
        if grid.GetNumberRows():
            grid.DeleteRows(0, grid.GetNumberRows())
        grid.AppendRows(len(self.orders))
        for row, order in enumerate(self.orders):
            for col, (_, key, _) in enumerate(GRID_COLUMNS):
                value = order.get(key)
                if key == "iznos":
                    text = ui.money(value)
                    grid.SetCellAlignment(row, col, wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
                elif isinstance(value, dt.datetime):
                    text = ui.date_text(value)
                else:
                    text = "" if value is None else str(value)
                grid.SetCellValue(row, col, text)
        if self.orders:
            grid.SetGridCursor(0, 0)
            grid.SelectRow(0)
        grid.Scroll(0, 0)
        self.l_count.SetLabel(f"Налози: {len(self.orders)}" if self.is_open else "Внесете шифра на сметка, пратка и датум на валута.")
        self.l_total.SetLabel(ui.money(self.total) if self.is_open else "")

    def on_grid_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.reset()
        elif event.GetKeyCode() == wx.WXK_DELETE:
            self.delete_selected()
        elif event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.edit_selected()
        else:
            event.Skip()

    # ----- actions ---------------------------------------------------------
    def reload(self, keep_row=None):
        pratka, day = self.shipment
        self.orders = db.shipment_orders(pratka, day)
        self.fill_grid()
        if keep_row is not None and 0 <= keep_row < len(self.orders):
            self.grid.SetGridCursor(keep_row, 0)
            self.grid.SelectRow(keep_row)
            self.grid.MakeCellVisible(keep_row, 0)
        self.on_state_change()

    def _context(self):
        pratka, day = self.shipment
        return {"pratka": pratka, "day": day, "account": self.account, "init": db.get_init()}

    def new_order(self, vidobr):
        if not self.is_open or self.is_booked or vidobr not in orders.FORMS:
            return
        pratka, day = self.shipment
        refusal = orders.mixing_error(vidobr, {o["vidobr"] for o in db.shipment_orders(pratka, day)})
        if refusal:
            ui.info(self, refusal)
            return
        dlg = orders.FORMS[vidobr](self, self._context())
        try:
            dlg.ShowModal()
            saved = dlg.saved
        finally:
            dlg.Destroy()
        if saved:
            self.reload(keep_row=len(self.orders) + saved - 1)

    def edit_selected(self):
        order = self.selected_order()
        if not order or self.is_booked or order["vidobr"] not in orders.FORMS:
            return
        row = self.orders.index(order)
        dlg = orders.FORMS[order["vidobr"]](self, self._context(), order=order)
        try:
            dlg.ShowModal()
            saved = dlg.saved
        finally:
            dlg.Destroy()
        if saved:
            self.reload(keep_row=row)

    def print_shipment(self):
        """ПЕЧАТЕЊЕ — allowed for booked shipments too (old: „дозволен е само преглед и печатење")."""
        if not self.is_open:
            return
        if not self.orders:
            ui.info(self, "НЕМА НИШТО ЗА ПЕЧАТЕЊЕ")
            return
        dlg = reports.PrintDialog(self, reports.is_salary_only(self.orders))
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            kind, copies = dlg.values()
        finally:
            dlg.Destroy()
        self._printer = reports.preview(self, self._context(), self.orders, kind, copies)

    def save_file(self):
        """СНИМИ — write the treasury file (*.TDB, MAC C, byte-identical to the old program). Booked shipments only."""
        if not self.is_open:
            return
        if not self.is_booked:
            ui.info(self, "ОВАА ПРАТКА НЕ Е ПРОКНИЖАНА")
            return
        pratka, day = self.shipment
        init = db.get_init()
        extension = (init.get("trzkodkor") or "TDB").strip()
        dlg = wx.FileDialog(self, "Сними", defaultFile=tdb.file_name(pratka, day, extension),
                            wildcard=f"FORMAT ZA TREZOR (*.{extension})|*.{extension}",
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            path = dlg.GetPath()
        finally:
            dlg.Destroy()
        data = tdb.build(init, self.booking, [o["_raw"] for o in db.shipment_orders(pratka, day)])
        with open(path, "wb") as f:
            f.write(data)
        ui.info(self, "ПОДАТОЦИТЕ СЕ СНИМЕНИ")

    def copy_refusal(self, src_pratka, src_day):
        """Why the source shipment cannot be copied into this one, or None."""
        if not src_pratka:
            return "ВНЕСЕТЕ БРОЈ НА ПРАТКА!"
        booking = db.get_booking(src_pratka, src_day)
        if booking is None:
            return "НЕ ПОСТОИ ТАКВА ПРАТКА!"
        if booking["sifsmet"] != self.account["sifra"]:
            return "ОВАА ПРАТКА Е ОД ДРУГА СМЕТКА"
        if (src_pratka, src_day) == self.shipment:
            return "ОВА Е ИСТАТА ПРАТКА"
        source_types = {o["vidobr"] for o in db.shipment_orders(src_pratka, src_day)}
        if not source_types:
            return "НЕМА НАЛОЗИ ЗА КОПИРАЊЕ"
        present = {o["vidobr"] for o in self.orders}
        for vidobr in source_types:
            refusal = orders.mixing_error(vidobr, present | (source_types - {vidobr}))
            if refusal:
                return refusal
        return None

    def copy_from(self):
        if not self.is_open or self.is_booked:
            return
        dlg = CopyDialog(self)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            src_pratka, src_day = dlg.values()
        finally:
            dlg.Destroy()
        refusal = self.copy_refusal(src_pratka, src_day)
        if refusal:
            ui.info(self, refusal)
            return
        pratka, day = self.shipment
        copied = db.copy_shipment(src_pratka, src_day, pratka, day)
        self.reload(keep_row=len(self.orders))
        ui.info(self, f"ИСКОПИРАНИ СЕ {copied} НАЛОЗИ")

    def delete_selected(self):
        order = self.selected_order()
        if not order or self.is_booked:
            return
        if not ui.confirm(self, "ОВОЈ ЗАПИС ЌЕ БИДЕ ИЗБРИШАН !"):
            return
        db.delete_order(order)
        self.orders.remove(order)
        self.fill_grid()
        self.on_state_change()

    def book(self):
        if not self.is_open or self.is_booked:
            return
        if not self.orders:
            ui.info(self, "НЕМА НИШТО ЗА КНИЖЕЊЕ")
            return
        pratka, day = self.shipment
        dlg = BookingDialog(self, day)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            podnes, valuta, plata = dlg.values()
        finally:
            dlg.Destroy()
        knizbr = db.book_shipment(
            pratka, day, self.account["sifra"], podnes, valuta, plata, len(self.orders), self.total
        )
        ui.info(self, f"ПРОКНИЖАНО ПОД БРОЈ {knizbr[:4]}-{knizbr[4:]}!")
        self.reset()
