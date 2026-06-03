"""
Utility functions — yordamchi funksiyalar
"""
import math
import datetime


def haversine(lat1, lon1, lat2, lon2) -> float:
    """Ikki koordinata orasidagi masofani hisoblash (km)"""
    if None in (lat1, lon1, lat2, lon2):
        return 0.0
    R = 6371  # Yer radiusi km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def timedelta_to_str(td) -> str | None:
    """timedelta ni "HH:MM" formatga o'girish"""
    if td is None:
        return None
    if isinstance(td, datetime.timedelta):
        total = int(td.total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        return f"{h:02d}:{m:02d}"
    return str(td)


def serialize_datetime(obj: dict, keys: list[str]) -> dict:
    """Dict ichidagi datetime fieldlarni ISO formatga o'girish"""
    for k in keys:
        if obj.get(k) and hasattr(obj[k], "isoformat"):
            obj[k] = obj[k].isoformat()
    return obj
