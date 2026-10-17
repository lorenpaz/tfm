"""
Servicio de captura periódica de las cámaras de tráfico de Málaga.

Se ejecuta como servicio de Windows (NSSM, "CamarasMalaga"). Las cámaras, intervalos y
horas punta se leen de config.yaml (sección `captura`):

- Cámaras normales: cada `intervalo_punta_s` en hora punta y `intervalo_valle_s` el resto.
- Cámaras de alta frecuencia (`alta_frecuencia`): cada `intervalo_s` (6 s, el refresco medido
  de las cámaras), solo en hora punta si `solo_hora_punta` es true. Permite medir duraciones
  de fase semafórica.

Cada cámara se planifica por separado y las descargas pendientes se hacen en paralelo, para
que las cámaras de alta frecuencia no esperen a las demás.

Los nombres de fichero y metadatos se guardan en UTC (sufijo Z) para evitar ambigüedades
en los cambios de hora. La hora local solo se usa para decidir las horas punta.
"""

import logging
import sys
import threading
import time

from concurrent.futures import ThreadPoolExecutor
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

HIGH_FREQ = CFG.get("alta_frecuencia", {})
HIGH_FREQ_CAMERAS = {str(c) for c in HIGH_FREQ.get("camaras", [])}
HIGH_FREQ_INTERVAL = HIGH_FREQ.get("intervalo_s", 6)
HIGH_FREQ_ONLY_PEAK = HIGH_FREQ.get("solo_hora_punta", True)
DISCARD_UNCHANGED = CFG.get("descartar_sin_cambios", True)

SUMMARY_EVERY_S = 60              # una línea de resumen por minuto en el log

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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://malaga.eu",
    "Accept-Language": "es-ES,es;q=0.9"
}

# Una sesión por hilo: requests.Session no garantiza ser segura entre hilos
_local = threading.local()


def get_session():

    if not hasattr(_local, "session"):

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

        _local.session = session

    return _local.session


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


def get_capture_interval(camera_id):
    """Segundos hasta la siguiente captura de una cámara."""

    peak = is_peak_hour()

    if camera_id in HIGH_FREQ_CAMERAS and (peak or not HIGH_FREQ_ONLY_PEAK):
        return HIGH_FREQ_INTERVAL

    return CFG["intervalo_punta_s"] if peak else CFG["intervalo_valle_s"]


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


def download_image(image_url):

    response = get_session().get(
        image_url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    return response.content, parse_last_modified(response)


# =====================================================
# CAPTURA
# =====================================================

def capture_camera(camera_row, previous_last_modified):

    camera_id = camera_row["ID"]
    camera_name = camera_row["NOMBRE"]
    image_url = camera_row["URLIMAGEN"]

    now_utc = datetime.now(timezone.utc)
    capture_time = now_utc.strftime(ISO_FORMAT)

    result = {
        "camera_id": camera_id,
        "camera_name": camera_name,
        "capture_time": capture_time,
        "server_last_modified": None,
        "image_file": None,
        "status": None
    }

    try:

        content, server_last_modified = download_image(image_url)
        result["server_last_modified"] = server_last_modified

        # La cámara aún no ha publicado una imagen nueva: no se guarda un duplicado
        if (
            DISCARD_UNCHANGED
            and server_last_modified is not None
            and server_last_modified == previous_last_modified
        ):
            result["status"] = "SIN_CAMBIOS"
            return result

        camera_dir = RAW_DIR / camera_id
        camera_dir.mkdir(exist_ok=True)

        image_file = camera_dir / f"{now_utc.strftime(FILENAME_FORMAT)}.jpg"
        image_file.write_bytes(content)

        result["image_file"] = image_file.relative_to(BASE_DIR).as_posix()
        result["status"] = "OK"

    except Exception as exc:

        logger.error(
            f"ERROR - Cámara {camera_id} - {exc}"
        )

        result["status"] = str(exc)

    return result


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
        f"Cámaras seleccionadas: {len(df)} "
        f"(alta frecuencia: {sorted(HIGH_FREQ_CAMERAS & set(df['ID']))} cada {HIGH_FREQ_INTERVAL} s"
        f"{' en hora punta' if HIGH_FREQ_ONLY_PEAK else ''})"
    )

    return df


# =====================================================
# BUCLE PRINCIPAL
# =====================================================

def main():

    logger.info("Servicio iniciado")

    cameras = {row["ID"]: row for _, row in load_cameras().iterrows()}

    # Próxima captura (reloj monótono), descarga en curso y último Last-Modified de cada cámara
    next_due = {camera_id: 0.0 for camera_id in cameras}
    in_flight = {}
    last_modified = {}

    summary = {"OK": 0, "SIN_CAMBIOS": 0, "ERROR": 0}
    last_summary = time.monotonic()

    with ThreadPoolExecutor(max_workers=12) as pool:

        while True:

            # 1) Recoger las descargas terminadas. Una descarga lenta (algunas tardan varios
            #    segundos) solo retrasa a su propia cámara, no a las demás.
            results = []
            for camera_id in [c for c, future in in_flight.items() if future.done()]:
                result = in_flight.pop(camera_id).result()
                if result["server_last_modified"]:
                    last_modified[camera_id] = result["server_last_modified"]
                status = result["status"] if result["status"] in ("OK", "SIN_CAMBIOS") else "ERROR"
                summary[status] += 1
                results.append(result)

            save_metadata(results)

            # 2) Lanzar las capturas pendientes (sin solapar dos de la misma cámara). La siguiente
            #    se programa desde el inicio de esta para mantener la cadencia.
            now = time.monotonic()
            for camera_id, due_time in next_due.items():
                if due_time <= now and camera_id not in in_flight:
                    next_due[camera_id] = now + get_capture_interval(camera_id)
                    in_flight[camera_id] = pool.submit(
                        capture_camera, cameras[camera_id], last_modified.get(camera_id)
                    )

            if time.monotonic() - last_summary >= SUMMARY_EVERY_S:
                logger.info(
                    f"Último minuto: {summary['OK']} capturas, {summary['SIN_CAMBIOS']} sin cambios, "
                    f"{summary['ERROR']} errores | hora punta: {is_peak_hour()}"
                )
                summary = dict.fromkeys(summary, 0)
                last_summary = time.monotonic()

            # Revisa al menos cada 0,5 s si han terminado descargas
            time.sleep(max(0.05, min(0.5, min(next_due.values()) - time.monotonic())))


if __name__ == "__main__":
    main()
