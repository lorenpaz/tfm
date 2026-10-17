"""
Priorización de imágenes a anotar para compensar desequilibrios de clases.

Las pre-anotaciones están muy desequilibradas: muchísimos coches y, por el sesgo de la
clasificación HSV, casi todos los semáforos salen en ámbar. Anotar al azar reproduciría ese
desequilibrio. Aquí se eligen las imágenes que más aportan a los GRUPOS escasos, con una
selección voraz: cada imagen elegida reduce el peso de los grupos que ya cubre.

Grupos (a partir de los conteos por fotograma de 02c_preproceso_deteccion_yolo26):
- Objetos: pedestrian, car, bus, truck, motorcycle.
- semaforo: cualquier semáforo vehicular, sea del color que sea. El color pre-anotado no es
  fiable, así que lo valioso es que la imagen tenga semáforos que el anotador clasifique.
- semaforo_rojo / semaforo_verde: indicios HSV de rojo o verde (pocos, pero valiosos).
- semaforo_peatonal: semáforos peatonales detectados por la heurística.
- poca_luz: imágenes de noche o crepúsculo (condición escasa en los datos).
El ámbar no es un grupo: está sobrerrepresentado y casi siempre mal clasificado.

TFM - Máster en Inteligencia Artificial
Autor: Lorenzo Jose de la Paz Suarez
"""

import numpy as np
import pandas as pd

GROUPS = {
    "pedestrian": ["n_pedestrian"],
    "car": ["n_car"],
    "bus": ["n_bus"],
    "truck": ["n_truck"],
    "motorcycle": ["n_motorcycle"],
    "semaforo": ["n_traffic_light_red", "n_traffic_light_yellow", "n_traffic_light_green", "n_traffic_light_unknown"],
    "semaforo_rojo": ["n_traffic_light_red"],
    "semaforo_verde": ["n_traffic_light_green"],
    "semaforo_peatonal": ["n_pedestrian_light_red", "n_pedestrian_light_green"],
}

# Clases de CVAT/CLASS_NAMES que cuentan para cada grupo (para incluir lo ya anotado)
CLASS_TO_GROUPS = {
    "pedestrian": ["pedestrian"],
    "car": ["car"],
    "bus": ["bus"],
    "truck": ["truck"],
    "motorcycle": ["motorcycle"],
    "traffic_light_red": ["semaforo", "semaforo_rojo"],
    "traffic_light_yellow": ["semaforo"],
    "traffic_light_green": ["semaforo", "semaforo_verde"],
    "traffic_light_unknown": ["semaforo"],
    "pedestrian_light_red": ["semaforo_peatonal"],
    "pedestrian_light_green": ["semaforo_peatonal"],
}


def group_counts(frames):
    """Instancias por grupo y fotograma. `frames` une las fases frames y detections."""
    counts = pd.DataFrame({group: frames[cols].sum(axis=1) for group, cols in GROUPS.items()}, index=frames.index)
    counts["poca_luz"] = frames["illumination"].isin(["noche", "crepusculo"]).astype(int)
    return counts


def class_balance(counts):
    """Resumen del desequilibrio: instancias, imágenes con el grupo y proporción frente al mayoritario."""
    summary = pd.DataFrame({
        "instancias": counts.sum(),
        "imagenes_con_grupo": (counts > 0).sum(),
    })
    summary["pct_imagenes"] = (100 * summary["imagenes_con_grupo"] / len(counts)).round(2)
    summary["ratio_vs_mayoritario"] = (summary["instancias"].max() / summary["instancias"].replace(0, np.nan)).round(1)
    return summary.sort_values("instancias", ascending=False)


def annotated_group_totals(class_counts):
    """Convierte cajas por clase (p. ej. de un lote de CVAT) en totales por grupo."""
    totals = dict.fromkeys(list(GROUPS) + ["poca_luz"], 0)
    for cls, n in class_counts.items():
        for group in CLASS_TO_GROUPS.get(cls, []):
            totals[group] += int(n)
    return pd.Series(totals)


def greedy_balanced_selection(frames, counts, n, max_per_camera, initial_totals=None, cap=3, min_gap_s=0):
    """Selección voraz que nivela los grupos.

    En cada paso elige la imagen con mayor ganancia = sum_g peso_g * min(n_g, cap), con
    peso_g = 1 / (1 + total_g) y total_g = instancias del grupo ya acumuladas (lo anotado
    previamente + lo seleccionado). Así los grupos escasos pesan mucho al principio y su peso
    baja a medida que se cubren; los abundantes (coches) apenas puntúan. `cap` evita que una
    imagen con 20 coches gane solo por cantidad. Limita a `max_per_camera` imágenes por cámara
    y exige `min_gap_s` segundos entre dos imágenes de la misma cámara (evita casi-duplicados).

    Devuelve las filas elegidas de `frames`, en orden de prioridad, con la columna `prioridad`
    (1 = la primera a anotar) y los totales esperados por grupo tras el lote.
    """
    raw = counts.to_numpy(dtype=float)
    values = np.minimum(raw, cap)
    # np.array(...) hace una copia escribible (con pandas 3, to_numpy puede devolver una vista de solo lectura)
    totals = np.array(initial_totals.reindex(counts.columns).fillna(0) if initial_totals is not None
                      else pd.Series(0.0, index=counts.columns), dtype=float)
    cameras = frames["camera"].to_numpy()
    seconds = (pd.to_datetime(frames["timestamp"]) - pd.Timestamp("2000-01-01")).dt.total_seconds().to_numpy()

    available = np.ones(len(frames), dtype=bool)
    per_camera = {}
    chosen = []
    for _ in range(min(n, len(frames))):
        gain = values @ (1.0 / (1.0 + totals))
        gain[~available] = -1
        best = int(np.argmax(gain))
        if gain[best] <= 0:
            break
        chosen.append(best)
        available[best] = False
        totals += raw[best]
        per_camera[cameras[best]] = per_camera.get(cameras[best], 0) + 1
        if per_camera[cameras[best]] >= max_per_camera:
            available &= cameras != cameras[best]
        elif min_gap_s:
            # Descarta las imágenes de la misma cámara demasiado próximas en el tiempo
            available &= ~((cameras == cameras[best]) & (np.abs(seconds - seconds[best]) < min_gap_s))

    selection = frames.iloc[chosen].copy()
    selection["prioridad"] = np.arange(1, len(chosen) + 1)
    return selection, pd.Series(totals, index=counts.columns)
