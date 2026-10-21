"""Print-outs: described once (Report), written as HTML for the wx print preview / Windows printers and as PDF.

User rule: every print-out can be printed (Windows dialog, any installed printer) and saved as PDF by the program.

Shipment print-outs (old TVNNAL QuickRep1/2/3):
- Спецификација на налози (QuickRep1): every order — for shipments with ordinary orders.
- Спецификација (QuickRep2): salary shipments (only 62) — totals per type, ledger account, programme and bank.
- Список (QuickRep3, landscape): salary shipments — one row per employee.
"""
import logging
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

import wx
import wx.html
from fpdf import FPDF
from fpdf.fonts import FontFace

import db
import ui

SALARY = "62"
FONT_DIR = Path(r"C:\Windows\Fonts")
logging.getLogger("fontTools.subset").setLevel(logging.ERROR)  # harmless notes while embedding Segoe UI


@dataclass
class Report:
    title: str
    subtitle: str = ""                       # e.g. „на трезорски налози од пратка бр. 6 за ден 05.10.2026"
    company: str = ""
    details: list = field(default_factory=list)   # (label, value) lines under the title
    columns: list = field(default_factory=list)   # (heading, align 'L'/'C'/'R', width %)
    rows: list = field(default_factory=list)      # cells; a cell may contain '\n'
    totals: list = field(default_factory=list)    # cells of the total row ('' where empty)
    landscape: bool = False
    signature: bool = True


def is_salary_only(orders):
    return bool(orders) and all(o["vidobr"] == SALARY for o in orders)


def _shipment_report(ctx, title, with_accounts=True, landscape=False):
    init, account = ctx["init"], ctx["account"]
    details = []
    if with_accounts:
        details = [("ТРЕЗОРСКИ КОД НА КОРИСНИК:", init.get("trzkodkor") or ""),
                   ("ТРЕЗОРСКА СМЕТКА:", init.get("trezsmet") or ""),
                   ("ПОДСМЕТКА НА КОРИСНИК:", account.get("smetbukor") or "")]
    return Report(title=title, company=init.get("naziv") or "", details=details, landscape=landscape,
                  subtitle=f"на трезорски налози од пратка бр. {ctx['pratka']} за ден {ui.date_text(ctx['day'])}")


def orders_report(ctx, orders):
    """СПЕЦИФИКАЦИЈА на трезорски налози — every order of the shipment (QuickRep1)."""
    r = _shipment_report(ctx, "СПЕЦИФИКАЦИЈА")
    r.columns = [("Р.бр.", "R", 5), ("Цел на дознака", "L", 32), ("Расх. конто", "C", 9), ("Прог-\nрама", "C", 6),
                 ("Назив на примач\nЖиро-сметка и подсметка", "L", 27), ("Прих. конто", "C", 8), ("Износ", "R", 13)]
    r.rows = [[str(n), f"{o['celdoz1'] or ''}\n{o['celdoz2'] or ''}".strip(), o["konzadolz"] or "", o["progzadolz"] or "",
               f"{o['nazprim1'] or ''}\n{o['smetprim'] or ''} {o['podsmetprim'] or ''}".strip(), o["konprim"] or "",
               ui.money(o["iznos"])] for n, o in enumerate(orders, 1)]
    r.totals = ["", "", "", "", "", "Вкупен износ", ui.money(sum(o["iznos"] or 0 for o in orders))]
    return r


def salary_specification_report(ctx, orders):
    """СПЕЦИФИКАЦИЈА of a salary shipment — grouped totals (QuickRep2)."""
    groups = db.specification(orders)
    r = _shipment_report(ctx, "СПЕЦИФИКАЦИЈА")
    r.columns = [("Р.бр.", "R", 6), ("Образец", "C", 9), ("Цел на дознака", "L", 30), ("Конто", "C", 10),
                 ("Програма", "C", 9), ("Водечки бр.\nна банка", "C", 11), ("Број на\nналози", "R", 10), ("Износ", "R", 15)]
    r.rows = [[str(n), g["vidobr"], g["cel"], g["konz"], g["progz"], g["banka"], str(g["broj"]), ui.money(g["vkupno"])]
              for n, g in enumerate(groups, 1)]
    r.totals = ["", "", "", "", "", "Вкупно", str(sum(g["broj"] for g in groups)), ui.money(sum(g["vkupno"] for g in groups))]
    return r


def salary_list_report(ctx, orders):
    """СПИСОК of a salary shipment — one row per employee (QuickRep3, landscape)."""
    r = _shipment_report(ctx, "СПИСОК", with_accounts=False, landscape=True)
    r.columns = [("Р.бр.", "R", 5), ("Шифра", "C", 7), ("Име и презиме", "L", 25), ("Трансакциона сметка", "L", 17),
                 ("Цел на дознака", "L", 33), ("Износ", "R", 13)]
    r.rows = [[str(n), o["sifprim"] or "", o["nazprim1"] or "", o["smetprim"] or "", o["celdoz1"] or "", ui.money(o["iznos"])]
              for n, o in enumerate(orders, 1)]
    r.totals = ["", "", "", "", "Вкупен износ", ui.money(sum(o["iznos"] or 0 for o in orders))]
    return r


def shipment_report(ctx, orders, kind):
    """kind: 'orders', 'specification' or 'list'."""
    return {"list": salary_list_report, "specification": salary_specification_report}.get(kind, orders_report)(ctx, orders)


# ----- writers -------------------------------------------------------------------------------------------------
_ALIGN = {"L": "left", "C": "center", "R": "right"}


def _cell_html(text):
    return escape(text).replace("\n", "<br>")


def to_html(r: Report) -> str:
    """HTML for wx.html printing. Fixed column widths: wx HTML does not wrap long texts without spaces."""
    parts = []
    if r.company:
        parts.append(f'<p><font size="+1"><b>{escape(r.company)}</b></font></p>')
    parts.append(f'<p align="center"><font size="+2"><b>{" ".join(r.title)}</b></font><br>{escape(r.subtitle)}</p>')
    if r.details:
        parts.append('<table cellpadding="1">' + "".join(
            f"<tr><td>{escape(label)}</td><td><b>{escape(value)}</b></td></tr>" for label, value in r.details) + "</table>")
    head = "".join(f'<th align="{_ALIGN[a]}" width="{w}%">{_cell_html(t)}</th>' for t, a, w in r.columns)
    body = "".join("<tr>" + "".join(f'<td align="{_ALIGN[a]}" valign="top"><font size="-1">{_cell_html(c)}</font></td>'
                                    for (_, a, _), c in zip(r.columns, row)) + "</tr>" for row in r.rows)
    foot = ""
    if r.totals:
        label = next(i for i, c in enumerate(r.totals) if c)  # merge the empty cells before the label into it
        foot = (f'<tr><td colspan="{label + 1}" align="right"><b>{_cell_html(r.totals[label])}</b></td>'
                + "".join(f'<td align="{_ALIGN[a]}"><b>{_cell_html(c)}</b></td>'
                          for (_, a, _), c in zip(r.columns[label + 1:], r.totals[label + 1:])) + "</tr>")
    parts.append(f'<br><table border="1" cellpadding="3" cellspacing="0" width="100%"><tr>{head}</tr>{body}{foot}</table>')
    if r.signature:
        parts.append('<br><br><p align="right">О д о б р и л<br><br>______________________</p>')
    return "".join(parts)


class _Pdf(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("ui", size=8)
        self.cell(0, 6, f"Страна {self.page_no()} / {{nb}}", align="R")


def to_pdf(r: Report, path) -> None:
    """Write the print-out as a PDF (A4, landscape when the report is), with Cyrillic fonts from Windows."""
    pdf = _Pdf(orientation="L" if r.landscape else "P", unit="mm", format="A4")
    pdf.add_font("ui", "", str(FONT_DIR / "segoeui.ttf"))
    pdf.add_font("ui", "B", str(FONT_DIR / "segoeuib.ttf"))
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(True, margin=16)
    pdf.add_page()
    if r.company:
        pdf.set_font("ui", "B", 12)
        pdf.cell(0, 7, r.company, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("ui", "B", 15)
    pdf.cell(0, 8, " ".join(r.title), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("ui", "", 10)
    pdf.cell(0, 6, r.subtitle, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    for label, value in r.details:
        pdf.set_font("ui", "", 9)
        pdf.cell(62, 5, label)
        pdf.set_font("ui", "B", 9)
        pdf.cell(0, 5, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    widths = [w for _, _, w in r.columns]
    aligns = [_ALIGN[a].upper() for _, a, _ in r.columns]
    pdf.set_font("ui", "", 8)
    bold = FontFace(emphasis="BOLD")
    with pdf.table(col_widths=widths, text_align=aligns, line_height=4.2, padding=1.2,
                   headings_style=FontFace(emphasis="BOLD", fill_color=(235, 235, 235)), repeat_headings=1) as table:
        heading = table.row()
        for title, _, _ in r.columns:
            heading.cell(title)
        for cells in r.rows:
            row = table.row()
            for c in cells:
                row.cell(c)
        if r.totals:
            # The empty cells before the label are merged into it, so „Вкупен износ" has room.
            label = next(i for i, c in enumerate(r.totals) if c)
            row = table.row()
            row.cell(r.totals[label], style=bold, colspan=label + 1, align="R")
            for c in r.totals[label + 1:]:
                row.cell(c, style=bold)
    if r.signature:
        pdf.ln(10)
        pdf.set_font("ui", "", 10)
        pdf.cell(0, 6, "О д о б р и л", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)
        pdf.cell(0, 6, "______________________", align="R")
    pdf.output(str(path))


def build(ctx, orders, kind):
    """(html, landscape) — kept for the wx print path and the tests."""
    r = shipment_report(ctx, orders, kind)
    return to_html(r), r.landscape


# ----- dialog and actions ----------------------------------------------------------------------------------------
ID_PDF = wx.NewIdRef()


class PrintDialog(wx.Dialog):
    """ПЕЧАТЕЊЕ: which print-out (salary shipments only), copies; Печати or Сними како PDF."""

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
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for button_id, label in ((wx.ID_OK, "Печати"), (ID_PDF, "Сними како PDF"), (wx.ID_CANCEL, "Откажи")):
            button = wx.Button(self, button_id, label)
            button.Bind(wx.EVT_BUTTON, lambda e, i=button_id: self.EndModal(i))
            buttons.Add(button, 0, wx.LEFT, 8)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 12)
        self.SetSizerAndFit(sizer)

    def values(self):
        if self.kind is None:
            return "orders", self.copies.GetValue()
        return ("list" if self.kind.GetSelection() == 0 else "specification"), self.copies.GetValue()


def preview(parent, report: Report, copies=1):
    """Print preview with a Print button; printing goes through the Windows dialog (any installed printer)."""
    printer = wx.html.HtmlEasyPrinting("Печатење", parent)
    data = printer.GetPrintData()
    data.SetNoCopies(copies)
    data.SetOrientation(wx.LANDSCAPE if report.landscape else wx.PORTRAIT)
    printer.SetFonts("Segoe UI", "Consolas", [7, 8, 9, 10, 12, 14, 16])
    printer.SetFooter('<p align="right"><font size="-1">Страна @PAGENUM@ / @PAGESCNT@</font></p>')
    printer.PreviewText(to_html(report))
    return printer


def save_pdf(parent, report: Report, default_name: str) -> bool:
    """Ask where to save and write the PDF; True when saved."""
    dlg = wx.FileDialog(parent, "Сними како PDF", defaultFile=default_name, wildcard="PDF (*.pdf)|*.pdf",
                        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return False
        path = dlg.GetPath()
    finally:
        dlg.Destroy()
    to_pdf(report, path)
    return True
