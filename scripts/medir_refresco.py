"""
Mide la frecuencia real de refresco de las cámaras de tráfico de Málaga.

Consulta varias cámaras cada POLL segundos durante DURACION minutos y, en cada consulta,
registra la cabecera Last-Modified del servidor y un hash de la imagen. Un cambio en
cualquiera de los dos indica que la cámara ha publicado una imagen nueva.

Uso:
    python scripts/medir_refresco.py --camaras 21547 21541 21560 --duracion 10 --poll 1
    python scripts/medir_refresco.py --duracion 15 --guardar-imagenes

Salida (data/malaga/refresco/):
    refresco_<UTC>.csv          una fila por consulta
    refresco_<UTC>_resumen.csv  intervalos entre imágenes nuevas por cámara
    refresco_<UTC>/<camara>/    imágenes nuevas (solo con --guardar-imagenes)
"""

import argparse
import hashlib
import sys
import time

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from catalogo import load_catalog
from config import load_config, path
from tiempo import FILENAME_FORMAT

OUT_DIR = path("refresco")
REQUEST_TIMEOUT = load_config()["captura"]["timeout_s"]

# Cámaras de referencia (buena visibilidad de semáforos, ver analisis_camaras_trafico_malaga.md)
DEFAULT_CAMERAS = load_config()["refresco"]["camaras_referencia"]

# Mismas cabeceras que captura_camaras.py (el servidor rechaza clientes sin User-Agent de navegador)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://malaga.eu",
}


def load_urls(camera_ids):
    df = load_catalog()
    df = df[df["ID"].isin({str(c) for c in camera_ids})]
    return dict(zip(df["ID"], df["URLIMAGEN"]))


def poll_camera(session, camera_id, url, save_dir, last_hash):
    requested_at = datetime.now(timezone.utc)
    row = {
        "camera_id": camera_id,
        "requested_at": requested_at,
        "status": None,
        "last_modified": pd.NaT,
        "sha1": None,
        "size": None,
        "elapsed_ms": None,
    }

    try:
        response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        row["status"] = response.status_code
        row["elapsed_ms"] = response.elapsed.total_seconds() * 1000

        if response.ok:
            content = response.content
            row["sha1"] = hashlib.sha1(content).hexdigest()
            row["size"] = len(content)

            header = response.headers.get("Last-Modified")
            if header:
                row["last_modified"] = parsedate_to_datetime(header).astimezone(timezone.utc)

            if save_dir is not None and row["sha1"] != last_hash:
                camera_dir = save_dir / camera_id
                camera_dir.mkdir(parents=True, exist_ok=True)
                (camera_dir / f"{requested_at.strftime(FILENAME_FORMAT)}.jpg").write_bytes(content)

    except requests.RequestException as exc:
        row["status"] = f"ERROR: {exc}"

    return row


def measure(camera_ids, duration_min, poll_s, save_images=False):
    urls = load_urls(camera_ids)
    missing = set(map(str, camera_ids)) - set(urls)
    if missing:
        print(f"Aviso: cámaras no encontradas en el catálogo: {sorted(missing)}")

    stamp = datetime.now(timezone.utc).strftime(FILENAME_FORMAT)
    save_dir = OUT_DIR / f"refresco_{stamp}" if save_images else None

    session = requests.Session()
    rows = []
    last_hash = {}
    end = time.monotonic() + duration_min * 60

    print(f"Midiendo {len(urls)} cámaras cada {poll_s}s durante {duration_min} min...")

    with ThreadPoolExecutor(max_workers=len(urls)) as pool:
        while time.monotonic() < end:
            round_start = time.monotonic()

            futures = [
                pool.submit(poll_camera, session, cam, url, save_dir, last_hash.get(cam))
                for cam, url in urls.items()
            ]
            for future in futures:
                row = future.result()
                rows.append(row)
                if row["sha1"]:
                    last_hash[row["camera_id"]] = row["sha1"]

            time.sleep(max(0.0, poll_s - (time.monotonic() - round_start)))

    polls = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    polls_file = OUT_DIR / f"refresco_{stamp}.csv"
    polls.to_csv(polls_file, index=False)

    summary = summarize(polls, poll_s)
    summary.to_csv(OUT_DIR / f"refresco_{stamp}_resumen.csv", index=False)

    print(f"Consultas guardadas en {polls_file}")
    return polls, summary


def change_intervals(polls):
    """Intervalos (s) entre imágenes nuevas por cámara, usando Last-Modified y, en su defecto, el hash."""
    records = []

    for camera_id, g in polls[polls["sha1"].notna()].groupby("camera_id"):
        g = g.sort_values("requested_at")

        # 1) Last-Modified: instante exacto de publicación según el servidor
        lm = pd.to_datetime(g["last_modified"], utc=True).dropna().drop_duplicates()
        for delta in lm.diff().dropna().dt.total_seconds():
            records.append({"camera_id": camera_id, "method": "last_modified", "interval_s": delta})

        # 2) Hash: primera consulta en la que el contenido cambia (precisión = POLL)
        changed = g["sha1"].ne(g["sha1"].shift())
        change_times = pd.to_datetime(g.loc[changed, "requested_at"], utc=True).iloc[1:]
        for delta in change_times.diff().dropna().dt.total_seconds():
            records.append({"camera_id": camera_id, "method": "hash", "interval_s": delta})

    return pd.DataFrame(records, columns=["camera_id", "method", "interval_s"])


def summarize(polls, poll_s):
    intervals = change_intervals(polls)
    if intervals.empty:
        return pd.DataFrame()

    summary = (
        intervals.groupby(["camera_id", "method"])["interval_s"]
        .describe(percentiles=[0.1, 0.5, 0.9])
        .reset_index()
        .rename(columns={"count": "n_intervalos", "50%": "mediana_s", "10%": "p10_s", "90%": "p90_s"})
    )
    summary["poll_s"] = poll_s

    # Latencia de publicación: cuánto tarda en servirse una imagen tras su Last-Modified
    lm = pd.to_datetime(polls["last_modified"], utc=True)
    req = pd.to_datetime(polls["requested_at"], utc=True)
    polls = polls.assign(antiguedad_s=(req - lm).dt.total_seconds())
    age = polls.groupby("camera_id")["antiguedad_s"].median().rename("antiguedad_mediana_s")

    return summary.merge(age, on="camera_id", how="left")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--camaras", type=int, nargs="+", default=DEFAULT_CAMERAS)
    parser.add_argument("--duracion", type=float, default=10, help="minutos de medición")
    parser.add_argument("--poll", type=float, default=1.0, help="segundos entre consultas")
    parser.add_argument("--guardar-imagenes", action="store_true", help="guarda cada imagen nueva detectada")
    args = parser.parse_args()

    _, summary = measure(args.camaras, args.duracion, args.poll, args.guardar_imagenes)

    if summary.empty:
        print("No se detectaron cambios de imagen: amplía la duración.")
    else:
        print(summary[["camera_id", "method", "n_intervalos", "mediana_s", "p10_s", "p90_s", "antiguedad_mediana_s"]]
              .to_string(index=False))


if __name__ == "__main__":
    main()
