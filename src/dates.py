"""Göreli Türkçe ve İngilizce tarih ifadelerini toplantı tarihine göre mutlak tarihe çevirir."""
import re
from datetime import date, timedelta

DAYS = {
    "pazartesi": 0, "salı": 1, "çarşamba": 2, "perşembe": 3, "cuma": 4, "cumartesi": 5, "pazar": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
}

def resolve(text: str, meeting: date):
    t = text.lower()
    if "bugün" in t or "today" in t: return meeting
    if "öbür gün" in t or "ertesi gün" in t or "day after tomorrow" in t: return meeting + timedelta(days=2)
    if "yarın" in t or "tomorrow" in t: return meeting + timedelta(days=1)
    
    m = re.search(r"(\d+)\s*(?:gün|days?)\s*(?:sonra|içinde|later)?", t)
    if m: return meeting + timedelta(days=int(m.group(1)))
    
    for name, wd in DAYS.items():
        if name in t:
            monday = meeting - timedelta(days=meeting.weekday())
            if any(w in t for w in ["haftaya", "gelecek hafta", "önümüzdeki hafta", "next week", "next"]):
                return monday + timedelta(days=7 + wd)
            d = meeting + timedelta(days=(wd - meeting.weekday()) % 7)
            return d if d > meeting else d + timedelta(days=7)
            
    if any(w in t for w in ["haftaya", "gelecek hafta", "next week"]): return meeting + timedelta(days=7)
    return None
