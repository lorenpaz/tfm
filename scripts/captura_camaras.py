"""
Servicio de captura periódica de las cámaras de tráfico de Málaga.

Se ejecuta como servicio de Windows (NSSM, "CamarasMalaga"). Las cámaras, intervalos y
horas punta se leen de config.yaml (sección `captura`).

Los nombres de fichero y metadatos se guardan en UTC (sufijo Z) para evitar ambigüedades
en los cambios de hora. La hora local solo se usa para decidir las horas punta.
"""

import logging
import sys
import time

from datetime import datetime, timezone, time as dt_time
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from catalogo import load_catalog
from config import load_config, path
from tiempo import FILENAME_FORMAT, LOCAL_TZ

# =====================================================
# CONFIGURACIÓN
# =====================================================

CFG = load_config()["captura"]

BASE_DIR = path("datos")          # las rutas de metadatos son relativas a data/malaga
RAW_DIR = path("raw")
LOG_DIR = path("logs")
METADATA_DIR = path("metadata")

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

RAW_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

CAMERAS = {str(c) for c in CFG["camaras"]}
REQUEST_TIMEOUT = CFG["timeout_s"]

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    filename=LOG_DIR / "capturas.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt=ISO_FORMAT
)

# Marcas de tiempo del log también en UTC
logging.Formatter.converter = time.gmtime

logger = logging.getLogger(__name__)

# =====================================================
# SESIÓN HTTP
# =====================================================

session = requests.Session()

retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)

session.mount(
    "https://",
    HTTPAdapter(max_retries=retries)
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://malaga.eu",
    "Accept-Language": "es-ES,es;q=0.9"
}


# =====================================================
# HORARIO
# =====================================================

def parse_hhmm(value):
    hours, minutes = value.split(":")
    return dt_time(int(hours), int(minutes))


PEAK_RANGES = [(parse_hhmm(start), parse_hhmm(end)) for start, end in CFG["horas_punta"]]


def is_peak_hour():
    # Las horas punta se definen en hora local de Málaga
    now = datetime.now(LOCAL_TZ).time()

    return any(start <= now < end for start, end in PEAK_RANGES)


def get_capture_interval():
    return CFG["intervalo_punta_s"] if is_peak_hour() else CFG["intervalo_valle_s"]


# =====================================================
# DESCARGA
# =====================================================

def parse_last_modified(response):
    """Devuelve la cabecera Last-Modified del servidor en UTC (ISO) o None."""

    header = response.headers.get("Last-Modified")

    if not header:
        return None

    try:
        return parsedate_to_datetime(header).astimezone(timezone.utc).strftime(ISO_FORMAT)
    except (TypeError, ValueError):
        return None


def download_image(image_url, output_file):

    response = session.get(
        image_url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    output_file.write_bytes(response.content)

    return parse_last_modified(response)


# =====================================================
# CAPTURA
# =====================================================

def capture_camera(camera_row):

    camera_id = camera_row["ID"]
    camera_name = camera_row["NOMBRE"]
    image_url = camera_row["URLIMAGEN"]

    now_utc = datetime.now(timezone.utc)
    capture_time = now_utc.strftime(ISO_FORMAT)

    camera_dir = RAW_DIR / camera_id
    camera_dir.mkdir(exist_ok=True)

    image_file = camera_dir / f"{now_utc.strftime(FILENAME_FORMAT)}.jpg"

    try:

        server_last_modified = download_image(
            image_url,
            image_file
        )

        logger.info(
            f"OK - Cámara {camera_id} - {camera_name}"
        )

        return {
            "camera_id": camera_id,
            "camera_name": camera_name,
            "capture_time": capture_time,
            "server_last_modified": server_last_modified,
            "image_file": image_file.relative_to(BASE_DIR).as_posix(),
            "status": "OK"
        }

    except Exception as exc:

        logger.error(
            f"ERROR - Cámara {camera_id} - {exc}"
        )

        return {
            "camera_id": camera_id,
            "camera_name": camera_name,
            "capture_time": capture_time,
            "server_last_modified": None,
            "image_file": None,
            "status": str(exc)
        }


# =====================================================
# METADATOS
# =====================================================

def save_metadata(results):

    if not results:
        return

    metadata_file = (
        METADATA_DIR /
        f"capturas_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    )

    df = pd.DataFrame(results)

    if metadata_file.exists():
        df.to_csv(
            metadata_file,
            mode="a",
            header=False,
            index=False
        )
    else:
        df.to_csv(
            metadata_file,
            index=False
        )


# =====================================================
# CARGA CATÁLOGO
# =====================================================

def load_cameras():

    df = load_catalog()

    df = df[df["ID"].isin(CAMERAS)]

    logger.info(
        f"Cámaras seleccionadas: {len(df)}"
    )

    return df


# =====================================================
# BUCLE PRINCIPAL
# =====================================================

def main():

    logger.info("Servicio iniciado")

    cameras_df = load_cameras()

    while True:

        cycle_start = time.time()

        results = []

        logger.info("Inicio ciclo de captura")

        for _, row in cameras_df.iterrows():

            result = capture_camera(row)

            if result:
                results.append(result)

        save_metadata(results)

        interval = get_capture_interval()

        elapsed = time.time() - cycle_start

        sleep_time = max(1, interval - elapsed)

        logger.info(
            f"Fin ciclo. Próxima captura en {sleep_time:.1f} segundos"
        )

        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
