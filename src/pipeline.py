"""
Salidas por fase del preprocesamiento y utilidades comunes del pipeline.

Cada notebook 02_* escribe SOLO su propia salida en data/malaga/fases/:
    frames.parquet      02a_preproceso_calidad_contexto     (fotogramas válidos + contexto temporal)
    weather.parquet     02b_preproceso_meteorologia_aemet   (etiqueta meteorológica + observación AEMET)
    detections.parquet  02c_preproceso_deteccion_yolo26     (conteos y estados de semáforo por fotograma)

Las fases se unen por (camera, image) con load_frames(), de modo que el orden de ejecución
de weather y detection es indiferente y ninguna fase puede pisar el trabajo de otra.

TFM - Máster en Inteligencia Artificial
Autor: Lorenzo Jose de la Paz Suarez
"""

from pathlib import Path

import pandas as pd

from config import PROJECT_ROOT, load_config, path

KEYS = ["camera", "image"]
PHASES = ("frames", "weather", "detections")


def phase_path(name):
    return path("fases") / f"{name}.parquet"


def save_phase(df, name):
    missing = set(KEYS) - set(df.columns)
    if missing:
        raise ValueError(f"La fase {name} debe incluir las columnas clave {missing}")
    if df.duplicated(KEYS).any():
        raise ValueError(f"La fase {name} tiene filas duplicadas para {KEYS}")

    out = phase_path(name)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return out


def load_phase(name):
    file = phase_path(name)
    if not file.exists():
        raise FileNotFoundError(f"No existe la fase '{name}' ({file}). Ejecuta antes el notebook correspondiente.")
    df = pd.read_parquet(file)
    df["camera"] = df["camera"].astype(str)
    return df


def load_frames(*extra_phases):
    """Fotogramas de la fase frames unidos (left join) con las fases indicadas que existan."""
    frames = load_phase("frames")
    for name in extra_phases:
        if not phase_path(name).exists():
            print(f"Aviso: la fase '{name}' aún no existe; se omite.")
            continue
        other = load_phase(name)
        overlap = (set(other.columns) & set(frames.columns)) - set(KEYS)
        frames = frames.merge(other.drop(columns=list(overlap)), on=KEYS, how="left")
    return frames


def service_cameras():
    """IDs (texto) de las 24 cámaras del servicio de captura continua (config.yaml -> captura.camaras)."""
    return {str(c) for c in load_config()["captura"]["camaras"]}


def only_service_cameras(df):
    """Filtra a las cámaras del servicio de captura.

    Las demás solo tienen 1-2 imágenes (instantáneas de 00a_captura_instantanea_catalogo): sus indicadores no son
    representativos y añadirían ruido a la evaluación y a los lotes de anotación.
    """
    return df[df["camera"].astype(str).isin(service_cameras())]


def image_path(relative_path):
    """Ruta absoluta de una imagen guardada como ruta relativa a la raíz del proyecto."""
    return PROJECT_ROOT / Path(relative_path)


def measured_refresh_s():
    """Mediana del intervalo entre imágenes nuevas (Last-Modified) de la última medición de 00b, o None."""
    summaries = sorted(path("refresco").glob("refresco_*_resumen.csv"))
    if not summaries:
        return None
    summary = pd.read_csv(summaries[-1])
    summary = summary[summary["method"] == "last_modified"]
    if summary.empty:
        return None
    return float(summary["mediana_s"].median())


def sampling_seconds():
    """Intervalo de muestreo de fotogramas: refresco medido (si existe y está activado) o el valor por defecto."""
    cfg = load_config()["muestreo"]
    refresh = measured_refresh_s() if cfg["usar_refresco_medido"] else None
    if refresh is not None:
        return max(1, round(refresh)), "refresco medido (00b)"
    return cfg["segundos_por_defecto"], "valor por defecto (config.yaml)"


def sample_every(df, seconds):
    """Conserva como máximo un fotograma por cámara y ventana de `seconds` segundos (columna timestamp)."""
    if df.empty:
        return df.copy()
    if seconds <= 0:
        raise ValueError("El intervalo de muestreo debe ser mayor que cero")

    df = df.sort_values(["camera", "timestamp", "image"], na_position="last")
    with_ts = df[df["timestamp"].notna()]
    seconds_since_start = (
        with_ts["timestamp"] - with_ts.groupby("camera")["timestamp"].transform("min")
    ).dt.total_seconds()
    bucket = (seconds_since_start // seconds).astype("int64")
    keep = ~pd.concat([with_ts["camera"], bucket], axis=1).duplicated()

    return pd.concat([with_ts[keep], df[df["timestamp"].isna()]]).reset_index(drop=True)


def far_enough(timestamp, chosen_timestamps, min_gap_s):
    """True si `timestamp` dista al menos `min_gap_s` de todos los ya elegidos de su cámara."""
    return all(abs((timestamp - t).total_seconds()) >= min_gap_s for t in chosen_timestamps)


def stratified_selection(df, strata, n, max_per_camera, seed, min_gap_s=0):
    """Selección en round-robin entre estratos con un máximo por cámara.

    Toma primero una imagen de cada estrato, luego la segunda de cada estrato, etc., de forma
    que la muestra cubre el máximo de combinaciones (cámara, franja, tipo de día...) posible.
    Dos imágenes de la misma cámara deben distar al menos `min_gap_s` segundos: con capturas
    cada 6 s, las consecutivas son casi idénticas y no aportan información nueva.
    """
    shuffled = df.sample(frac=1, random_state=seed)
    shuffled = shuffled.assign(_ronda=shuffled.groupby(strata).cumcount())
    shuffled = shuffled.sort_values("_ronda", kind="stable")

    chosen, by_camera = [], {}
    for idx, camera, ts in zip(shuffled.index, shuffled["camera"], shuffled["timestamp"]):
        taken = by_camera.setdefault(camera, [])
        if len(taken) >= max_per_camera or (min_gap_s and not far_enough(ts, taken, min_gap_s)):
            continue
        taken.append(ts)
        chosen.append(idx)
        if len(chosen) == n:
            break
    return shuffled.loc[chosen].drop(columns=["_ronda"])
