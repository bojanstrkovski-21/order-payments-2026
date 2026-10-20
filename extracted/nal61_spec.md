# НАЛОГ 61 — БАРАЊЕ ЗА ПЛАЌАЊЕ НА ПРИДОНЕСИ КОН ФОНДОВИТЕ (TNAL61)

Recovered from `forms/TNAL61.dfm`, `asm/TNAL61/` (`tools/param_map.py`). No 61 order exists in the data.
Same rules as Налог 60 (`nal60_spec.md`) except:

- Payer side shows Трезорска сметка **and** Единствен даночен број (`init.edb`).
- Recipient: business partner — **Сметка на примач** (`ziro`), name and place; then **Уплатна сметка** (15 digits)
  and **Приходна шифра** (6 digits). No recipient programme, no Повикување.
- Old app: **no Датум на доспевање field**, `datdos`/`dosdat` never written.
  **New app (user decision): the field is added and optional** — empty → `datdos` NULL, `dosdat` '' (as the old app
  stored an empty due date on the other forms); filled → saved and updated like on the other forms.
- Saved: `edb = init.edb`, `podsmetprim = Уплатна сметка`, `konprim = Приходна шифра`, **`nacin = '3'`**, `vidobr = '61'`.
- АЖУРИРАЈ: `konzadolz, progzadolz, celdoz1, celdoz2, smetprim, nazprim1, nazprim2, podsmetprim, konprim, iznos, datpod,
  mespod, valdat, sifprim` — not `edb`.
- Mixing: refused in a shipment with 62 orders („ВО ОВАА ПРАТКА ИМА НАЛОЗИ 62").
