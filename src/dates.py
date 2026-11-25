"""Göreli Türkçe tarih ifadelerini toplantı tarihine göre mutlak tarihe çevirir."""
import re
from datetime import date, timedelta

DAYS = {"pazartesi": 0, "salı": 1, "çarşamba": 2, "perşembe": 3, "cuma": 4, "cumartesi": 5, "pazar": 6}

def resolve(text: str, meeting: date):
    t = text.lower()
    if "bugün" in t: return meeting
    if "öbür gün" in t or "ertesi gün" in t: return meeting + timedelta(days=2)
    if "yarın" in t: return meeting + timedelta(days=1)
    m = re.search(r"(\d+)\s*gün\s*(sonra|içinde)", t)
    if m: return meeting + timedelta(days=int(m.group(1)))
    for name, wd in DAYS.items():
        if name in t:
            monday = meeting - timedelta(days=meeting.weekday())
            if "haftaya" in t or "gelecek hafta" in t or "önümüzdeki hafta" in t:
                return monday + timedelta(days=7 + wd)
            d = meeting + timedelta(days=(wd - meeting.weekday()) % 7)
            return d if d > meeting else d + timedelta(days=7)
    if "haftaya" in t or "gelecek hafta" in t: return meeting + timedelta(days=7)
    return None
