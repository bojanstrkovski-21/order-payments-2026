r"""Check ПЕЧАТЕЊЕ: the three print-outs built from real shipments of a throwaway database copy.

Usage:  python -I tools\test_reports.py <settings.ini pointing at a throwaway copy>
"""
import re
import sys
from pathlib import Path

import wx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import db  # noqa: E402
import reports  # noqa: E402
import ui  # noqa: E402

db.SETTINGS = Path(sys.argv[1])


def check(name, condition):
    print(("OK   " if condition else "FAIL ") + name)
    assert condition, name


def body_rows(html):
    """Rows of the bordered data table, minus its column-header row and total row (the page header is a table too)."""
    table = html[html.index('<table border="1"'):]
    return len(re.findall(r"<tr>", table)) - 2


con = db.connect()
cur = con.cursor()
cur.execute("select p.pratka, p.datkniz, p.sifsmet, count(*), sum(case when p.vidobr='62' then 1 else 0 end) "
            "from promet p group by 1,2,3 order by 2 desc")
shipments = cur.fetchall()
con.close()
ordinary = next(s for s in shipments if s[4] == 0 and s[3] >= 3)
salary = next(s for s in shipments if s[4] == s[3] and s[3] >= 5)
init = db.get_init()


def context(s):
    return {"pratka": s[0].strip(), "day": s[1].date(), "account": db.get_account(s[2].strip()), "init": init}


app = wx.App()

# 1. Ordinary shipment: СПЕЦИФИКАЦИЈА of every order.
ctx, orders = context(ordinary), db.shipment_orders(ordinary[0], ordinary[1].date())
check("ordinary shipment is not salary-only", not reports.is_salary_only(orders))
html, landscape = reports.build(ctx, orders, "orders")
check(f"orders: one row per order ({len(orders)})", body_rows(html) == len(orders))
check("orders: total equals the shipment total", ui.money(sum(o["iznos"] for o in orders)) in html)
check("orders: header with company, shipment number and date, treasury code/account, sub-account",
      all(x in html for x in (init["naziv"], f'пратка бр. {ctx["pratka"]}', ui.date_text(ctx["day"]),
                              init["trzkodkor"], init["trezsmet"], ctx["account"]["smetbukor"])))
check("orders: portrait, signature line", not landscape and "О д о б р и л" in html)

# 2. Salary shipment: СПЕЦИФИКАЦИЈА grouped and СПИСОК per employee.
ctx, orders = context(salary), db.shipment_orders(salary[0], salary[1].date())
check("salary shipment is salary-only", reports.is_salary_only(orders))
groups = db.specification(orders)
check(f"specification counts every order ({len(orders)})", sum(g["broj"] for g in groups) == len(orders))
check("specification total equals the shipment total",
      abs(sum(g["vkupno"] for g in groups) - sum(o["iznos"] for o in orders)) < 0.005)
html, landscape = reports.build(ctx, orders, "specification")
check("specification: one row per group, portrait", body_rows(html) == len(groups) and not landscape)
check("specification: ledger account description shown", all(g["cel"] in html for g in groups if g["cel"]))
html, landscape = reports.build(ctx, orders, "list")
check(f"list: one row per employee ({len(orders)}), landscape", body_rows(html) == len(orders) and landscape)
check("list: names and transaction accounts shown",
      all(o["nazprim1"] in html and o["smetprim"] in html for o in orders[:5]))

# 3. The specification no longer misses orders whose value date differs from the shipment date.
con = db.connect()
cur = con.cursor()
cur.execute("select first 1 pratka, datkniz from promet where vidobr='62' and valdat<>datkniz and "
            "(brkniz is null or brkniz='')")
row = cur.fetchall()
if row:
    pratka, day = row[0][0], row[0][1].date()
    cur.execute("select count(*) from specif ((select first 1 sifsmet from promet where pratka=? and datkniz=?), ?, ?)",
                (pratka, day, pratka, day))
    old_groups = cur.fetchall()
    con.close()
    orders = db.shipment_orders(pratka, day)
    check("shipment with differing value dates: every order counted (old SPECIF would miss some)",
          sum(g["broj"] for g in db.specification(orders)) == len(orders))
else:
    con.close()

# 4. PDF export: open the written PDFs and check what they contain.
import tempfile  # noqa: E402

import pymupdf  # noqa: E402  (only used by this test to read the PDFs back)

with tempfile.TemporaryDirectory() as tmp:
    ctx, orders = context(ordinary), db.shipment_orders(ordinary[0], ordinary[1].date())
    path = Path(tmp) / "spec.pdf"
    reports.to_pdf(reports.shipment_report(ctx, orders, "orders"), path)
    doc = pymupdf.open(path)
    text = "".join(page.get_text() for page in doc)
    check("PDF: specification portrait, title, subtitle and company in Cyrillic",
          doc[0].rect.width < doc[0].rect.height and "С П Е Ц И Ф И К А Ц И Ј А" in text
          and f"пратка бр. {ctx['pratka']}" in text and init["naziv"] in text)
    check("PDF: every order amount and the total are in the text",
          all(ui.money(o["iznos"]) in text for o in orders) and ui.money(sum(o["iznos"] for o in orders)) in text)
    check("PDF: fonts embedded (opens the same on any PC)", all(f[1] != "n/a" for f in doc.get_page_fonts(0)))
    doc.close()

    ctx, orders = context(salary), db.shipment_orders(salary[0], salary[1].date())
    path = Path(tmp) / "list.pdf"
    reports.to_pdf(reports.shipment_report(ctx, orders, "list"), path)
    doc = pymupdf.open(path)
    text = "".join(page.get_text() for page in doc)
    check("PDF: list is landscape with the employees' names",
          doc[0].rect.width > doc[0].rect.height and all(o["nazprim1"] in text for o in orders[:5]))
    doc.close()

    big = next(s for s in shipments if s[4] == s[3] and s[3] >= 80)
    ctx, orders = context(big), db.shipment_orders(big[0], big[1].date())
    path = Path(tmp) / "big.pdf"
    reports.to_pdf(reports.shipment_report(ctx, orders, "list"), path)
    doc = pymupdf.open(path)
    pages = [page.get_text() for page in doc]
    check(f"PDF: {len(orders)} employees run over {len(pages)} pages with the column headings repeated and page numbers",
          len(pages) > 1 and all("Име и презиме" in p for p in pages) and f"Страна {len(pages)} / {len(pages)}" in pages[-1])
    check("PDF: total on the last page equals the shipment total", ui.money(sum(o["iznos"] for o in orders)) in pages[-1])
    doc.close()

print("all checks passed")
