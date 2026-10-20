"""Default Датум на валута: the next working day after Датум на поднесување.

Non-working days (user rules):
- Saturdays and Sundays;
- fixed holidays every year (FIXED);
- holidays tied to Orthodox Easter, calculated: Велики Петок, Велигден Monday, Духовден (Friday before Pentecost);
- dates listed in holidays.txt — Рамазан Бајрам each year (it follows the lunar calendar) and any extra day;
- the Monday after any holiday that falls on a Sunday.
The user can always change the date by hand.
"""
import datetime as dt
from pathlib import Path

HOLIDAYS_FILE = Path(__file__).with_name("holidays.txt")

FIXED = {
    (1, 1): "Нова Година",
    (6, 1): "Бадник",
    (7, 1): "Божик",
    (1, 5): "Ден на трудот",
    (24, 5): "Св. Кирил и Методиј",
    (2, 8): "Ден на Републиката",
    (28, 8): "Успение на Пресвета Богородица (Голема Богородица)",
    (8, 9): "Ден на независноста",
    (11, 10): "Ден на народното востание",
    (23, 10): "Ден на македонската револуционерна борба",
    (8, 12): "Св. Климент Охридски",
    (31, 12): "Стара Година",
}


def orthodox_easter(year: int) -> dt.date:
    """Orthodox Easter Sunday (Julian computus, Meeus), as a Gregorian date (valid 1900–2099)."""
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month, day = divmod(d + e + 114, 31)
    return dt.date(year, month, day + 1) + dt.timedelta(days=13)


def easter_holidays(year: int) -> dict:
    easter = orthodox_easter(year)
    return {
        easter - dt.timedelta(days=2): "Велики Петок",
        easter + dt.timedelta(days=1): "Велигден, вториот ден",
        easter + dt.timedelta(days=47): "Духовден, петок пред Духовден",
    }


def listed_days():
    """Dates from holidays.txt: one dd.mm.yyyy per line; text after # and empty lines are ignored."""
    if not HOLIDAYS_FILE.exists():
        return set()
    days = set()
    for number, line in enumerate(HOLIDAYS_FILE.read_text(encoding="utf-8").splitlines(), 1):
        text = line.split("#")[0].strip()
        if text:
            try:
                days.add(dt.datetime.strptime(text, "%d.%m.%Y").date())
            except ValueError:
                raise ValueError(f'{HOLIDAYS_FILE.name}, ред {number}: „{text}" не е датум (dd.mm.yyyy)') from None
    return days


def holidays(year: int) -> set:
    days = {dt.date(year, month, day) for day, month in FIXED}
    days |= set(easter_holidays(year))
    days |= {d for d in listed_days() if d.year == year}
    return days


def non_working_days(year: int) -> set:
    """Holidays of the year plus the Monday after a holiday that falls on a Sunday."""
    days = holidays(year) | {d for d in holidays(year - 1) if d.month == 12}  # a Sunday 31.12 -> Monday 01.01
    return days | {d + dt.timedelta(days=1) for d in days if d.weekday() == 6}


def is_working_day(day: dt.date) -> bool:
    return day.weekday() < 5 and day not in non_working_days(day.year)


def next_working_day(after: dt.date) -> dt.date:
    day = after + dt.timedelta(days=1)
    while not is_working_day(day):
        day += dt.timedelta(days=1)
    return day
