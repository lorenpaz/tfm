"""
Función de auto-anotación de CVAT basada en YOLO26 (pesos COCO).

Genera PRE-anotaciones (cajas) que después se revisan y corrigen a mano en CVAT:
- person / car / bus / truck / motorcycle: directamente de las clases COCO.
- semáforos: la clase COCO "traffic light" se etiqueta por caja según su color HSV
  (traffic_light_red/yellow/green) o traffic_light_unknown si no se distingue.
  Los semáforos peatonales no se distinguen automáticamente: el anotador cambia la
  etiqueta a pedestrian_light_* durante la revisión.

Uso desde Python:
    import cvat_sdk.auto_annotation as cvataa
    from cvat_yolo26 import Yolo26PreAnnotator

    cvataa.annotate_task(client, task_id, Yolo26PreAnnotator(), clear_existing=True)

Uso desde la CLI de CVAT:
    cvat-cli task auto-annotate <task_id> --function-module cvat_yolo26 -p weights=str:yolo26s.pt
"""

import numpy as np

import cvat_sdk.auto_annotation as cvataa

from deteccion import CLASS_NAMES, CLASS_TO_IDX, predict_boxes


class Yolo26PreAnnotator:
    def __init__(self, weights="yolo26s.pt", imgsz=640, conf=0.25, device=None):
        from ultralytics import YOLO

        self._model = YOLO(weights)
        self._imgsz = imgsz
        self._conf = conf
        self._device = device

        self.spec = cvataa.DetectionFunctionSpec(
            labels=[cvataa.label_spec(name, idx) for idx, name in enumerate(CLASS_NAMES)]
        )

    def detect(self, context, image):
        conf = context.conf_threshold if context.conf_threshold is not None else self._conf
        img_bgr = np.ascontiguousarray(np.asarray(image.convert("RGB"))[..., ::-1])

        boxes = predict_boxes(self._model, img_bgr, conf=conf, imgsz=self._imgsz, device=self._device)
        return [cvataa.rectangle(CLASS_TO_IDX[name], xyxy) for name, xyxy in boxes]


# Punto de entrada para `cvat-cli task auto-annotate --function-module cvat_yolo26`
def create(weights: str = "yolo26s.pt", imgsz: int = 640, conf: float = 0.25):
    return Yolo26PreAnnotator(weights=weights, imgsz=imgsz, conf=conf)
