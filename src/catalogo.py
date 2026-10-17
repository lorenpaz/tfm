"""
Catálogo municipal de cámaras de tráfico (da_camarasTrafico-4326.csv).

TFM - Máster en Inteligencia Artificial
Autor: Lorenzo Jose de la Paz Suarez
"""

import re

import pandas as pd

from config import path

_POINT = re.compile(r"POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)")


def parse_point(geom):
    """(lat, lon) de una geometría WKT 'POINT (lon lat)', o (None, None)."""
    match = _POINT.search(geom) if isinstance(geom, str) else None
    if not match:
        return None, None
    lon, lat = float(match.group(1)), float(match.group(2))
    return lat, lon


def load_catalog(csv_path=None):
    """Catálogo con ID como texto, URLIMAGEN sin espacios/tabuladores y columnas lat/lon."""
    df = pd.read_csv(csv_path or path("catalogo"))
    df["ID"] = df["ID"].astype(str)
    # Algunas URL traen un tabulador final (p. ej. TV-132 -> 404)
    df["URLIMAGEN"] = df["URLIMAGEN"].astype("string").str.strip()
    coords = [parse_point(g) for g in df["SDOGEOMETRIA"]]
    df["lat"] = [c[0] for c in coords]
    df["lon"] = [c[1] for c in coords]
    return df
