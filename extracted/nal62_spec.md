# НАЛОГ 62 — payment to an employee (TNAL62)

Recovered from `forms/TNAL62.dfm`, `asm/TNAL62/` and the opener `TVNNAL.JvSpeedButton12Click`.
Same paper form and rules as Налог 60 (`nal60_spec.md`) except:

| | Налог 60 | Налог 62 |
|---|---|---|
| Recipient code | Шифра на партнер → `partneri` | **Вработен** → `lica` (`select * from lica where sifra=:sif`) |
| Unknown code | „НЕМА ТАКОВ ДЕЛОВЕН ПАРТНЕР" | „НЕМА ТАКОВ ВРАБОТЕН" |
| Empty code | opens the partner register | opens the employee register |
| Recipient account | `partneri.ziro` („Сметка на примач") | `lica.transak` („Трансакциона сметка") |
| Extra display | — | ЕМБГ = `lica.embg` |
| Extra saved column | — | `edb` = employee EMBG |
| `vidobr` | 60 | 62 |

Name/place: `lica.naziv` → `nazprim1`, `lica.mesto` → `nazprim2`.
Update SQL adds `edb=:edb` to the Налог 60 column list.

## Mixing order types in one shipment
Old app:
- opening 62 when the shipment has 60/61/70/73/76/80 → „ВО ОВАА ПРАТКА ИМА ДРУГИ НАЛОЗИ";
- opening any other type when the shipment has 62 → „ВО ОВАА ПРАТКА ИМА НАЛОЗИ 62".

**New app (user decision):** 62 and 70 may share a shipment; all other combinations with 62 stay refused
(`orders.mixing_error`).

New-app changes shared with Налог 60: Датум на доспевање required, deni always 00.
