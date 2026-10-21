"""ПЕЧАТЕЊЕ — the three print-outs of a shipment (old TVNNAL QuickRep1/2/3), as HTML for wx print preview.

- Спецификација на налози (QuickRep1): every order — for shipments with ordinary orders.
- Спецификација (QuickRep2): salary shipments (only 62) — totals per type, ledger account, programme and bank.
- Список (QuickRep3, landscape): salary shipments — one row per employee.
"""
from html import escape

import wx
import wx.html

import db
import ui

SALARY = "62"


def is_salary_only(orders):
    return bool(orders) and all(o["vidobr"] == SALARY for o in orders)


def _e(value):
    return escape(str(value or ""))


def _header(ctx, title, with_accounts=True):
    pratka, day = ctx["pratka"], ctx["day"]
    init, account = ctx["init"], ctx["account"]
    parts = [
        f'<p><font size="+1"><b>{_e(init.get("naziv"))}</b></font></p>',
        f'<p align="center"><font size="+2"><b>{" ".join(title)}</b></font><br>',
        f'на трезорски налози од пратка бр. <b>{_e(pratka)}</b> за ден <b>{ui.date_text(day)}</b></p>',
    ]
    if with_accounts:
        parts.append(
            '<table cellpadding="1">'
            f'<tr><td>ТРЕЗОРСКИ КОД НА КОРИСНИК:</td><td><b>{_e(init.get("trzkodkor"))}</b></td></tr>'
            f'<tr><td>ТРЕЗОРСКА СМЕТКА:</td><td><b>{_e(init.get("trezsmet"))}</b></td></tr>'
            f'<tr><td>ПОДСМЕТКА НА КОРИСНИК:</td><td><b>{_e(account.get("smetbukor"))}</b></td></tr>'
            "</table>"
        )
    return "".join(parts)


def _table(columns, rows, total_label, total, total_colspan, extra_total=None):
    """columns: (title, align, width %). Fixed widths: wx HTML does not wrap long texts without spaces
    (e.g. „/ОБ/2550427126/Р/01/превозни"), so the purpose column must be wide enough."""
    head = "".join(f'<th align="{a}" width="{w}%">{t}</th>' for t, a, w in columns)
    body = "".join("<tr>" + "".join(f'<td align="{a}" valign="top"><font size="-1">{c}</font></td>'
                                    for (_, a, _), c in zip(columns, r)) + "</tr>"
                   for r in rows)
    trailing = len(columns) - total_colspan - 1 - (1 if extra_total is not None else 0)
    foot = (f'<tr><td colspan="{total_colspan}" align="right"><b>{total_label}</b></td>'
            + (f'<td align="right"><b>{extra_total}</b></td>' if extra_total is not None else "")
            + f'<td align="right"><b>{ui.money(total)}</b></td>' + ("<td></td>" * trailing) + "</tr>")
    return f'<table border="1" cellpadding="3" cellspacing="0" width="100%"><tr>{head}</tr>{body}{foot}</table>'


SIGNATURE = '<br><br><p align="right">О д о б р и л<br><br>______________________</p>'


def orders_html(ctx, orders):
    """СПЕЦИФИКАЦИЈА на трезорски налози — every order of the shipment (QuickRep1)."""
    columns = [("Р.бр.", "right", 5), ("Цел на дознака", "left", 32), ("Расх. конто", "center", 9),
               ("Прог-<br>рама", "center", 6), ("Назив на примач<br>Жиро-сметка и подсметка", "left", 27),
               ("Прих. конто", "center", 8), ("Износ", "right", 13)]
    rows = [(n, f'{_e(o["celdoz1"])}<br>{_e(o["celdoz2"])}', _e(o["konzadolz"]), _e(o["progzadolz"]),
             f'{_e(o["nazprim1"])}<br>{_e(o["smetprim"])} {_e(o["podsmetprim"])}', _e(o["konprim"]), ui.money(o["iznos"]))
            for n, o in enumerate(orders, 1)]
    total = sum(o["iznos"] or 0 for o in orders)
    return (_header(ctx, "СПЕЦИФИКАЦИЈА") + "<br>" + _table(columns, rows, "Вкупен износ", total, 6) + SIGNATURE)


def salary_specification_html(ctx, orders):
    """СПЕЦИФИКАЦИЈА of a salary shipment — grouped totals (QuickRep2)."""
    groups = db.specification(orders)
    columns = [("Р.бр.", "right", 6), ("Образец", "center", 9), ("Цел на дознака", "left", 30), ("Конто", "center", 10),
               ("Програма", "center", 9), ("Водечки бр.<br>на банка", "center", 11), ("Број на<br>налози", "right", 10),
               ("Износ", "right", 15)]
    rows = [(n, _e(g["vidobr"]), _e(g["cel"]), _e(g["konz"]), _e(g["progz"]), _e(g["banka"]), g["broj"],
             ui.money(g["vkupno"])) for n, g in enumerate(groups, 1)]
    total = sum(g["vkupno"] for g in groups)
    return (_header(ctx, "СПЕЦИФИКАЦИЈА") + "<br>"
            + _table(columns, rows, "Вкупно", total, 6, extra_total=sum(g["broj"] for g in groups)) + SIGNATURE)


def salary_list_html(ctx, orders):
    """СПИСОК of a salary shipment — one row per employee (QuickRep3, landscape)."""
    columns = [("Р.бр.", "right", 5), ("Шифра", "center", 7), ("Име и презиме", "left", 25),
               ("Трансакциона сметка", "left", 17), ("Цел на дознака", "left", 33), ("Износ", "right", 13)]
    rows = [(n, _e(o["sifprim"]), _e(o["nazprim1"]), _e(o["smetprim"]), _e(o["celdoz1"]), ui.money(o["iznos"]))
            for n, o in enumerate(orders, 1)]
    total = sum(o["iznos"] or 0 for o in orders)
    return _header(ctx, "СПИСОК", with_accounts=False) + "<br>" + _table(columns, rows, "Вкупен износ", total, 5) + SIGNATURE


def build(ctx, orders, kind):
    """(html, landscape) for kind 'orders', 'specification' or 'list'."""
    if kind == "list":
        return salary_list_html(ctx, orders), True
    if kind == "specification":
        return salary_specification_html(ctx, orders), False
    return orders_html(ctx, orders), False


class PrintDialog(wx.Dialog):
    """ПЕЧАТЕЊЕ: which print-out (salary shipments only) and how many copies."""

    def __init__(self, parent, salary_only):
        super().__init__(parent, title="Печатење")
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.kind = None
        if salary_only:
            self.kind = wx.RadioBox(self, label="Вид", choices=["Список", "Спецификација"])
            sizer.Add(self.kind, 0, wx.EXPAND | wx.ALL, 12)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label="Број на копии:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.copies = wx.SpinCtrl(self, min=1, max=99, initial=1, size=(70, -1))
        row.Add(self.copies, 0)
        sizer.Add(row, 0, wx.ALL, 12)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 12)
        self.FindWindowById(wx.ID_OK).SetLabel("Печати")
        self.FindWindowById(wx.ID_CANCEL).SetLabel("Откажи")
        self.SetSizerAndFit(sizer)

    def values(self):
        if self.kind is None:
            return "orders", self.copies.GetValue()
        return ("list" if self.kind.GetSelection() == 0 else "specification"), self.copies.GetValue()


def preview(parent, ctx, orders, kind, copies):
    """Open the print preview (with its Print button) for the chosen print-out."""
    html, landscape = build(ctx, orders, kind)
    printer = wx.html.HtmlEasyPrinting("Печатење", parent)
    data = printer.GetPrintData()
    data.SetNoCopies(copies)
    data.SetOrientation(wx.LANDSCAPE if landscape else wx.PORTRAIT)
    printer.SetFonts("Segoe UI", "Consolas", [7, 8, 9, 10, 12, 14, 16])
    printer.SetFooter('<p align="right"><font size="-1">Страна @PAGENUM@ / @PAGESCNT@</font></p>')
    printer.PreviewText(html)
    return printer
