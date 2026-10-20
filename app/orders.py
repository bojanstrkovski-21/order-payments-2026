"""Order forms (old TNAL60…TNAL80). Behaviour per type: extracted/nal60_spec.md, extracted/nal62_spec.md, …

The paper-form layout is shared; the order types differ in who the recipient is
(business partner, employee, …) and in a few saved columns.
"""
import datetime as dt

import wx
import wx.adv

import db
import ui
import workdays

# Recipient registers. `account` is the register column shown as the recipient account.
PARTNER = {
    "code_label": "Шифра на партнер:", "missing": "НЕМА ТАКОВ ДЕЛОВЕН ПАРТНЕР", "title": "Деловни партнери",
    "lookup": db.get_partner, "search": db.search_partners,
    "account": "ziro", "account_label": "Сметка на примач", "columns": [("Жиро сметка", "ziro", 150)],
}
EMPLOYEE = {
    "code_label": "Вработен:", "missing": "НЕМА ТАКОВ ВРАБОТЕН", "title": "Вработени",
    "lookup": db.get_employee, "search": db.search_employees,
    "account": "transak", "account_label": "Трансакциона сметка",
    "columns": [("Трансакциона сметка", "transak", 150), ("ЕМБГ", "embg", 110)],
}


class RecipientPicker(wx.Dialog):
    """Register picker (partners or employees), opened when the recipient code is left empty."""

    def __init__(self, parent, register):
        super().__init__(parent, title=register["title"], size=(760, 480), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.register = register
        self.columns = [("Шифра", "sifra", 60), ("Назив", "naziv", 260), ("Место", "mesto", 120)] + register["columns"]
        self.search = wx.SearchCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.search.ShowCancelButton(True)
        self.search.SetDescriptiveText("Барај по шифра или назив")
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        for i, (title, _, width) in enumerate(self.columns):
            self.list.InsertColumn(i, title, width=width)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.search, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(sizer)
        self.search.Bind(wx.EVT_TEXT, lambda e: self.fill())
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda e: self.EndModal(wx.ID_OK))
        self.rows = []
        self.fill()
        self.search.SetFocus()

    def fill(self):
        self.rows = [r for r in self.register["search"](self.search.GetValue()) if r["sifra"]]
        self.list.DeleteAllItems()
        for r in self.rows:
            self.list.Append([r[key] or "" for _, key, _ in self.columns])
        if self.rows:
            self.list.Select(0)

    def selected(self):
        index = self.list.GetFirstSelected()
        return self.rows[index] if index >= 0 else None


def _labeled(parent, sizer, label, ctrl, flag=wx.EXPAND):
    sizer.Add(wx.StaticText(parent, label=label), 0, wx.TOP, 6)
    sizer.Add(ctrl, 0, flag | wx.TOP, 2)
    return ctrl


def _readonly(parent, width=-1):
    ctrl = wx.TextCtrl(parent, size=(width, -1), style=wx.TE_READONLY)
    ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
    return ctrl


def _optional_date(parent):
    return wx.adv.DatePickerCtrl(parent, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY | wx.adv.DP_ALLOWNONE)


def _get_date(picker):
    """Date from an optional picker; None when empty or when the form has no such field."""
    value = picker.GetValue() if picker else wx.DefaultDateTime
    return dt.date(value.GetYear(), value.GetMonth() + 1, value.GetDay()) if value.IsValid() else None


def _set_date(picker, day):
    if picker:
        picker.SetValue(wx.DateTime.FromDMY(day.day, day.month - 1, day.year) if day else wx.DefaultDateTime)


class OrderDialog(wx.Dialog):
    """БАРАЊЕ ЗА ПЛАЌАЊЕ — the paper-form layout shared by the order types."""

    VIDOBR = ""
    TITLE = "БАРАЊЕ ЗА ПЛАЌАЊЕ\nкон небуџетски институции"
    RECIPIENT = PARTNER
    NACIN = "2"
    SHOW_TREZSMET = True     # Трезорска сметка on the payer side
    SHOW_EDB = False         # Единствен даночен број on the payer side (init.edb, saved in edb)
    SHOW_POVIK = True        # Повикување на број – одобрување
    BUDGET_RECIPIENT = False  # recipient block of payments between budget users (Налог 70)
    CASH_RECIPIENT = False    # cash payout: recipient ID card and EMBG instead of an account (Налог 80)
    FUNDS_RECIPIENT = False   # contributions to the funds: account, name, payment account, revenue code (Налог 61)
    SHOW_DATDOS = True        # Датум на доспевање
    REQUIRE_DATDOS = True     # user decision: required, except Налог 61 where it is optional
    FUND_RECIPIENT = False    # payments to the Fund's treasury: partner budget account + fixed Fund account (Налог 76)
    PURPOSE_LABEL = "Цел на дознака"
    LABELS = {"trezsmet": "Трезорска сметка", "smetbukor": "Сметка на буџетски корисник",
              "naziv": "Назив и седиште на буџетски корисник", "raskon": "Расходно конто", "prog": "Програма"}

    def __init__(self, parent, shipment, order=None):
        """shipment: dict with pratka, day, account (smetki row), init (init row). order: edit this order."""
        super().__init__(parent, title=f"НАЛОГ {self.VIDOBR}", style=wx.DEFAULT_DIALOG_STYLE)
        self.shipment = shipment
        self.order = order
        self.recipient = None
        self.saved = 0
        init = shipment["init"]
        reg = self.RECIPIENT

        title = wx.StaticText(self, label=self.TITLE, style=wx.ALIGN_CENTRE_HORIZONTAL)
        title.SetFont(title.GetFont().Bold().Scaled(1.2))

        top = wx.FlexGridSizer(cols=10, vgap=4, hgap=8)
        self.f_code = wx.TextCtrl(self, size=(60, -1), style=wx.TE_PROCESS_ENTER)
        self.f_code.SetMaxLength(4)
        self.f_trzkan = _readonly(self, 170)
        self.f_valdat = _optional_date(self)
        self.f_datdos = _optional_date(self) if self.SHOW_DATDOS else None
        self.f_obrazec = _readonly(self, 36)
        for label, ctrl in ((reg["code_label"], self.f_code), ("Трезорска канцеларија:", self.f_trzkan),
                            ("Датум на валута:", self.f_valdat), ("Датум на доспевање:", self.f_datdos),
                            ("Образец:", self.f_obrazec)):
            if ctrl:
                top.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
                top.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL)

        # Left: the budget user (payer); right: the recipient — as on the paper form.
        left = wx.BoxSizer(wx.VERTICAL)
        self.f_trezsmet = _labeled(self, left, self.LABELS["trezsmet"], _readonly(self)) if self.SHOW_TREZSMET else None
        self.f_smetbukor = _labeled(self, left, self.LABELS["smetbukor"], _readonly(self))
        self.f_naziv = _labeled(self, left, self.LABELS["naziv"], _readonly(self))
        self.f_mesto = _readonly(self)
        left.Add(self.f_mesto, 0, wx.EXPAND | wx.TOP, 2)
        row = wx.BoxSizer(wx.HORIZONTAL)
        konto = wx.BoxSizer(wx.VERTICAL)
        self.f_raskon = _labeled(self, konto, self.LABELS["raskon"], wx.TextCtrl(self, size=(90, -1)), 0)
        self.f_raskon.SetMaxLength(6)
        prog = wx.BoxSizer(wx.VERTICAL)
        self.f_prog = _labeled(self, prog, self.LABELS["prog"], wx.TextCtrl(self, size=(50, -1)), 0)
        self.f_prog.SetMaxLength(2)
        row.Add(konto, 0, wx.RIGHT, 24)
        row.Add(prog, 0)
        left.Add(row)
        self.f_edb = _labeled(self, left, "Единствен даночен број", _readonly(self, 160), 0) if self.SHOW_EDB else None
        self.f_cel1 = _labeled(self, left, self.PURPOSE_LABEL, wx.TextCtrl(self))
        self.f_cel1.SetMaxLength(35)
        self.f_cel2 = wx.TextCtrl(self)
        self.f_cel2.SetMaxLength(35)
        left.Add(self.f_cel2, 0, wx.EXPAND | wx.TOP, 2)

        right = wx.BoxSizer(wx.VERTICAL)
        self.f_embg = self.f_uplsmet = self.f_prihsif = self.f_progprim = self.f_brlk = self.f_smprim = None
        if self.CASH_RECIPIENT:
            # Налог 80: who collects the cash — name, place, ID card number and EMBG.
            self.f_nazprim1 = _labeled(self, right, "Назив и седиште на примач", _readonly(self))
            self.f_nazprim2 = _readonly(self)
            right.Add(self.f_nazprim2, 0, wx.EXPAND | wx.TOP, 2)
            self.f_brlk = _labeled(self, right, "Број на лична карта на примач", _readonly(self, 130), 0)
            self.f_embg = _labeled(self, right, "Единствен матичен број на примач", _readonly(self, 160), 0)
        elif self.FUND_RECIPIENT:
            # Налог 76: the partner's budget account and codes, then the Fund's fixed treasury account.
            box = wx.StaticBoxSizer(wx.VERTICAL, self, "")
            inner = box.GetStaticBox()
            self.f_smprim = _labeled(inner, box, "Сметка на буџетски корисник – примач", _readonly(inner, 210), 0)
            codes = wx.BoxSizer(wx.HORIZONTAL)
            prih = wx.BoxSizer(wx.VERTICAL)
            self.f_prihsif = _labeled(inner, prih, "Приходно конто", wx.TextCtrl(inner, size=(90, -1)), 0)
            self.f_prihsif.SetMaxLength(6)
            progp = wx.BoxSizer(wx.VERTICAL)
            self.f_progprim = _labeled(inner, progp, "Потпрограма", wx.TextCtrl(inner, size=(50, -1)), 0)
            self.f_progprim.SetMaxLength(2)
            codes.Add(prih, 0, wx.RIGHT, 24)
            codes.Add(progp, 0)
            box.Add(codes, 0, wx.BOTTOM, 6)
            right.Add(box, 0, wx.EXPAND)
            self.f_fund = _labeled(self, right, "Трансакциска сметка на примач", _readonly(self, 210), 0)
            self.f_fund.SetValue(self.FUND_ACCOUNT)
            self.f_nazprim1 = _labeled(self, right, "Назив и седиште на примач", _readonly(self))
            self.f_nazprim2 = _readonly(self)
            right.Add(self.f_nazprim2, 0, wx.EXPAND | wx.TOP, 2)
        elif self.FUNDS_RECIPIENT:
            # Налог 61: the fund's account and name, then its payment account and revenue code.
            self.f_smprim = _labeled(self, right, "Сметка на примач", _readonly(self))
            self.f_nazprim1 = _labeled(self, right, "Назив и седиште на примач", _readonly(self))
            self.f_nazprim2 = _readonly(self)
            right.Add(self.f_nazprim2, 0, wx.EXPAND | wx.TOP, 2)
            box = wx.StaticBoxSizer(wx.VERTICAL, self, "")
            inner = box.GetStaticBox()
            self.f_uplsmet = _labeled(inner, box, "Уплатна сметка", wx.TextCtrl(inner, size=(170, -1)), 0)
            self.f_uplsmet.SetMaxLength(15)
            self.f_prihsif = _labeled(inner, box, "Приходна шифра", wx.TextCtrl(inner, size=(90, -1)), 0)
            self.f_prihsif.SetMaxLength(6)
            box.AddSpacer(6)
            right.Add(box, 0, wx.EXPAND | wx.TOP, 6)
        elif self.BUDGET_RECIPIENT:
            # Налог 70: recipient name first, then its payment account, budget account, revenue code, programme.
            self.f_nazprim1 = _labeled(self, right, "Назив и седиште на примач", _readonly(self))
            self.f_nazprim2 = _readonly(self)
            right.Add(self.f_nazprim2, 0, wx.EXPAND | wx.TOP, 2)
            box = wx.StaticBoxSizer(wx.VERTICAL, self, "")
            inner = box.GetStaticBox()
            self.f_uplsmet = _labeled(inner, box, "Уплатна сметка", wx.TextCtrl(inner, size=(170, -1)), 0)
            self.f_uplsmet.SetMaxLength(15)
            self.f_smprim = _labeled(inner, box, "Сметка на буџетски корисник – примач", _readonly(inner, 210), 0)
            codes = wx.BoxSizer(wx.HORIZONTAL)
            prih = wx.BoxSizer(wx.VERTICAL)
            self.f_prihsif = _labeled(inner, prih, "Приходна шифра", wx.TextCtrl(inner, size=(90, -1)), 0)
            self.f_prihsif.SetMaxLength(6)
            progp = wx.BoxSizer(wx.VERTICAL)
            self.f_progprim = _labeled(inner, progp, "Програма", wx.TextCtrl(inner, size=(50, -1)), 0)
            self.f_progprim.SetMaxLength(2)
            codes.Add(prih, 0, wx.RIGHT, 24)
            codes.Add(progp, 0)
            box.Add(codes, 0, wx.BOTTOM, 6)
            right.Add(box, 0, wx.EXPAND | wx.TOP, 6)
        else:
            account_row = wx.BoxSizer(wx.HORIZONTAL)
            acc = wx.BoxSizer(wx.VERTICAL)
            self.f_smprim = _labeled(self, acc, reg["account_label"], _readonly(self))
            account_row.Add(acc, 1, wx.EXPAND)
            if reg is EMPLOYEE:
                embg = wx.BoxSizer(wx.VERTICAL)
                self.f_embg = _labeled(self, embg, "ЕМБГ", _readonly(self, 130), 0)
                account_row.Add(embg, 0, wx.LEFT, 10)
            right.Add(account_row, 0, wx.EXPAND)
            self.f_nazprim1 = _labeled(self, right, "Назив и седиште на примач", _readonly(self))
            self.f_nazprim2 = _readonly(self)
            right.Add(self.f_nazprim2, 0, wx.EXPAND | wx.TOP, 2)
        right.Add(wx.StaticText(self, label="Износ"), 0, wx.TOP, 6)
        amount = wx.BoxSizer(wx.HORIZONTAL)
        amount.Add(wx.StaticText(self, label="MKD"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.f_denari = wx.TextCtrl(self, size=(150, -1), style=wx.TE_RIGHT)
        amount.Add(self.f_denari, 0)
        amount.Add(wx.StaticText(self, label=","), 0, wx.ALIGN_BOTTOM | wx.LEFT | wx.RIGHT, 3)
        self.f_deni = _readonly(self, 34)  # amounts are whole denars: deni is always 00 (user decision)
        amount.Add(self.f_deni, 0)
        right.Add(amount, 0, wx.TOP, 2)
        self.f_povik = None
        if self.SHOW_POVIK:
            self.f_povik = _labeled(self, right, "Повикување на број – одобрување", wx.TextCtrl(self))
            self.f_povik.SetMaxLength(24)
        right.Add(wx.StaticText(self, label="Датум и место на поднесување"), 0, wx.TOP, 6)
        podnes = wx.BoxSizer(wx.HORIZONTAL)
        self.f_datpod = _optional_date(self)
        self.f_mespod = wx.TextCtrl(self)
        self.f_mespod.SetMaxLength(20)
        podnes.Add(self.f_datpod, 0, wx.RIGHT, 6)
        podnes.Add(self.f_mespod, 1)
        right.Add(podnes, 0, wx.EXPAND | wx.TOP, 2)

        columns = wx.BoxSizer(wx.HORIZONTAL)
        columns.Add(left, 1, wx.EXPAND | wx.RIGHT, 24)
        columns.Add(right, 1, wx.EXPAND)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        if order is None:
            specs = [("ПОНАТАМУ", self.on_next), ("КРАЈ", self.on_finish), ("ОТКАЗ", self.on_cancel)]
        else:
            specs = [("АЖУРИРАЈ", self.on_update), ("ОТКАЗ", self.on_cancel)]
        buttons.AddStretchSpacer()
        for label, handler in specs:
            button = wx.Button(self, label=label, size=(110, 30))
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.LEFT, 10)
        self.l_rbr = wx.StaticText(self, label="")
        buttons.Insert(0, self.l_rbr, 0, wx.ALIGN_CENTER_VERTICAL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(title, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        sizer.Add(top, 0, wx.ALL, 12)
        sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        sizer.Add(columns, 1, wx.EXPAND | wx.ALL, 12)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(sizer)
        self.SetMinSize((900, -1))
        self.Fit()
        self.CentreOnParent()

        # Fixed values (the old opener filled these from init / the shipment).
        self.f_trzkan.SetValue(init.get("trzkan") or "")
        self.f_obrazec.SetValue(self.VIDOBR)
        if self.f_trezsmet:
            self.f_trezsmet.SetValue(init.get("trezsmet") or "")
        if self.f_edb:
            self.f_edb.SetValue(init.get("edb") or "")
        self.f_smetbukor.SetValue(shipment["account"]["smetbukor"] or "")
        self.f_naziv.SetValue(init.get("naziv") or "")
        self.f_mesto.SetValue(init.get("mesto") or "")

        self.f_code.Bind(wx.EVT_KILL_FOCUS, self.on_code_left)
        self.f_code.Bind(wx.EVT_TEXT_ENTER, lambda e: self.f_valdat.SetFocus())
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)

        if order is None:
            self.clear(first=True)
        else:
            self.load(order)

    # ----- helpers -----------------------------------------------------------
    def set_default_valdat(self):
        """Датум на валута defaults to the next working day after Датум на поднесување (user rule;
        the old app used tomorrow). It follows the submission date until the user picks another date."""
        if not getattr(self, "_valdat_bound", False):
            self.f_datpod.Bind(wx.adv.EVT_DATE_CHANGED, self.on_datpod_changed)
            self._valdat_bound = True
        default = workdays.next_working_day(_get_date(self.f_datpod) or dt.date.today())
        _set_date(self.f_valdat, default)
        self._auto_valdat = default

    def on_datpod_changed(self, event):
        event.Skip()
        if getattr(self, "_auto_valdat", None) is not None and _get_date(self.f_valdat) in (None, self._auto_valdat):
            self.set_default_valdat()

    def on_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.on_cancel(event)
        else:
            event.Skip()

    def clear(self, first=False):
        """cisti: empties the order fields for the next order; submission date and place stay."""
        for ctrl in (self.f_code, self.f_raskon, self.f_prog, self.f_cel1, self.f_cel2, self.f_denari,
                     self.f_povik, self.f_uplsmet, self.f_prihsif, self.f_progprim):
            if ctrl:
                ctrl.SetValue("")
        self.f_deni.SetValue("00")
        self.recipient = None
        self.show_recipient()
        _set_date(self.f_datdos, None)
        if first:
            _set_date(self.f_datpod, dt.date.today())
            self.f_mespod.SetValue(self.shipment["init"].get("mesto") or "")
        self.set_default_valdat()
        rbr = db.next_rbr(self.shipment["pratka"], self.shipment["day"])
        self.l_rbr.SetLabel(f"Реден број: {int(rbr)}")
        self.f_code.SetFocus()

    def load(self, o):
        """Fill the form from a stored order (the recipient comes from the order, not the register)."""
        self.f_code.SetValue(o.get("sifprim") or "")
        self.recipient = {"sifra": o.get("sifprim") or "", self.RECIPIENT["account"]: o.get("smetprim") or "",
                          "naziv": o.get("nazprim1") or "", "mesto": o.get("nazprim2") or "", "embg": o.get("edb") or ""}
        if self.CASH_RECIPIENT:
            self.recipient["brlk"] = o.get("povik1") or ""
        self.show_recipient()
        _set_date(self.f_valdat, o["valdat"].date() if o.get("valdat") else None)
        _set_date(self.f_datdos, o["datdos"].date() if o.get("datdos") else None)
        _set_date(self.f_datpod, o["datpod"].date() if o.get("datpod") else None)
        self.f_raskon.SetValue(o.get("konzadolz") or "")
        self.f_prog.SetValue(o.get("progzadolz") or "")
        self.f_cel1.SetValue(o.get("celdoz1") or "")
        self.f_cel2.SetValue(o.get("celdoz2") or "")
        cents = round((o.get("iznos") or 0) * 100)
        self.f_denari.SetValue(ui.money(cents // 100)[:-3])
        self.f_deni.SetValue(f"{cents % 100:02d}")
        for ctrl, key in ((self.f_povik, "povik1"), (self.f_uplsmet, "podsmetprim"), (self.f_prihsif, "konprim"),
                          (self.f_progprim, "progprim"), (self.f_edb, "edb")):
            if ctrl and (o.get(key) or ctrl is not self.f_edb):
                ctrl.SetValue(o.get(key) or "")
        self.f_mespod.SetValue(o.get("mespod") or "")
        self.l_rbr.SetLabel(f"Реден број: {int(o['rbr']) if (o.get('rbr') or '').isdigit() else o.get('rbr')}")

    def show_recipient(self):
        r = self.recipient or {}
        if self.f_smprim:
            self.f_smprim.SetValue(r.get(self.RECIPIENT["account"]) or "")
        self.f_nazprim1.SetValue(r.get("naziv") or "")
        self.f_nazprim2.SetValue(r.get("mesto") or "")
        if self.f_embg:
            self.f_embg.SetValue(r.get("embg") or "")
        if self.f_brlk:
            self.f_brlk.SetValue(r.get("brlk") or "")

    # ----- field rules ----------------------------------------------------------
    def on_code_left(self, event):
        event.Skip()
        wx.CallAfter(self.check_recipient)

    def check_recipient(self):
        if not self or self.IsBeingDeleted():  # the form closed before this queued check ran
            return
        code = self.f_code.GetValue().strip()
        if not code:
            # Like the old form: no register when leaving towards a button (e.g. ОТКАЗ).
            focus = self.FindFocus()
            if focus is None or focus is self.f_code or isinstance(focus, wx.Button) or not self.IsActive():
                return
            picker = RecipientPicker(self, self.RECIPIENT)
            try:
                if picker.ShowModal() == wx.ID_OK and picker.selected():
                    self.recipient = picker.selected()
                    self.f_code.SetValue(self.recipient["sifra"])
                    self.show_recipient()
                    self.f_valdat.SetFocus()
                else:
                    self.f_code.SetFocus()
            finally:
                picker.Destroy()
            return
        if self.recipient and self.recipient.get("sifra") == code:
            return
        found = self.RECIPIENT["lookup"](code)
        if found is None:
            ui.info(self, self.RECIPIENT["missing"])
            self.f_code.SetFocus()
            return
        self.recipient = found
        self.show_recipient()

    # ----- saving ---------------------------------------------------------------
    def amount(self):
        """Whole denars (deni is fixed: 00 for new orders, the stored value for old ones).
        None when the field is empty, zero or not a number."""
        denari = self.f_denari.GetValue().replace(".", "").replace(" ", "").strip()
        if not denari.isdigit() or int(denari) == 0:
            return None
        return int(denari) + int(self.f_deni.GetValue() or "0") / 100

    def values(self):
        """Validated column values, or None after telling the user what is missing."""
        code = self.f_code.GetValue().strip()
        if self.recipient is None or not code or self.recipient.get("sifra") != code:
            found = self.RECIPIENT["lookup"](code) if code else None
            if found is None:
                ui.info(self, self.RECIPIENT["missing"])
                self.f_code.SetFocus()
                return None
            self.recipient = found
            self.show_recipient()
        valdat, datpod, datdos = _get_date(self.f_valdat), _get_date(self.f_datpod), _get_date(self.f_datdos)
        # Датум на доспевање is required (the old app wrongly let it be empty).
        for day, ctrl in ((valdat, self.f_valdat), (datdos, self.f_datdos if self.REQUIRE_DATDOS else None)):
            if ctrl and day is None:
                ui.info(self, "ВНЕСЕТЕ ДАТУМ")
                ctrl.SetFocus()
                return None
        required = [(self.f_raskon.GetValue().strip(), self.f_raskon),
                    (self.f_prog.GetValue().strip(), self.f_prog), (self.f_cel1.GetValue().strip(), self.f_cel1),
                    (datpod, self.f_datpod)]
        for value, ctrl in required:
            if not value:
                ui.info(self, "ВНЕСЕТЕ ВРЕДНОСТИ")
                ctrl.SetFocus()
                return None
        amount = self.amount()
        if amount is None:
            ui.info(self, "ВНЕСЕТЕ ИЗНОС")
            self.f_denari.SetFocus()
            return None
        r = self.recipient
        return {
            "konzadolz": self.f_raskon.GetValue().strip(),
            "progzadolz": self.f_prog.GetValue().strip().upper(),
            "celdoz1": self.f_cel1.GetValue().strip(),
            "celdoz2": self.f_cel2.GetValue().strip(),
            "smetprim": r.get(self.RECIPIENT["account"]) or "",
            "nazprim1": r.get("naziv") or "",
            "nazprim2": r.get("mesto") or "",
            "iznos": amount,
            **({"povik1": self.f_povik.GetValue().strip()} if self.f_povik else {}),
            "datpod": datpod,
            "mespod": self.f_mespod.GetValue().strip(),
            "valdat": valdat,
            "sifprim": code,
            # An empty optional due date is stored as the old app did: datdos NULL, dosdat ''.
            **({"datdos": datdos, "dosdat": db.yyyymmdd(datdos) if datdos else ""} if self.SHOW_DATDOS else {}),
            **self.extra_values(),
        }

    def extra_values(self):
        """Columns only some order types write (both on save and on АЖУРИРАЈ)."""
        return {}

    def insert_only_values(self):
        """Columns written when the order is created but not changed by АЖУРИРАЈ."""
        return {}

    def insert(self):
        values = self.values()
        if values is None:
            return False
        s = self.shipment
        values.update(self.insert_only_values())
        values.update(
            slvid="2", nacin=self.NACIN, sifra="000000", vidobr=self.VIDOBR, pratka=s["pratka"], datkniz=s["day"],
            smetzadolz=s["init"].get("trezsmet") or "", podsmetzadolz=s["account"]["smetbukor"] or "",
            sifsmet=s["account"]["sifra"],
        )
        db.insert_order(values)
        self.saved += 1
        return True

    def on_next(self, event):
        if self.insert():
            self.clear()

    def on_finish(self, event):
        if self.insert():
            self.EndModal(wx.ID_OK)

    def on_update(self, event):
        values = self.values()
        if values is None:
            return
        db.update_order(self.order, values)
        self.saved += 1
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)


class Nal60Dialog(OrderDialog):
    """НАЛОГ 60 — payment to a business partner (extracted/nal60_spec.md)."""

    VIDOBR = "60"
    RECIPIENT = PARTNER


class Nal62Dialog(OrderDialog):
    """НАЛОГ 62 — payment to an employee; the employee's EMBG is saved in `edb` (extracted/nal62_spec.md)."""

    VIDOBR = "62"
    RECIPIENT = EMPLOYEE

    def extra_values(self):
        return {"edb": (self.recipient or {}).get("embg") or ""}


class Nal70Dialog(OrderDialog):
    """НАЛОГ 70 — public duties and payments between budget users (extracted/nal70_spec.md)."""

    VIDOBR = "70"
    TITLE = "БАРАЊЕ ЗА ПЛАЌАЊЕ НА ЈАВНИ ДАВАЧКИ\nИ ЗА ПЛАЌАЊА ПОМЕЃУ БУЏЕТСКИ КОРИСНИЦИ"
    RECIPIENT = {**PARTNER, "account_label": "Сметка на буџетски корисник – примач"}
    NACIN = "3"
    SHOW_TREZSMET = False
    SHOW_EDB = True
    SHOW_POVIK = False
    BUDGET_RECIPIENT = True

    def extra_values(self):
        return {
            "podsmetprim": self.f_uplsmet.GetValue().strip().upper(),
            "konprim": self.f_prihsif.GetValue().strip(),
            "progprim": self.f_progprim.GetValue().strip().upper(),
        }

    def insert_only_values(self):
        # The old АЖУРИРАЈ never rewrote edb; it is the company's tax number taken when the order was made.
        return {"edb": self.shipment["init"].get("edb") or ""}


class Nal80Dialog(OrderDialog):
    """НАЛОГ 80 — cash payout (extracted/nal80_spec.md)."""

    VIDOBR = "80"
    TITLE = "БАРАЊЕ ЗА ИСПЛАТА НА ГОТОВИНА"
    NACIN = "3"
    SHOW_POVIK = False
    CASH_RECIPIENT = True
    PURPOSE_LABEL = "Цел на исплата"

    def extra_values(self):
        r = self.recipient or {}
        return {
            "smetprim": self.shipment["init"].get("trezsmet") or "",  # cash leaves through the treasury account
            "edb": r.get("embg") or "",       # recipient EMBG
            "povik1": r.get("brlk") or "",    # recipient ID card number
        }


class Nal61Dialog(OrderDialog):
    """НАЛОГ 61 — contributions to the funds (extracted/nal61_spec.md). Never used in the data so far."""

    VIDOBR = "61"
    TITLE = "БАРАЊЕ ЗА ПЛАЌАЊЕ НА ПРИДОНЕСИ\nКОН ФОНДОВИТЕ"
    NACIN = "3"
    SHOW_EDB = True
    SHOW_POVIK = False
    FUNDS_RECIPIENT = True
    REQUIRE_DATDOS = False  # the old form had no due date; user decision: add it, optional

    def extra_values(self):
        return {
            "podsmetprim": self.f_uplsmet.GetValue().strip(),
            "konprim": self.f_prihsif.GetValue().strip(),
        }

    def insert_only_values(self):
        return {"edb": self.shipment["init"].get("edb") or ""}


class Nal73Dialog(OrderDialog):
    """НАЛОГ 73 — БАРАЊЕ ЗА БЕЗГОТОВИНСКИ ПОВРАТ НА СРЕДСТВА (extracted/nal73_spec.md).

    No register lookup: the recipient (account, name, tax number, budget codes) is typed in.
    Own layout; saving, buttons and the amount come from OrderDialog.
    """

    VIDOBR = "73"
    TITLE = "БАРАЊЕ ЗА БЕЗГОТОВИНСКИ ПОВРАТ НА СРЕДСТВА"
    NACIN = "2"

    def __init__(self, parent, shipment, order=None):  # noqa: C901 — one flat form layout
        wx.Dialog.__init__(self, parent, title=f"НАЛОГ {self.VIDOBR}", style=wx.DEFAULT_DIALOG_STYLE)
        self.shipment = shipment
        self.order = order
        self.recipient = None
        self.saved = 0
        init = shipment["init"]

        title = wx.StaticText(self, label=self.TITLE, style=wx.ALIGN_CENTRE_HORIZONTAL)
        title.SetFont(title.GetFont().Bold().Scaled(1.2))

        top = wx.FlexGridSizer(cols=8, vgap=4, hgap=8)
        self.f_trzkan = _readonly(self, 170)
        self.f_valdat = _optional_date(self)
        self.f_datdos = _optional_date(self)
        self.f_obrazec = _readonly(self, 36)
        for label, ctrl in (("Трезорска канцеларија:", self.f_trzkan), ("Датум на валута:", self.f_valdat),
                            ("Датум на доспевање:", self.f_datdos), ("Образец:", self.f_obrazec)):
            top.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            top.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL)

        def text(parent, width, length):
            ctrl = wx.TextCtrl(parent, size=(width, -1))
            ctrl.SetMaxLength(length)
            return ctrl

        def code_pair(parent, sizer, first_label, second_label):
            row = wx.BoxSizer(wx.HORIZONTAL)
            a, b = wx.BoxSizer(wx.VERTICAL), wx.BoxSizer(wx.VERTICAL)
            first = _labeled(parent, a, first_label, text(parent, 90, 6), 0)
            second = _labeled(parent, b, second_label, text(parent, 50, 2), 0)
            row.Add(a, 0, wx.RIGHT, 24)
            row.Add(b, 0)
            sizer.Add(row, 0, wx.BOTTOM, 6)
            return first, second

        # Left: the budget user that returns the funds.
        left = wx.BoxSizer(wx.VERTICAL)
        payer = wx.StaticBoxSizer(wx.VERTICAL, self, "")
        box = payer.GetStaticBox()
        self.f_trezsmet = _labeled(box, payer, "Трезорска сметка", _readonly(box, 210), 0)
        self.f_smetbukor = _labeled(box, payer, "Сметка на буџетски корисник", _readonly(box, 210), 0)
        self.f_prihsif, self.f_progprim = code_pair(box, payer, "Приходно конто", "Потпрограма")
        left.Add(payer, 0, wx.EXPAND)
        self.f_naziv = _labeled(self, left, "Назив и седиште на буџетски корисник", _readonly(self))
        self.f_mesto = _readonly(self)
        left.Add(self.f_mesto, 0, wx.EXPAND | wx.TOP, 2)
        self.f_cel1 = _labeled(self, left, "Цел на дознака", text(self, -1, 35))
        self.f_cel2 = text(self, -1, 35)
        left.Add(self.f_cel2, 0, wx.EXPAND | wx.TOP, 2)

        # Right: the recipient, typed in.
        right = wx.BoxSizer(wx.VERTICAL)
        self.f_smprim = _labeled(self, right, "Сметка на примач", text(self, 170, 15), 0)
        self.f_nazprim1 = _labeled(self, right, "Назив и седиште на примач", text(self, -1, 35))
        self.f_nazprim2 = text(self, -1, 20)
        right.Add(self.f_nazprim2, 0, wx.EXPAND | wx.TOP, 2)
        self.f_edb = _labeled(self, right, "Единствен даночен број", text(self, 160, 13), 0)
        rec = wx.StaticBoxSizer(wx.VERTICAL, self, "")
        box = rec.GetStaticBox()
        self.f_smbukorprim = _labeled(box, rec, "Сметка на буџетски корисник – примач", text(box, 210, 18), 0)
        self.f_rasprihkon, self.f_prograsprim = code_pair(box, rec, "Расходно конто / приходно конто", "Потпрограма")
        right.Add(rec, 0, wx.EXPAND | wx.TOP, 6)
        right.Add(wx.StaticText(self, label="Износ"), 0, wx.TOP, 6)
        amount = wx.BoxSizer(wx.HORIZONTAL)
        amount.Add(wx.StaticText(self, label="MKD"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.f_denari = wx.TextCtrl(self, size=(150, -1), style=wx.TE_RIGHT)
        amount.Add(self.f_denari, 0)
        amount.Add(wx.StaticText(self, label=","), 0, wx.ALIGN_BOTTOM | wx.LEFT | wx.RIGHT, 3)
        self.f_deni = _readonly(self, 34)
        amount.Add(self.f_deni, 0)
        right.Add(amount, 0, wx.TOP, 2)
        self.f_povik = _labeled(self, right, "Повикување на број – одобрување", text(self, -1, 24))
        right.Add(wx.StaticText(self, label="Датум и место на поднесување"), 0, wx.TOP, 6)
        podnes = wx.BoxSizer(wx.HORIZONTAL)
        self.f_datpod = _optional_date(self)
        self.f_mespod = text(self, -1, 20)
        podnes.Add(self.f_datpod, 0, wx.RIGHT, 6)
        podnes.Add(self.f_mespod, 1)
        right.Add(podnes, 0, wx.EXPAND | wx.TOP, 2)

        columns = wx.BoxSizer(wx.HORIZONTAL)
        columns.Add(left, 1, wx.EXPAND | wx.RIGHT, 24)
        columns.Add(right, 1, wx.EXPAND)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.l_rbr = wx.StaticText(self, label="")
        buttons.Add(self.l_rbr, 0, wx.ALIGN_CENTER_VERTICAL)
        buttons.AddStretchSpacer()
        specs = ([("ПОНАТАМУ", self.on_next), ("КРАЈ", self.on_finish), ("ОТКАЗ", self.on_cancel)] if order is None
                 else [("АЖУРИРАЈ", self.on_update), ("ОТКАЗ", self.on_cancel)])
        for label, handler in specs:
            button = wx.Button(self, label=label, size=(110, 30))
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.LEFT, 10)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(title, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        sizer.Add(top, 0, wx.ALL, 12)
        sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        sizer.Add(columns, 1, wx.EXPAND | wx.ALL, 12)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(sizer)
        self.SetMinSize((900, -1))
        self.Fit()
        self.CentreOnParent()

        self.f_trzkan.SetValue(init.get("trzkan") or "")
        self.f_obrazec.SetValue(self.VIDOBR)
        self.f_trezsmet.SetValue(init.get("trezsmet") or "")
        self.f_smetbukor.SetValue(shipment["account"]["smetbukor"] or "")
        self.f_naziv.SetValue(init.get("naziv") or "")
        self.f_mesto.SetValue(init.get("mesto") or "")
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        if order is None:
            self.clear(first=True)
        else:
            self.load(order)

    def _typed(self):
        return (self.f_prihsif, self.f_progprim, self.f_cel1, self.f_cel2, self.f_smprim, self.f_nazprim1,
                self.f_nazprim2, self.f_edb, self.f_smbukorprim, self.f_rasprihkon, self.f_prograsprim,
                self.f_denari, self.f_povik)

    def clear(self, first=False):
        for ctrl in self._typed():
            ctrl.SetValue("")
        self.f_deni.SetValue("00")
        _set_date(self.f_datdos, None)
        if first:
            _set_date(self.f_datpod, dt.date.today())
            self.f_mespod.SetValue(self.shipment["init"].get("mesto") or "")
        self.set_default_valdat()
        self.l_rbr.SetLabel(f"Реден број: {int(db.next_rbr(self.shipment['pratka'], self.shipment['day']))}")
        self.f_valdat.SetFocus()

    COLUMNS = (("f_prihsif", "konzadolz"), ("f_progprim", "progzadolz"), ("f_cel1", "celdoz1"), ("f_cel2", "celdoz2"),
               ("f_smprim", "smetprim"), ("f_nazprim1", "nazprim1"), ("f_nazprim2", "nazprim2"), ("f_edb", "edb"),
               ("f_smbukorprim", "podsmetprim"), ("f_rasprihkon", "konprim"), ("f_prograsprim", "progprim"),
               ("f_povik", "povik1"), ("f_mespod", "mespod"))

    def load(self, o):
        for attr, key in self.COLUMNS:
            getattr(self, attr).SetValue(o.get(key) or "")
        _set_date(self.f_valdat, o["valdat"].date() if o.get("valdat") else None)
        _set_date(self.f_datdos, o["datdos"].date() if o.get("datdos") else None)
        _set_date(self.f_datpod, o["datpod"].date() if o.get("datpod") else None)
        cents = round((o.get("iznos") or 0) * 100)
        self.f_denari.SetValue(ui.money(cents // 100)[:-3])
        self.f_deni.SetValue(f"{cents % 100:02d}")
        self.l_rbr.SetLabel(f"Реден број: {int(o['rbr']) if (o.get('rbr') or '').isdigit() else o.get('rbr')}")

    def values(self):
        valdat, datpod, datdos = _get_date(self.f_valdat), _get_date(self.f_datpod), _get_date(self.f_datdos)
        for day, ctrl in ((valdat, self.f_valdat), (datdos, self.f_datdos), (datpod, self.f_datpod)):
            if day is None:
                ui.info(self, "ВНЕСЕТЕ ДАТУМ")
                ctrl.SetFocus()
                return None
        # Required by the old form: приходно конто, потпрограма, сметка и назив на примач, цел на дознака.
        for ctrl in (self.f_prihsif, self.f_progprim, self.f_smprim, self.f_nazprim1, self.f_cel1):
            if not ctrl.GetValue().strip():
                ui.info(self, "ВНЕСЕТЕ ВРЕДНОСТИ")
                ctrl.SetFocus()
                return None
        amount = self.amount()
        if amount is None:
            ui.info(self, "ВНЕСЕТЕ ИЗНОС")
            self.f_denari.SetFocus()
            return None
        values = {key: getattr(self, attr).GetValue().strip() for attr, key in self.COLUMNS}
        values["progzadolz"] = values["progzadolz"].upper()
        values["progprim"] = values["progprim"].upper()
        values.update(iznos=amount, valdat=valdat, datpod=datpod, datdos=datdos, dosdat=db.yyyymmdd(datdos))
        return values

    def insert_only_values(self):
        # No register lookup for 73: the old app wrote four spaces as the recipient code.
        return {"sifprim": ""}


class Nal76Dialog(OrderDialog):
    """НАЛОГ 76 — payments between the Treasury and the Fund's treasury (extracted/nal76_spec.md)."""

    VIDOBR = "76"
    TITLE = "БАРАЊЕ ЗА ПЛАЌАЊЕ\nпомеѓу Трезорот и Трезорот на Фондот"
    NACIN = "3"
    SHOW_EDB = True
    SHOW_POVIK = False
    FUND_RECIPIENT = True
    # Hard-coded in the old program as the recipient's transaction account (all 31 real 76 orders use it).
    FUND_ACCOUNT = "100000000066005"
    LABELS = {"trezsmet": "Трансакциска сметка", "smetbukor": "Сметка на буџетски корисник/ЈЗУ",
              "naziv": "Назив и седиште на корисник", "raskon": "Расходно конто / приходно конто", "prog": "Потпрограма"}

    def load(self, o):
        super().load(o)
        # The partner's budget account is stored in podsmetprim; smetprim holds the fixed Fund account.
        self.recipient["ziro"] = o.get("podsmetprim") or ""
        self.show_recipient()
        self.f_prihsif.SetValue(o.get("konprim") or "")
        self.f_progprim.SetValue(o.get("progprim") or "")

    def extra_values(self):
        return {
            "smetprim": self.FUND_ACCOUNT,
            "podsmetprim": (self.recipient or {}).get("ziro") or "",
            "konprim": self.f_prihsif.GetValue().strip(),
            "progprim": self.f_progprim.GetValue().strip().upper(),
            "smetzadolz": self.shipment["init"].get("trezsmet") or "",  # АЖУРИРАЈ rewrote it too
        }

    def insert_only_values(self):
        return {"edb": self.shipment["init"].get("edb") or ""}


FORMS = {"60": Nal60Dialog, "61": Nal61Dialog, "62": Nal62Dialog, "70": Nal70Dialog, "73": Nal73Dialog,
         "76": Nal76Dialog, "80": Nal80Dialog}


def mixing_error(vidobr, existing_types):
    """Which order types may share a shipment, or the message refusing it.

    Old app: 62 never mixed with other types. New app (user decision): 62 and 70 may share a shipment.
    """
    existing = set(existing_types)
    if vidobr == "62" and existing - {"62", "70"}:
        return "ВО ОВАА ПРАТКА ИМА ДРУГИ НАЛОЗИ"
    if vidobr not in ("62", "70") and "62" in existing:
        return "ВО ОВАА ПРАТКА ИМА НАЛОЗИ 62"
    return None
