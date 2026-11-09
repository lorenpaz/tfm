"""
Depuración de data/malaga/raw/: conserva la rejilla de entrenamiento y lo que aún hace falta,
y propone borrar el resto. Las reglas están en src/retencion.py y los parámetros en
config.yaml -> retencion.

Por defecto es una SIMULACIÓN: no borra nada, muestra cuánto espacio liberaría y escribe el
plan (las imágenes que borraría y por qué) en data/malaga/logs/depuracion_<UTC>_simulacion.csv.
Solo con --aplicar borra esas imágenes, y deja el registro en depuracion_<UTC>_aplicado.csv.

Uso (desde la raíz del proyecto, con el Python del .venv):
    python scripts/depurar_raw.py              # simulación
    python scripts/depurar_raw.py --aplicar    # borra lo que la simulación propone

TFM - Máster en Inteligencia Artificial
Autor: Lorenzo Jose de la Paz Suarez
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from calidad import IMAGE_EXTENSIONS
from config import PROJECT_ROOT, load_config, path
from estado_vehiculos import continuous_sequences
from retencion import DELETE, classify_images
from tiempo import parse_timestamp_from_name

GB = 1024 ** 3


def list_raw_images(raw_dir):
    """Imágenes de raw/<cámara>/ con su marca de tiempo y tamaño (os.scandir: rápido en Windows)."""
    rows = []
    with os.scandir(raw_dir) as cameras:
        for cam in cameras:
            if not (cam.is_dir() and cam.name.isdigit()):
                continue
            with os.scandir(cam.path) as files:
                for f in files:
                    if not f.is_file() or Path(f.name).suffix.lower() not in IMAGE_EXTENSIONS:
                        continue
                    ts = parse_timestamp_from_name(f.name)
                    if ts is not None:
                        rows.append((cam.name, f.name, ts, f.stat().st_size, f.path))
    return pd.DataFrame(rows, columns=["camera", "image", "timestamp", "bytes", "abs_path"])


def keys(df):
    return set(zip(df["camera"].astype(str), df["image"]))


def lote_keys(anotacion_dir):
    """(camera, image) original de cada imagen incluida en un lote (columna source_path)."""
    found = set()
    for indice in Path(anotacion_dir).glob("*/indice.csv"):
        for p in pd.read_csv(indice, usecols=["source_path"])["source_path"].dropna():
            parts = Path(p).parts
            found.add((parts[-2], parts[-1]))
    return found


def pending_06(images, cfg):
    """Imágenes de secuencias a 6 s de las cámaras de referencia que 06 aún no ha procesado."""
    ev = cfg["estado_vehiculos"]
    ref = images[images["camera"].isin([str(c) for c in ev["camaras"]])]
    seq = continuous_sequences(ref, ev["max_hueco_s"])
    boxes_file = path("fases") / "vehiculos_cajas.parquet"
    done = keys(pd.read_parquet(boxes_file, columns=["camera", "image"])) if boxes_file.exists() else set()
    return keys(seq) - done


def gb(n_bytes):
    return f"{n_bytes / GB:.2f} GB"


def main():
    parser = argparse.ArgumentParser(description="Depuración de raw/ (simulación por defecto)")
    parser.add_argument("--aplicar", action="store_true", help="borra de verdad lo que propone la simulación")
    args = parser.parse_args()

    cfg = load_config()
    ret = cfg["retencion"]
    frames_file = path("fases") / "frames.parquet"
    detections_file = path("fases") / "detections.parquet"
    if not (frames_file.exists() and detections_file.exists()):
        sys.exit("Faltan las fases frames o detections: ejecuta antes 02a y 02c.")

    print("Leyendo raw/ ...")
    images = list_raw_images(path("raw"))
    frames = pd.read_parquet(frames_file, columns=["camera", "image", "timestamp", "quality_score"])
    frames["camera"] = frames["camera"].astype(str)
    detected = keys(pd.read_parquet(detections_file, columns=["camera", "image"]))
    processed_until = frames["timestamp"].max()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    result = classify_images(images, frames, detected, lote_keys(path("anotacion")), pending_06(images, cfg),
                             now=now, processed_until=processed_until, cfg=ret, tz=cfg["zona_horaria"])

    # Resumen
    print(f"\nImágenes en raw/: {len(result)} ({gb(result['bytes'].sum())}) de {result['camera'].nunique()} cámaras")
    print(f"Procesadas por 02 hasta: {processed_until} UTC | franja: {ret['franja_min']} min | "
          f"gracia: {ret['dias_gracia']} días | ventanas: {ret.get('ventanas_evaluacion') or 'ninguna'}\n")
    summary = (result.groupby(["accion", "motivo"])["bytes"].agg(imagenes="size", bytes="sum")
               .reset_index().sort_values(["accion", "bytes"], ascending=[True, False]))
    summary["espacio"] = summary["bytes"].map(gb)
    print(summary[["accion", "motivo", "imagenes", "espacio"]].to_string(index=False))

    plan = result[result["accion"] == DELETE]
    window = result[result["motivo"] == "ventana"]
    print(f"\nLiberaría: {len(plan)} imágenes, {gb(plan['bytes'].sum())}.")
    if len(window):
        print(f"Protegidas solo por las ventanas de evaluación: {len(window)} imágenes, {gb(window['bytes'].sum())} "
              "(se liberarían al cerrar esas ventanas).")

    # Plan o registro de lo borrado
    mode = "aplicado" if args.aplicar else "simulacion"
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    out = path("logs") / f"depuracion_{stamp}_{mode}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    plan_csv = plan.assign(path=[Path(p).relative_to(PROJECT_ROOT).as_posix() for p in plan["abs_path"]])
    plan_csv[["camera", "image", "timestamp", "motivo", "bytes", "path"]].to_csv(out, index=False)
    print(f"Plan de borrado: {out}")

    if not args.aplicar:
        print("\nSIMULACIÓN: no se ha borrado nada. Para borrar: python scripts/depurar_raw.py --aplicar")
        return
    deleted = 0
    for p in plan["abs_path"]:
        try:
            os.remove(p)
            deleted += 1
        except FileNotFoundError:
            pass
    print(f"\nBorradas {deleted} imágenes. Registro: {out}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
