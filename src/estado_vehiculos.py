"""
Estado de los vehículos junto al semáforo: esperando, aparcado o circulando.

En una sola imagen no se distingue un coche aparcado de uno que espera en rojo. Se combinan
dos criterios (decisión documentada en notebooks/README.md, sección 06):

1. Zonas por cámara, dibujadas una vez en CVAT:
   - zona_espera: carril de espera antes de la línea de detención.
   - zona_aparcamiento: plazas de aparcamiento visibles.
   - paso_peatones: paso de cebra. Un vehículo sobre el paso no está "esperando" en el carril;
     la zona se usará también para los peatones al inferir la fase peatonal.
   Se usa el punto inferior central de la caja (donde la rueda toca el suelo), que es más
   estable que el centro de la caja frente a la perspectiva.
2. Persistencia temporal (capturas cada 6 s): las cajas se enlazan entre fotogramas
   consecutivos por solape (IoU). Un vehículo que sigue inmóvil más de `tiempo_aparcado_s`
   (~3 ciclos semafóricos, verdes incluidos) está aparcado; uno que espera arranca en verde.

Regla de clasificación de cada caja:
- aparcado:   en zona_aparcamiento, o inmóvil durante más de tiempo_aparcado_s.
- esperando:  en zona_espera, detenido (sin moverse respecto al fotograma anterior) y no aparcado.
- circulando: el resto.

Test: localizados en tests/test_estado_vehiculos.py-

TFM - Máster en Inteligencia Artificial
Autor: Lorenzo Jose de la Paz Suarez
"""

import json

from pathlib import Path

ESTADOS = ["desconocido", "esperando", "aparcado", "circulando"]


def load_zones(json_path):
    """{camara: {"zona_espera": [polígonos], "zona_aparcamiento": [polígonos]}} con puntos normalizados (0-1)."""
    json_path = Path(json_path)
    if not json_path.exists():
        return {}
    return json.loads(json_path.read_text(encoding="utf-8"))["camaras"]


def point_in_polygon(x, y, polygon):
    """Ray casting: True si (x, y) está dentro del polígono [(x1, y1), (x2, y2), ...]."""
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_cross = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_cross:
                inside = not inside
    return inside


def box_zone(box, img_w, img_h, camera_zones):
    """Zona de una caja [x1, y1, x2, y2] (px) según su punto inferior central, o None."""
    if not camera_zones:
        return None
    x = (box[0] + box[2]) / 2 / img_w
    y = box[3] / img_h
    # Prioridad: aparcamiento > espera > paso de peatones (si los polígonos se solapan,
    # una plaza junto al carril es aparcamiento y el carril hasta la línea de detención, espera)
    for zone in ("zona_aparcamiento", "zona_espera", "paso_peatones"):
        if any(point_in_polygon(x, y, polygon) for polygon in camera_zones.get(zone, [])):
            return zone
    return None


def iou(a, b):
    """Intersección sobre unión de dos cajas [x1, y1, x2, y2]."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def track_vehicles(frames, iou_link=0.3, iou_still=0.7, max_gap_s=15):
    """Enlaza las cajas de vehículos entre fotogramas consecutivos de UNA cámara.

    `frames`: lista ordenada por tiempo de (timestamp, [caja, ...]), con timestamp datetime y
    cajas [x1, y1, x2, y2]. Devuelve, para cada fotograma, una lista paralela a sus cajas con
    dicts {track, inmovil_desde, detenido}:
    - track: identificador del vehículo seguido.
    - detenido: la caja apenas se ha movido respecto al fotograma anterior (IoU >= iou_still).
    - inmovil_desde: instante desde el que el vehículo no se ha movido (para medir cuánto lleva parado).
    Un hueco mayor que max_gap_s entre imágenes corta todos los seguimientos.
    El emparejamiento es voraz por IoU decreciente (suficiente con pocas cajas por imagen).
    """
    results = []
    previous = []          # [(caja, info)] del fotograma anterior
    previous_ts = None
    next_track = 0

    for ts, boxes in frames:
        if previous_ts is not None and (ts - previous_ts).total_seconds() > max_gap_s:
            previous = []

        pairs = sorted(
            ((iou(box, prev_box), i, j) for i, box in enumerate(boxes) for j, (prev_box, _) in enumerate(previous)),
            reverse=True,
        )
        matched_new, matched_prev = {}, set()
        for overlap, i, j in pairs:
            if overlap < iou_link or i in matched_new or j in matched_prev:
                continue
            matched_new[i] = (j, overlap)
            matched_prev.add(j)

        current = []
        for i, box in enumerate(boxes):
            if i in matched_new:
                j, overlap = matched_new[i]
                prev_info = previous[j][1]
                still = overlap >= iou_still
                info = {
                    "track": prev_info["track"],
                    "detenido": still,
                    "inmovil_desde": prev_info["inmovil_desde"] if still else ts,
                }
            else:
                info = {"track": next_track, "detenido": False, "inmovil_desde": ts}
                next_track += 1
            current.append((box, info))

        results.append([info for _, info in current])
        previous, previous_ts = current, ts

    return results


def classify_state(zone, detenido, seconds_still, parked_after_s=300):
    """Estado de un vehículo a partir de su zona y de cuánto tiempo lleva inmóvil."""
    if zone == "zona_aparcamiento" or seconds_still >= parked_after_s:
        return "aparcado"
    if zone == "zona_espera" and detenido:
        return "esperando"
    return "circulando"
