"""
Utilidades para el etiquetado meteorológico con AEMET OpenData.

Solo usa la librería estándar.
"""

import math
import re

_DMS = re.compile(r"^\s*(\d{5,7})([NSEW])\s*$")


def dms_to_decimal(value):
    """Coordenada AEMET en grados-minutos-segundos -> grados decimales.

    El inventario de estaciones usa el formato [D]DDMMSS + hemisferio, p. ej.
    latitud '364000N' -> 36.6667 y longitud '042900W' -> -4.4833.
    Devuelve None si el valor no tiene ese formato.
    """
    if value is None:
        return None
    match = _DMS.match(str(value))
    if not match:
        return None

    digits, hemisphere = match.groups()
    degrees, minutes, seconds = int(digits[:-4]), int(digits[-4:-2]), int(digits[-2:])
    if minutes >= 60 or seconds >= 60:
        return None

    decimal = degrees + minutes / 60 + seconds / 3600
    return -decimal if hemisphere in "SW" else decimal


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos puntos (lat, lon) en grados."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def classify_weather(prec=None, vis=None, hr=None, wind=None, nub=None):
    """Etiqueta meteorológica a partir de una observación (la iluminación se trata aparte).

    Prioridad: rain > fog > windy > cloudy > sunny. Los valores None/NaN se ignoran.
    """
    def ok(x):
        return x is not None and not (isinstance(x, float) and math.isnan(x))

    if ok(prec) and prec > 0:
        return "rain"
    if (ok(vis) and vis < 1000) or (ok(hr) and hr >= 97):
        return "fog"
    if ok(wind) and wind >= 10:
        return "windy"
    if (ok(nub) and nub >= 6) or (ok(hr) and hr >= 85):
        return "cloudy"
    return "sunny"
