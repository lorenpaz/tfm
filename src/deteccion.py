"""
Definiciones compartidas de detección: clases del dataset, mapeo COCO y color de semáforos.

Es la fuente única de las clases para la anotación en CVAT (03a_anotacion_lote_estratificado) y el
entrenamiento (04_entrenamiento_yolo26): el orden de CLASS_NAMES define el índice de clase YOLO.

TFM - Máster en Inteligencia Artificial
Autor: Lorenzo Jose de la Paz Suarez
"""


import cv2

# Clases del detector (orden = índice de clase YOLO)
CLASS_NAMES = [
    "pedestrian",
    "car",
    "bus",
    "truck",
    "motorcycle",
    "traffic_light_red",
    "traffic_light_yellow",
    "traffic_light_green",
    "traffic_light_unknown",   # semáforo visible pero sin color distinguible (de lado, de espaldas, apagado)
    "pedestrian_light_red",
    "pedestrian_light_green",
]
CLASS_TO_IDX = {name: i for i, name in enumerate(CLASS_NAMES)}

TRAFFIC_LIGHT_CLASSES = ["traffic_light_red", "traffic_light_yellow", "traffic_light_green"]
PEDESTRIAN_LIGHT_CLASSES = ["pedestrian_light_red", "pedestrian_light_green"]

# Clases COCO (pesos preentrenados de YOLO26) que se reutilizan
COCO_TO_CLASS = {
    0: "pedestrian",       # clase COCO "person"
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
COCO_TRAFFIC_LIGHT = 9

TRAFFIC_LIGHT_MIN_AREA = 20  # píxeles^2 mínimos del recorte para clasificar color


def classify_traffic_light_color(img_bgr, bbox, min_area=TRAFFIC_LIGHT_MIN_AREA):
    """Clasifica el color encendido de un semáforo (red/yellow/green) por el color dominante en HSV.

    Devuelve None si el recorte es demasiado pequeño o no hay suficientes píxeles coloreados.
    """
    x1, y1, x2, y2 = [int(round(v)) for v in bbox]
    h, w = img_bgr.shape[:2]
    x1, x2 = max(0, x1), min(w, x2)
    y1, y2 = max(0, y1), min(h, y2)
    crop = img_bgr[y1:y2, x1:x2]
    if crop.size == 0 or crop.shape[0] * crop.shape[1] < min_area:
        return None

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    # El rojo ocupa los dos extremos del canal H
    red_mask = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255)) | cv2.inRange(hsv, (160, 100, 100), (179, 255, 255))
    yellow_mask = cv2.inRange(hsv, (18, 100, 100), (35, 255, 255))
    green_mask = cv2.inRange(hsv, (45, 80, 80), (90, 255, 255))

    counts = {
        "red": int(cv2.countNonZero(red_mask)),
        "yellow": int(cv2.countNonZero(yellow_mask)),
        "green": int(cv2.countNonZero(green_mask)),
    }
    best_color, best_count = max(counts.items(), key=lambda kv: kv[1])

    # Mínimo de píxeles coloreados para evitar falsos positivos
    if best_count < max(3, 0.02 * crop.shape[0] * crop.shape[1]):
        return None
    return best_color


def predict_boxes(model, img_bgr, conf=0.25, imgsz=640, device=None):
    """Inferencia YOLO26 (pesos COCO) -> lista de (clase, [x1, y1, x2, y2]) con clases de CLASS_NAMES.

    Los semáforos se etiquetan por caja con su color (traffic_light_red/yellow/green)
    o traffic_light_unknown si no se distingue.
    """
    result = model.predict(img_bgr, imgsz=imgsz, conf=conf, device=device, verbose=False)[0]

    boxes = []
    for xyxy, cls_id in zip(result.boxes.xyxy.tolist(), result.boxes.cls.tolist()):
        cls_id = int(cls_id)
        if cls_id == COCO_TRAFFIC_LIGHT:
            color = classify_traffic_light_color(img_bgr, xyxy)
            name = f"traffic_light_{color}" if color else "traffic_light_unknown"
        elif cls_id in COCO_TO_CLASS:
            name = COCO_TO_CLASS[cls_id]
        else:
            continue
        boxes.append((name, [float(v) for v in xyxy]))
    return boxes


def is_pedestrian_light(bbox, img_shape):
    """Heurística: semáforo peatonal = caja pequeña en la mitad inferior de la imagen.

    Solo se usa para los indicadores de 02c_preproceso_deteccion_yolo26; en CVAT el anotador decide el tipo.
    """
    x1, y1, x2, y2 = bbox
    h, w = img_shape[:2]
    return (y1 + y2) / 2 > h * 0.5 and (y2 - y1) < h * 0.15 and (x2 - x1) < w * 0.08


VEHICLE_CLASSES = ["car", "bus", "truck", "motorcycle"]


def frame_counts(boxes, img_shape):
    """Conteos por fotograma a partir de predict_boxes().

    Devuelve n_<clase> para objetos y semáforos (los de color con la heurística peatonal
    aplicada) y n_vehiculos.
    """
    counts = {f"n_{name}": 0 for name in CLASS_NAMES}
    for name, bbox in boxes:
        if name in TRAFFIC_LIGHT_CLASSES and is_pedestrian_light(bbox, img_shape):
            # Los peatonales solo tienen rojo/verde; un ámbar se mantiene como vehicular
            pedestrian = f"pedestrian_light_{name.rsplit('_', 1)[1]}"
            name = pedestrian if pedestrian in CLASS_TO_IDX else name
        counts[f"n_{name}"] += 1

    counts["n_vehiculos"] = sum(counts[f"n_{c}"] for c in VEHICLE_CLASSES)
    return counts
