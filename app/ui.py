"""Small shared helpers for the wx screens."""
import datetime as dt

import wx

CAPTION = "ИНФОРМАЦИЈА"


def info(parent, text):
    wx.MessageBox(text, CAPTION, wx.OK | wx.ICON_INFORMATION, parent)


def confirm(parent, text):
    """OK / Не question, as the old app asked; True when confirmed."""
    dlg = wx.MessageDialog(parent, text, CAPTION, wx.OK | wx.CANCEL | wx.ICON_QUESTION)
    dlg.SetOKCancelLabels("ОК", "Не")
    try:
        return dlg.ShowModal() == wx.ID_OK
    finally:
        dlg.Destroy()


def money(value):
    """1500.1 -> '1.500,10' (Macedonian format, rounded to two decimals)."""
    text = f"{round(value or 0, 2):,.2f}"
    return text.replace(",", " ").replace(".", ",").replace(" ", ".")


def date_text(value):
    return value.strftime("%d.%m.%Y") if value else ""


def picker_date(picker) -> dt.date:
    d = picker.GetValue()
    return dt.date(d.GetYear(), d.GetMonth() + 1, d.GetDay())


def set_picker_date(picker, day: dt.date):
    picker.SetValue(wx.DateTime.FromDMY(day.day, day.month - 1, day.year))


def date_picker(parent):
    return wx.adv.DatePickerCtrl(parent, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
