"""
Marcas de tiempo: nombres de fichero en UTC, hora local, franjas, tipo de día e iluminación.

Convención del proyecto:
- Nombres de fichero y columna `timestamp`: UTC (datetime naive).
- Columna `timestamp_local`: hora de Madrid (datetime naive), usada para franjas y tipo de día.

TFM - Máster en Inteligencia Artificial
Autor: Lorenzo Jose de la Paz Suarez
"""

import csv
import math
import re

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/Madrid")
FILENAME_FORMAT = "%Y%m%dT%H%M%SZ"

_UTC_NAME = re.compile(r"(20\d{6})T(\d{6})Z")


def parse_timestamp_from_name(filename):
    """Marca de tiempo UTC (naive) codificada en el nombre del fichero (20260825T144834Z.jpg), o None."""
    stem = Path(filename).stem

    match = _UTC_NAME.search(stem)
    if match:
        try:
            return datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")
        except ValueError:
            return None

    return None


def to_local(ts_utc):
    """UTC (naive) -> hora local de Madrid (naive)."""
    if ts_utc is None:
        return None
    return ts_utc.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ).replace(tzinfo=None)


def time_slot_2h(ts_local):
    """Franja horaria de 2 horas ('16:00-18:00') a partir de la hora local."""
    if ts_local is None:
        return "unknown"
    start = (ts_local.hour // 2) * 2
    return f"{start:02d}:00-{(start + 2) % 24:02d}:00"


def day_type(ts_local, holidays):
    """'festivo', 'fin_de_semana' o 'laborable' a partir de la hora local."""
    if ts_local is None:
        return "unknown"
    if ts_local.date() in holidays:
        return "festivo"
    if ts_local.weekday() >= 5:
        return "fin_de_semana"
    return "laborable"


def load_holidays(csv_path):
    """Fechas festivas del calendario (primera columna con nombre fecha/date o la primera columna)."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return set()

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        column = next((c for c in columns if c.strip().lower() in ("fecha", "date", "dia", "day")), columns[0])
        holidays = set()
        for row in reader:
            value = (row.get(column) or "").strip()
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    holidays.add(datetime.strptime(value, fmt).date())
                    break
                except ValueError:
                    continue
    return holidays


def solar_elevation(ts_utc, lat, lon):
    """Elevación del sol en grados (algoritmo aproximado de la NOAA, error < 1º)."""
    day_of_year = ts_utc.timetuple().tm_yday
    hour = ts_utc.hour + ts_utc.minute / 60 + ts_utc.second / 3600
    gamma = 2 * math.pi / 365 * (day_of_year - 1 + (hour - 12) / 24)

    eq_time = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                        - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))

    true_solar_minutes = hour * 60 + eq_time + 4 * lon
    hour_angle = math.radians(true_solar_minutes / 4 - 180)
    lat_rad = math.radians(lat)

    cos_zenith = (math.sin(lat_rad) * math.sin(decl)
                  + math.cos(lat_rad) * math.cos(decl) * math.cos(hour_angle))
    return 90 - math.degrees(math.acos(max(-1.0, min(1.0, cos_zenith))))


def illumination(ts_utc, lat, lon, twilight_elevation=-6):
    """'dia', 'crepusculo' o 'noche' según la elevación solar (independiente del clima)."""
    if ts_utc is None:
        return "unknown"
    elevation = solar_elevation(ts_utc, lat, lon)
    if elevation > 0:
        return "dia"
    if elevation > twilight_elevation:
        return "crepusculo"
    return "noche"
