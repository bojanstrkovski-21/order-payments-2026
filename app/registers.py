"""ШИФРАРНИК — registers (old TGEN „ГЕНЕРАЛИИ", TTRZSM „СМЕТКИ", …). Behaviour: extracted/registers_spec.md.

New fields the old program lacked (user decisions): institution ЕМБС and three e-mail addresses,
a name for every account.
"""
import wx

import db
import konta
import reports
import ui
import uplatni


def _row(parent, grid, label, ctrl):
    grid.Add(wx.StaticText(parent, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
    grid.Add(ctrl, 0, wx.EXPAND)
    return ctrl


def _text(parent, length, width=-1):
    ctrl = wx.TextCtrl(parent, size=(width, -1))
    ctrl.SetMaxLength(length)
    return ctrl


def _digits(value):
    return "".join(ch for ch in value if ch.isdigit())


class GeneralDialog(wx.Dialog):
    """ГЕНЕРАЛИИ — the institution (single INIT row): old fields plus ЕМБС and e-mail addresses."""

    def __init__(self, parent):
        super().__init__(parent, title="Генералии — податоци за институцијата")
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        grid.AddGrowableCol(1)
        self.f = {
            "naziv": _row(self, grid, "Назив на вашата институција:", _text(self, 35, 330)),
            "adresa": _row(self, grid, "Адреса:", _text(self, 35)),
            "mesto": _row(self, grid, "Место:", _text(self, 20)),
            "telefon": _row(self, grid, "Телефон:", _text(self, 9, 120)),
            "edb": _row(self, grid, "ЕДБ:", _text(self, 13, 150)),
            "embs": _row(self, grid, "ЕМБС:", _text(self, 10, 150)),
            "trezsmet": _row(self, grid, "Трезорска сметка:", _text(self, 15, 170)),
            "trzkan": _row(self, grid, "Трезорска канцеларија:", _text(self, 20)),
            "trzkodkor": _row(self, grid, "Трезорски код на корисник:", _text(self, 3, 60)),
            "trzinskod": _row(self, grid, "Код на трезорска институција:", _text(self, 3, 60)),
            "opstina": _row(self, grid, "Основна општина (шифра):", _text(self, 3, 60)),
        }
        mail = wx.StaticBoxSizer(wx.VERTICAL, self, "Е-пошта")
        mgrid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        mgrid.AddGrowableCol(1)
        box = mail.GetStaticBox()
        self.f["email1"] = _row(box, mgrid, "Училиште (1):", _text(box, 100, 300))
        self.f["email2"] = _row(box, mgrid, "Училиште (2):", _text(box, 100))
        self.f["email_fin"] = _row(box, mgrid, "Финансии и сметководство:", _text(box, 100))
        mail.Add(mgrid, 0, wx.EXPAND | wx.ALL, 8)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 14)
        sizer.Add(mail, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)
        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self.FindWindowById(wx.ID_OK).SetLabel("Памти")
        self.FindWindowById(wx.ID_CANCEL).SetLabel("Откажи")
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 14)
        self.SetSizerAndFit(sizer)
        self.FindWindowById(wx.ID_OK).Bind(wx.EVT_BUTTON, self.on_save)
        init = db.get_init()
        for key, ctrl in self.f.items():
            value = (init.get(key) or "").strip()
            if key == "opstina" and not value:
                value = db.DEFAULT_OPSTINA
            ctrl.SetValue(value)

    def values(self):
        v = {k: c.GetValue().strip() for k, c in self.f.items()}
        v["telefon"] = _digits(v["telefon"])  # the old form stored the phone as 9 digits
        v["trzkodkor"], v["trzinskod"] = v["trzkodkor"].upper(), v["trzinskod"].upper()
        v["opstina"] = "".join(c for c in v.get("opstina", "") if c.isdigit())[:3]
        return v

    def check(self, v):
        """Message for the first wrong value, or None."""
        for key, label in (("edb", "ЕДБ"), ("trezsmet", "Трезорска сметка"), ("embs", "ЕМБС")):
            if v[key] and not v[key].isdigit():
                return f"{label} СОДРЖИ САМО ЦИФРИ"
        for key in ("email1", "email2", "email_fin"):
            address = v[key]
            if address and ("@" not in address or " " in address or "." not in address.split("@")[-1]):
                return f"НЕИСПРАВНА Е-ПОШТА: {address}"
        if not v["naziv"]:
            return "ВНЕСЕТЕ ВРЕДНОСТИ"
        return None

    def on_save(self, event):
        v = self.values()
        problem = self.check(v)
        if problem:
            ui.info(self, problem)
            return
        db.save_init(v)
        self.EndModal(wx.ID_OK)


class AccountDialog(wx.Dialog):
    """One account: code, name (new), budget account, sub-account."""

    def __init__(self, parent, account=None):
        super().__init__(parent, title="Нова сметка" if account is None else "Измена на сметка")
        self.account = account
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        grid.AddGrowableCol(1)
        self.f_sifra = _row(self, grid, "Шифра:", _text(self, 2, 50))
        self.f_naziv = _row(self, grid, "Назив на сметката:", _text(self, 60, 300))
        self.f_smet = _row(self, grid, "Сметка на буџетски корисник:", _text(self, 15, 170))
        self.f_podsmet = _row(self, grid, "Подсметка на корисник:", _text(self, 15, 170))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 14)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 14)
        self.FindWindowById(wx.ID_OK).SetLabel("Памти")
        self.FindWindowById(wx.ID_CANCEL).SetLabel("Откажи")
        self.SetSizerAndFit(sizer)
        self.FindWindowById(wx.ID_OK).Bind(wx.EVT_BUTTON, self.on_save)
        if account:
            self.f_sifra.SetValue(account["sifra"] or "")
            self.f_naziv.SetValue(account.get("naziv") or "")
            self.f_smet.SetValue((account["smetbukor"] or "").strip())
            self.f_podsmet.SetValue((account["podsbukor"] or "").strip())

    def values(self):
        return {"sifra": self.f_sifra.GetValue().strip(), "naziv": self.f_naziv.GetValue().strip(),
                "smetbukor": self.f_smet.GetValue().strip().upper(), "podsbukor": self.f_podsmet.GetValue().strip().upper()}

    def on_save(self, event):
        v = self.values()
        if not (v["sifra"].isdigit() and len(v["sifra"]) == 2) or not v["smetbukor"]:
            ui.info(self, "ВНЕСЕТЕ ВРЕДНОСТИ (шифра од 2 цифри и сметка)")
            return
        try:
            db.save_account(v, old_code=self.account["sifra"] if self.account else None)
        except ValueError as problem:
            ui.info(self, str(problem))
            return
        self.EndModal(wx.ID_OK)


class AccountsDialog(wx.Dialog):
    """СМЕТКИ — the institution's accounts: list, add, edit, delete, search, print / PDF."""

    COLUMNS = [("Шифра", "sifra", 60), ("Назив", "naziv", 230), ("Сметка", "smetbukor", 150),
               ("Подсметка", "podsbukor", 150)]

    def __init__(self, parent, pick=False):
        """pick=True: choose an account (the shipment screen opens this when the code is left empty)."""
        super().__init__(parent, title="Сметки", size=(720, 520), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.pick = pick
        self.search = wx.SearchCtrl(self)
        self.search.SetDescriptiveText("Барај по шифра, назив или сметка")
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        for i, (title, _, width) in enumerate(self.COLUMNS):
            self.list.InsertColumn(i, title, width=width)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        specs = [("Додавање", self.on_add), ("Измена", self.on_edit), ("Бришење", self.on_delete),
                 ("Печатење", self.on_print)]
        if pick:
            specs.append(("Избери", lambda e: self.EndModal(wx.ID_OK) if self.selected() else None))
        specs.append(("Излез", lambda e: self.EndModal(wx.ID_CANCEL)))
        for label, handler in specs:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.search, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(buttons, 0, wx.ALL, 8)
        self.SetSizer(sizer)
        self.search.Bind(wx.EVT_TEXT, lambda e: self.fill())
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda e: self.EndModal(wx.ID_OK) if pick else self.on_edit(e))
        self.accounts, self.shown = [], []
        self.reload()

    def reload(self):
        self.accounts = db.list_accounts()
        self.fill()

    def fill(self):
        needle = self.search.GetValue().strip().lower()
        self.shown = [a for a in self.accounts
                      if not needle or any(needle in (a.get(k) or "").lower() for _, k, _ in self.COLUMNS)]
        self.list.DeleteAllItems()
        for a in self.shown:
            self.list.Append([(a.get(k) or "").strip() for _, k, _ in self.COLUMNS])
        if self.shown:
            self.list.Select(0)

    def selected(self):
        index = self.list.GetFirstSelected()
        return self.shown[index] if index >= 0 else None

    def on_add(self, event):
        self._edit(None)

    def on_edit(self, event):
        if self.selected():
            self._edit(self.selected())

    def _edit(self, account):
        dlg = AccountDialog(self, account)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.reload()
        finally:
            dlg.Destroy()

    def on_delete(self, event):
        account = self.selected()
        if not account:
            return
        used = db.account_in_use(account["sifra"])
        if used:
            ui.info(self, f"СМЕТКАТА СЕ КОРИСТИ ВО {used} НАЛОЗИ И КНИЖЕЊА — НЕ МОЖЕ ДА СЕ ИЗБРИШЕ")
            return
        if ui.confirm(self, "ОВОЈ ЗАПИС ЌЕ БИДЕ ИЗБРИШАН"):
            db.delete_account(account["sifra"])
            self.reload()

    def report(self):
        return reports.Report(
            title="СМЕТКИ", company=(db.get_init().get("naziv") or ""), subtitle="список на сметки на институцијата",
            columns=[("Шифра", "C", 10), ("Назив", "L", 44), ("Сметка", "L", 23), ("Подсметка", "L", 23)],
            rows=[[(a.get(k) or "").strip() for _, k, _ in self.COLUMNS] for a in self.accounts], signature=False)

    def on_print(self, event):
        reports.print_or_pdf(self, self.report(), "Сметки.pdf")


class KontoDialog(wx.Dialog):
    """One konto: code, full official name (new) and the 30-character short form (old OPIS)."""

    def __init__(self, parent, konto=None):
        super().__init__(parent, title="Ново конто" if konto is None else "Измена на конто")
        self.konto = konto
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        grid.AddGrowableCol(1)
        self.f_konto = _row(self, grid, "Конто:", _text(self, 6, 80))
        self.f_full = _row(self, grid, "Целосен назив:", _text(self, konta.FULL_LEN, 520))
        self.f_short = _row(self, grid, "Кратко (за печатење, до 30 знаци):", _text(self, konta.OPIS_LEN, 280))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 14)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 14)
        self.FindWindowById(wx.ID_OK).SetLabel("Памти")
        self.FindWindowById(wx.ID_CANCEL).SetLabel("Откажи")
        self.SetSizerAndFit(sizer)
        self.FindWindowById(wx.ID_OK).Bind(wx.EVT_BUTTON, self.on_save)
        self.short_by_hand = False
        if konto:
            self.f_konto.SetValue(konto["konto"])
            self.f_full.SetValue(konto["naziv"])
            self.f_short.SetValue(konto["opis"].strip())
            self.short_by_hand = True   # keep the stored short form until the full name is edited
        self.f_full.Bind(wx.EVT_TEXT, self.on_full_changed)
        self.f_short.Bind(wx.EVT_TEXT, self.on_short_changed)

    def on_full_changed(self, event):
        """The short form follows the full name (cut at a word boundary) until it is typed by hand."""
        if not self.short_by_hand:
            self.f_short.ChangeValue(konta.short_name(self.f_full.GetValue()))
        event.Skip()

    def on_short_changed(self, event):
        short = self.f_short.GetValue()
        self.short_by_hand = bool(short.strip()) and short != konta.short_name(self.f_full.GetValue())
        event.Skip()

    def values(self):
        full = " ".join(self.f_full.GetValue().split())
        short = " ".join(self.f_short.GetValue().split()) or konta.short_name(full)
        return {"konto": self.f_konto.GetValue().strip(), "opis": short, "opisfull": full or short}

    def on_save(self, event):
        v = self.values()
        if not (v["konto"].isdigit() and len(v["konto"]) == 6) or not v["opis"]:
            ui.info(self, "ВНЕСЕТЕ ВРЕДНОСТИ (конто од 6 цифри и назив)")
            return
        try:
            db.save_konto(v, old_code=self.konto["konto"] if self.konto else None)
        except ValueError as problem:
            ui.info(self, str(problem))
            return
        self.EndModal(wx.ID_OK)


class KontaDialog(wx.Dialog):
    """КОНТА — expense (class 4) and revenue (class 7) codes: search by code or name, add, edit, delete, print / PDF.
    The search looks in the full name, so the right konto is easy to find when filling an order."""

    CLASSES = [("Сите конта", None), ("Расходи (класа 4)", "4"), ("Приходи (класа 7)", "7")]

    def __init__(self, parent, pick=False):
        """pick=True: choose a konto for an order (the dialog returns wx.ID_OK and selected())."""
        super().__init__(parent, title="Конта", size=(980, 600), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.pick = pick
        top = wx.BoxSizer(wx.HORIZONTAL)
        self.search = wx.SearchCtrl(self)
        self.search.SetDescriptiveText("Барај по конто или назив")
        self.kind = wx.Choice(self, choices=[label for label, _ in self.CLASSES])
        self.kind.SetSelection(0)
        top.Add(self.search, 1, wx.RIGHT, 8)
        top.Add(self.kind, 0)
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.InsertColumn(0, "Конто", width=70)
        self.list.InsertColumn(1, "Назив", width=650)
        self.list.InsertColumn(2, "Кратко (печатење)", width=200)
        self.count = wx.StaticText(self)
        self.detail = wx.StaticText(self, style=wx.ST_NO_AUTORESIZE, size=(-1, 58))   # full name of the selected konto
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        specs = [("Додавање", self.on_add), ("Измена", self.on_edit), ("Бришење", self.on_delete),
                 ("Печатење", self.on_print)]
        if pick:
            specs.append(("Избери", lambda e: self.EndModal(wx.ID_OK) if self.selected() else None))
        specs.append(("Излез", lambda e: self.EndModal(wx.ID_CANCEL)))
        for label, handler in specs:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(self.count, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(top, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.detail, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.SetSizer(sizer)
        self.search.Bind(wx.EVT_TEXT, lambda e: self.fill())
        self.kind.Bind(wx.EVT_CHOICE, lambda e: self.fill())
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda e: self.show_detail())
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda e: self.EndModal(wx.ID_OK) if pick else self.on_edit(e))
        self.konta, self.shown = [], []
        self.reload()

    def reload(self):
        self.konta = db.list_konta()
        self.fill()

    def fill(self):
        needle = " ".join(self.search.GetValue().lower().split())
        wanted = self.CLASSES[self.kind.GetSelection()][1]
        self.shown = [k for k in self.konta
                      if (wanted is None or konta.konto_class(k["konto"]) == wanted)
                      and (not needle or needle in k["konto"] or needle in k["naziv"].lower()
                           or needle in k["opis"].lower())]
        self.list.DeleteAllItems()
        for k in self.shown:
            self.list.Append([k["konto"], k["naziv"], k["opis"].strip()])
        self.count.SetLabel(f"{len(self.shown)} од {len(self.konta)}")
        if self.shown:
            self.list.Select(0)
        self.show_detail()

    def show_detail(self):
        konto = self.selected()
        self.detail.SetLabel(f"{konto['konto']}  {konto['naziv']}" if konto else "")
        self.detail.Wrap(self.detail.GetSize().width)

    def selected(self):
        index = self.list.GetFirstSelected()
        return self.shown[index] if index >= 0 else None

    def on_add(self, event):
        self._edit(None)

    def on_edit(self, event):
        if self.selected():
            self._edit(self.selected())

    def _edit(self, konto):
        dlg = KontoDialog(self, konto)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.reload()
        finally:
            dlg.Destroy()

    def on_delete(self, event):
        konto = self.selected()
        if not konto:
            return
        used = db.konto_in_use(konto["konto"])
        if used:
            ui.info(self, f"КОНТОТО СЕ КОРИСТИ ВО {used} НАЛОЗИ — НЕ МОЖЕ ДА СЕ ИЗБРИШЕ")
            return
        if ui.confirm(self, "ОВОЈ ЗАПИС ЌЕ БИДЕ ИЗБРИШАН"):
            db.delete_konto(konto["konto"])
            self.reload()

    def report(self):
        """The list as filtered on screen (class and search), with the full names."""
        search = self.search.GetValue().strip()
        return reports.Report(
            title="КОНТА", company=(db.get_init().get("naziv") or ""),
            subtitle=self.kind.GetStringSelection().lower() + (f" — „{search}“" if search else ""),
            columns=[("Конто", "C", 12), ("Назив", "L", 88)],
            rows=[[k["konto"], k["naziv"]] for k in self.shown], signature=False)

    def on_print(self, event):
        reports.print_or_pdf(self, self.report(), "Конта.pdf")


class OpstinaDialog(wx.Dialog):
    """One municipality: 3-digit code and name."""

    def __init__(self, parent, opstina=None):
        super().__init__(parent, title="Општина" if opstina else "Нова општина")
        self.opstina = opstina
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        grid.AddGrowableCol(1)
        self.f_sifra = _row(self, grid, "Шифра:", _text(self, 3, 60))
        self.f_naziv = _row(self, grid, "Назив:", _text(self, 40, 320))
        if opstina:
            self.f_sifra.SetValue((opstina.get("sifra") or "").strip())
            self.f_naziv.SetValue((opstina.get("naziv") or "").strip())
        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.ALL | wx.EXPAND, 12)
        sizer.Add(buttons, 0, wx.ALL | wx.EXPAND, 12)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.FindWindowById(wx.ID_OK).Bind(wx.EVT_BUTTON, self.on_save)

    def values(self):
        return {"sifra": self.f_sifra.GetValue().strip(), "naziv": self.f_naziv.GetValue().strip()}

    def on_save(self, event):
        v = self.values()
        try:
            db.save_opstina(v, old_code=self.opstina["sifra"] if self.opstina else None)
        except ValueError as problem:
            ui.info(self, str(problem))
            return
        self.EndModal(wx.ID_OK)


class OpstiniDialog(wx.Dialog):
    """ОПШТИНИ — municipalities (ministry codes): search, add, edit, delete, print / PDF.
    pick=True returns the selected row via .chosen after OK.
    """

    COLUMNS = [("Шифра", "sifra", 70), ("Назив", "naziv", 280)]

    def __init__(self, parent, pick=False):
        super().__init__(parent, title="Општини", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.pick = pick
        self.chosen = None
        self.rows = []
        self.shown = []
        self.search = wx.SearchCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.search.SetDescriptiveText("барај шифра или назив…")
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        for i, (title, _key, width) in enumerate(self.COLUMNS):
            self.list.InsertColumn(i, title, width=width)
        self.count = wx.StaticText(self, label="")
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        specs = [("Нов", self.on_new), ("Измена", self.on_edit), ("Бришење", self.on_delete),
                 ("Печати", self.on_print), ("PDF", self.on_pdf)]
        if pick:
            specs = [("Избери", self.on_pick)] + specs
        for label, handler in specs:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(self.count, 0, wx.ALIGN_CENTER_VERTICAL)
        close = wx.Button(self, wx.ID_CANCEL, label="Затвори")
        buttons.Add(close, 0, wx.LEFT, 12)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.search, 0, wx.ALL | wx.EXPAND, 8)
        sizer.Add(self.list, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        sizer.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        self.SetSizer(sizer)
        self.SetSize((520, 480))
        self.CentreOnParent()
        self.search.Bind(wx.EVT_TEXT, lambda e: self.fill())
        self.search.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, lambda e: self.fill())
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_activate)
        self.reload()

    def reload(self):
        self.rows = db.list_opstini()
        self.fill()

    def fill(self):
        needle = self.search.GetValue().strip().lower()
        self.shown = [r for r in self.rows
                      if not needle or needle in (r.get("sifra") or "").lower()
                      or needle in (r.get("naziv") or "").lower()]
        self.list.DeleteAllItems()
        for r in self.shown:
            i = self.list.InsertItem(self.list.GetItemCount(), (r.get("sifra") or "").strip())
            self.list.SetItem(i, 1, (r.get("naziv") or "").strip())
        self.count.SetLabel(f"{len(self.shown)} / {len(self.rows)}")

    def selected(self):
        i = self.list.GetFirstSelected()
        return self.shown[i] if i >= 0 else None

    def on_new(self, event):
        dlg = OpstinaDialog(self)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.reload()
        finally:
            dlg.Destroy()

    def on_edit(self, event):
        row = self.selected()
        if not row:
            ui.info(self, "Изберете општина.")
            return
        self._edit(row)

    def on_activate(self, event):
        if self.pick:
            self.on_pick(event)
        else:
            row = self.selected()
            if row:
                self._edit(row)

    def _edit(self, row):
        dlg = OpstinaDialog(self, row)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.reload()
        finally:
            dlg.Destroy()

    def on_delete(self, event):
        row = self.selected()
        if not row:
            ui.info(self, "Изберете општина.")
            return
        if not ui.confirm(self, f"Да се избрише општина {row['sifra']} — {row['naziv']}?"):
            return
        try:
            db.delete_opstina(row["sifra"])
        except ValueError as problem:
            ui.info(self, str(problem))
            return
        self.reload()

    def on_pick(self, event):
        row = self.selected()
        if not row:
            ui.info(self, "Изберете општина.")
            return
        self.chosen = row
        self.EndModal(wx.ID_OK)

    def report(self):
        return reports.Report(
            title="ОПШТИНИ",
            company=(db.get_init().get("naziv") or ""),
            subtitle="шифри на општини",
            columns=[("Шифра", "C", 10), ("Назив", "L", 50)],
            rows=[[(r.get("sifra") or "").strip(), (r.get("naziv") or "").strip()] for r in self.shown],
            signature=False,
        )

    def on_print(self, event):
        reports.print_or_pdf(self, self.report(), "Opstini.pdf")

    def on_pdf(self, event):
        reports.print_or_pdf(self, self.report(), "Opstini.pdf")



class UplatnaDialog(wx.Dialog):
    """One payment account: banka (3), kod (5), naziv, linked prihoden konto."""

    def __init__(self, parent, row=None):
        super().__init__(parent, title="Уплатна сметка" if row else "Нова уплатна сметка")
        self.row = row
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        grid.AddGrowableCol(1)
        self.f_banka = _row(self, grid, "Банка:", _text(self, 3, 60))
        self.f_kod = _row(self, grid, "Код:", _text(self, 5, 80))
        self.f_naziv = _row(self, grid, "Назив:", _text(self, 0, 420))
        self.f_konto = _row(self, grid, "Конто:", _text(self, 6, 80))
        if row:
            self.f_banka.SetValue((row.get("banka") or "").strip())
            self.f_kod.SetValue((row.get("kod") or "").strip())
            self.f_naziv.SetValue((row.get("naziv") or "").strip())
            self.f_konto.SetValue((row.get("konto") or "").strip())
        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.ALL | wx.EXPAND, 12)
        sizer.Add(buttons, 0, wx.ALL | wx.EXPAND, 12)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.FindWindowById(wx.ID_OK).Bind(wx.EVT_BUTTON, self.on_save)

    def values(self):
        return {
            "banka": self.f_banka.GetValue().strip(),
            "kod": self.f_kod.GetValue().strip(),
            "naziv": self.f_naziv.GetValue().strip(),
            "konto": self.f_konto.GetValue().strip(),
        }

    def on_save(self, event):
        v = self.values()
        try:
            db.save_uplatna(
                v,
                old_banka=self.row["banka"] if self.row else None,
                old_kod=self.row["kod"] if self.row else None,
            )
        except ValueError as problem:
            ui.info(self, str(problem))
            return
        self.EndModal(wx.ID_OK)


class UplatniDialog(wx.Dialog):
    """УПЛАТНИ СМЕТКИ — search, add, edit, delete, print / PDF.
    pick=True returns the selected row via .chosen after OK (for Налог 61/70).
    """

    COLUMNS = [("Шифра", "code", 100), ("Назив", "naziv", 420), ("Конто", "konto", 80)]

    def __init__(self, parent, pick=False):
        super().__init__(
            parent, title="Уплатни сметки",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.pick = pick
        self.chosen = None
        self.rows = []
        self.shown = []
        self.search = wx.SearchCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.search.SetDescriptiveText("барај шифра, назив или конто…")
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        for i, (title, _key, width) in enumerate(self.COLUMNS):
            self.list.InsertColumn(i, title, width=width)
        self.detail = wx.StaticText(self, label="")
        self.detail.Wrap(760)
        self.count = wx.StaticText(self, label="")
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        specs = [
            ("Нов", self.on_new), ("Измена", self.on_edit), ("Бришење", self.on_delete),
            ("Печати", self.on_print), ("PDF", self.on_pdf),
        ]
        if pick:
            specs = [("Избери", self.on_pick)] + specs
        for label, handler in specs:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(self.count, 0, wx.ALIGN_CENTER_VERTICAL)
        close = wx.Button(self, wx.ID_CANCEL, label="Затвори")
        buttons.Add(close, 0, wx.LEFT, 12)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.search, 0, wx.ALL | wx.EXPAND, 8)
        sizer.Add(self.list, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        sizer.Add(self.detail, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 8)
        sizer.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        self.SetSizer(sizer)
        self.SetSize((900, 560))
        self.CentreOnParent()
        self.search.Bind(wx.EVT_TEXT, lambda e: self.fill())
        self.search.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, lambda e: self.fill())
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_activate)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select)
        self.reload()

    @staticmethod
    def _code(row):
        return uplatni.format_code(row.get("banka") or "", row.get("kod") or "")

    def reload(self):
        self.rows = db.list_uplatni()
        self.fill()

    def fill(self):
        needle = self.search.GetValue().strip().lower()
        self.shown = []
        for r in self.rows:
            code = self._code(r)
            blob = " ".join([
                code, r.get("banka") or "", r.get("kod") or "",
                r.get("naziv") or "", r.get("konto") or "",
            ]).lower()
            if not needle or needle in blob:
                self.shown.append(r)
        self.list.DeleteAllItems()
        for r in self.shown:
            i = self.list.InsertItem(self.list.GetItemCount(), self._code(r))
            self.list.SetItem(i, 1, (r.get("naziv") or "").strip())
            self.list.SetItem(i, 2, (r.get("konto") or "").strip())
        self.count.SetLabel(f"{len(self.shown)} / {len(self.rows)}")
        self.detail.SetLabel("")

    def selected(self):
        i = self.list.GetFirstSelected()
        return self.shown[i] if i >= 0 else None

    def on_select(self, event):
        row = self.selected()
        if not row:
            self.detail.SetLabel("")
            return
        self.detail.SetLabel(f"{self._code(row)}  {(row.get('naziv') or '').strip()}")

    def on_new(self, event):
        dlg = UplatnaDialog(self)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.reload()
        finally:
            dlg.Destroy()

    def on_edit(self, event):
        row = self.selected()
        if not row:
            ui.info(self, "Изберете уплатна сметка.")
            return
        self._edit(row)

    def on_activate(self, event):
        if self.pick:
            self.on_pick(event)
        else:
            row = self.selected()
            if row:
                self._edit(row)

    def _edit(self, row):
        dlg = UplatnaDialog(self, row)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.reload()
        finally:
            dlg.Destroy()

    def on_delete(self, event):
        row = self.selected()
        if not row:
            ui.info(self, "Изберете уплатна сметка.")
            return
        code = self._code(row)
        if not ui.confirm(self, f"Да се избрише уплатна сметка {code}?"):
            return
        try:
            db.delete_uplatna(row["banka"], row["kod"])
        except ValueError as problem:
            ui.info(self, str(problem))
            return
        self.reload()

    def on_pick(self, event):
        row = self.selected()
        if not row:
            ui.info(self, "Изберете уплатна сметка.")
            return
        self.chosen = row
        self.EndModal(wx.ID_OK)

    def report(self):
        return reports.Report(
            title="УПЛАТНИ СМЕТКИ",
            company=(db.get_init().get("naziv") or ""),
            subtitle="уплатни сметки (банкарски кодови)",
            columns=[("Шифра", "C", 14), ("Назив", "L", 70), ("Конто", "C", 10)],
            rows=[
                [self._code(r), (r.get("naziv") or "").strip(), (r.get("konto") or "").strip()]
                for r in self.shown
            ],
            signature=False,
        )

    def on_print(self, event):
        reports.print_or_pdf(self, self.report(), "Uplatni.pdf")

    def on_pdf(self, event):
        reports.print_or_pdf(self, self.report(), "Uplatni.pdf")
