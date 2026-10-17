"""
Métricas de calidad visual, filtro de imágenes y lista negra de cámaras.

TFM - Máster en Inteligencia Artificial
Autor: Lorenzo Jose de la Paz Suarez
"""

from pathlib import Path

import cv2
import pandas as pd

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def list_camera_images(raw_dir):
    """Imágenes de raw/<id_camara>/. Ignora carpetas que no son cámaras (p. ej. .ipynb_checkpoints)."""
    raw_dir = Path(raw_dir)
    return sorted(
        p
        for camera_dir in raw_dir.iterdir()
        if camera_dir.is_dir() and camera_dir.name.isdigit()
        for p in camera_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def image_metrics(image_path):
    """Resolución, brillo medio y nitidez (varianza del Laplaciano) de una imagen."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = img.shape[:2]
    return {
        "camera": Path(image_path).parent.name,
        "image": Path(image_path).name,
        "width": w,
        "height": h,
        "brightness": float(gray.mean()),
        "sharpness": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
    }


def add_quality(df, cfg):
    """Añade los criterios de calidad y un score normalizado.

    - Brillo: el mínimo solo se exige de día (columna `illumination`); de noche/crepúsculo
      una imagen oscura es normal y no indica una cámara defectuosa.
    - Nitidez: el umbral es un percentil de la distribución observada, no un valor fijo.
    - quality_score: media ponderada de los percentiles (0-1) de brillo y nitidez, de modo
      que ambas métricas tienen la misma escala.

    Devuelve (df, umbrales).
    """
    df = df.copy()
    sharpness_min = float(df["sharpness"].quantile(cfg["percentil_nitidez_min"] / 100))
    is_day = df["illumination"].eq("dia") if "illumination" in df.columns else pd.Series(True, index=df.index)

    df["resolution_ok"] = (df["width"] >= cfg["min_ancho"]) & (df["height"] >= cfg["min_alto"])
    df["brightness_ok"] = (df["brightness"] <= cfg["brillo_max"]) & (~is_day | (df["brightness"] >= cfg["brillo_min_dia"]))
    df["sharpness_ok"] = df["sharpness"] >= sharpness_min
    df["valid"] = df["resolution_ok"] & df["brightness_ok"] & df["sharpness_ok"]

    weights = cfg["pesos_score"]
    df["quality_score"] = (
        weights["brillo"] * df["brightness"].rank(pct=True)
        + weights["nitidez"] * df["sharpness"].rank(pct=True)
    )

    thresholds = {
        "sharpness_min": sharpness_min,
        "brightness_min_dia": cfg["brillo_min_dia"],
        "brightness_max": cfg["brillo_max"],
    }
    return df, thresholds


def camera_blacklist(df, max_fail_fraction):
    """Cámaras cuya fracción de imágenes de día no válidas supera el umbral.
    Una sola imagen defectuosa (o nocturna) ya no descarta la cámara entera.
    """
    day = df[df["illumination"].eq("dia")] if "illumination" in df.columns else df
    stats = day.groupby("camera")["valid"].agg(n_imagenes="size", fraccion_fallos=lambda v: 1 - v.mean())
    stats = stats.reset_index()
    stats["en_lista_negra"] = stats["fraccion_fallos"] > max_fail_fraction
    return stats
