"""ШИФРАРНИК — registers (old TGEN „ГЕНЕРАЛИИ", TTRZSM „СМЕТКИ", …). Behaviour: extracted/registers_spec.md.

New fields the old program lacked (user decisions): institution ЕМБС and three e-mail addresses,
a name for every account.
"""
import wx

import db
import reports
import ui


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
            ctrl.SetValue((init.get(key) or "").strip())

    def values(self):
        v = {k: c.GetValue().strip() for k, c in self.f.items()}
        v["telefon"] = _digits(v["telefon"])  # the old form stored the phone as 9 digits
        v["trzkodkor"], v["trzinskod"] = v["trzkodkor"].upper(), v["trzinskod"].upper()
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
