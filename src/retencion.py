"""
Retención de imágenes en raw/: rejilla de entrenamiento y depuración de lo que no aporta.

Los lotes de anotación exigen al menos `cvat.separacion_minima_min` (10 min) entre dos
imágenes de la misma cámara, así que de cada cámara solo puede llegar a entrenamiento una
imagen por franja de 10 minutos. El resto es redundante salvo que haga falta para otra cosa.

Rejilla: el día se divide en franjas fijas de `franja_min` minutos (en UTC, alineadas con la
hora). De cada cámara y franja se conserva la imagen de mayor quality_score entre los
fotogramas válidos (fase frames de 02a) que se pudieron leer (fase detections de 02c). Si la
franja no tiene ninguno, se conserva su primera imagen, para no perder la estadística de
fallos de la cámara.

Decisión por imagen, en este orden (la primera que se cumple):
1. en_lote:          está en un lote de anotación (anotacion/*/indice.csv) -> conservar.
2. reciente:         tiene menos de `dias_gracia` días -> conservar.
3. pendiente_02:     es posterior a la última ejecución de 02 -> conservar.
4. pendiente_06:     pertenece a una secuencia a 6 s que 06 aún no ha procesado -> conservar.
5. ilegible:         02a la registró, pero 02c no la pudo leer -> borrar.
6. rejilla:          es la representante de su franja -> conservar.
7. ventana:          su día local está en una ventana de evaluación -> conservar.
8. redundante:       el resto -> borrar.

Test: localizados en tests/test_retencion.py.

TFM - Máster en Inteligencia Artificial
Autor: Lorenzo Jose de la Paz Suarez
"""

import pandas as pd

KEEP = "conservar"
DELETE = "borrar"

REASONS = {
    "en_lote": KEEP,
    "reciente": KEEP,
    "pendiente_02": KEEP,
    "pendiente_06": KEEP,
    "ilegible": DELETE,
    "rejilla": KEEP,
    "ventana": KEEP,
    "redundante": DELETE,
}


def grid_slot(timestamps, minutes):
    """Inicio de la franja de `minutes` minutos de cada marca de tiempo (UTC)."""
    return pd.to_datetime(timestamps).dt.floor(f"{minutes}min")


def grid_representatives(images, frames, minutes):
    """Claves (camera, image) de la imagen que representa a cada cámara y franja.

    `images`: DataFrame (camera, image, timestamp) con todas las imágenes de raw/.
    `frames`: DataFrame (camera, image, quality_score) con los fotogramas válidos y legibles.
    Gana la de mayor quality_score; una franja sin fotogramas válidos conserva su primera imagen.
    """
    df = images[["camera", "image", "timestamp"]].copy()
    df["slot"] = grid_slot(df["timestamp"], minutes)
    df = df.merge(frames[["camera", "image", "quality_score"]], on=["camera", "image"], how="left")
    df["_valid"] = df["quality_score"].notna()
    # Primero las válidas por calidad descendente; si no hay ninguna, la más antigua de la franja
    df = df.sort_values(["camera", "slot", "_valid", "quality_score", "timestamp"],
                        ascending=[True, True, False, False, True])
    best = df.drop_duplicates(["camera", "slot"])
    return set(zip(best["camera"], best["image"]))


def in_windows(local_dates, windows):
    """True si la fecha local está en alguna ventana [inicio, fin] (fechas ISO, ambas incluidas)."""
    dates = pd.to_datetime(pd.Series(local_dates)).dt.normalize()
    inside = pd.Series(False, index=dates.index)
    for start, end in windows or []:
        inside |= dates.between(pd.Timestamp(start), pd.Timestamp(end))
    return inside.to_numpy()


def classify_images(images, frames, detected, lote_keys, pending_06, now, processed_until, cfg,
                    tz="Europe/Madrid"):
    """Decide qué hacer con cada imagen de raw/.

    `images`: DataFrame (camera, image, timestamp UTC naive, ...) de las imágenes en disco.
    `frames`: fase frames (camera, image, quality_score) de 02a.
    `detected`: claves (camera, image) que 02c pudo procesar.
    `lote_keys`: claves (camera, image) de las imágenes incluidas en algún lote de anotación.
    `pending_06`: claves de las imágenes de secuencias a 6 s que 06 aún no ha procesado.
    `now`: instante actual (UTC naive). `processed_until`: último timestamp procesado por 02.
    `cfg`: sección `retencion` de config.yaml (franja_min, dias_gracia, ventanas_evaluacion).
    Devuelve `images` con las columnas `motivo` y `accion`.
    """
    df = images.copy()
    keys = list(zip(df["camera"], df["image"]))
    frame_keys = set(zip(frames["camera"], frames["image"]))
    valid = frames[[k in detected for k in zip(frames["camera"], frames["image"])]]
    reps = grid_representatives(df, valid, cfg["franja_min"])

    local_dates = (pd.to_datetime(df["timestamp"]).dt.tz_localize("UTC").dt.tz_convert(tz)
                   .dt.tz_localize(None).dt.normalize())
    in_window = in_windows(local_dates, cfg.get("ventanas_evaluacion"))
    recent = (pd.Timestamp(now) - pd.to_datetime(df["timestamp"])) < pd.Timedelta(days=cfg["dias_gracia"])
    pending_02 = pd.to_datetime(df["timestamp"]) > pd.Timestamp(processed_until)

    reasons = []
    for key, is_recent, is_pending, is_window in zip(keys, recent, pending_02, in_window):
        if key in lote_keys:
            reasons.append("en_lote")
        elif is_recent:
            reasons.append("reciente")
        elif is_pending:
            reasons.append("pendiente_02")
        elif key in pending_06:
            reasons.append("pendiente_06")
        elif key in frame_keys and key not in detected:
            reasons.append("ilegible")
        elif key in reps:
            reasons.append("rejilla")
        elif is_window:
            reasons.append("ventana")
        else:
            reasons.append("redundante")
    df["motivo"] = reasons
    df["accion"] = df["motivo"].map(REASONS)
    return df
