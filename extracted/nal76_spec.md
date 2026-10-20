# НАЛОГ 76 — БАРАЊЕ ЗА ПЛАЌАЊЕ помеѓу Трезорот и Трезорот на Фондот (TNAL76)

Recovered from `forms/TNAL76.dfm`, `asm/TNAL76/` (`tools/param_map.py`) and the opener `TVNNAL.JvSpeedButton14Click`.
Same rules as Налог 60 (`nal60_spec.md`) except:

- Payer side: Трансакциска сметка (`init.trezsmet` → `smetzadolz`), Сметка на буџетски корисник/ЈЗУ (shipment account →
  `podsmetzadolz`), Назив и седиште на корисник, Расходно конто / приходно конто → `konzadolz`, Потпрограма → `progzadolz`,
  Единствен даночен број (`init.edb` → `edb`). No Повикување.
- Recipient: business partner — Сметка на буџетски корисник – примач = `partneri.ziro` → **`podsmetprim`**,
  Приходно конто → `konprim`, Потпрограма → `progprim`, name and place.
- **Трансакциска сметка на примач is hard-coded `100000000066005`** (the Fund's treasury) → `smetprim`.
  All 31 real 76 orders use it.
- Both „Уплатна сметка" boxes are dead (one never filled, the other editable but never saved): left out.
- Saved `nacin = '3'`, `vidobr = '76'`; dates as on Налог 60 (`datkniz` = shipment, `valdat` = form) — all 31 real
  orders have valdat = datkniz.
- АЖУРИРАЈ also rewrites `smetzadolz` and `smetprim`; `edb` is not rewritten.
- Mixing: refused in a shipment with 62 orders.
