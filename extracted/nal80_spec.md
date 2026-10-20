# НАЛОГ 80 — БАРАЊЕ ЗА ИСПЛАТА НА ГОТОВИНА (TNAL80)

Recovered from `forms/TNAL80.dfm`, `asm/TNAL80/` (`tools/param_map.py` on `dodaj` and `JvXPButton4Click`).
Same rules as Налог 60 (`nal60_spec.md`) except:

- Recipient: business partner (`partneri`), shown as name and place, **Број на лична карта на примач** (`partneri.brlk`)
  and **Единствен матичен број на примач** (`partneri.embg`). No recipient account, no Повикување.
- Purpose label „Цел на исплата".
- Saved: `smetprim = init.trezsmet` (the treasury account — true for all 61 orders since 2020), `edb = embg`,
  `povik1 = brlk`, **`nacin = '3'`**, `vidobr = '80'`. The insert binds `:podsmetprim` into `edb` — only a parameter name;
  the value is the recipient EMBG.
- АЖУРИРАЈ updates the same columns as Налог 60 plus `edb` and `povik1`.
- `Edit9`/`Edit10` on the old form are never filled by any code: left out.

`brlk` is MAC C text like `povik1` (the old app showed it in the MAC C font); the new app shows it converted in both
the register and the order, and stores the original bytes.
