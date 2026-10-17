"""
Gestión de lotes de anotación en CVAT: creación, pre-anotación, estado y exportación.

Un lote es una carpeta data/malaga/anotacion/<lote>/ con:
    images/          copias de las imágenes con nombre único <cámara>_<timestamp>.jpg
    indice.csv       una fila por imagen (contexto, estado pendiente/revisada, etiqueta)
    cvat_task.json   tarea y proyecto de CVAT del lote
    labels/          etiquetas YOLO revisadas (se crean al exportar)

Lo usan 03a_anotacion_lote_estratificado (lotes estratificados), 03b_anotacion_lote_prioritario (lotes que
compensan los desequilibrios de clases) y 03c_anotacion_zonas_estado_vehiculos (zonas por cámara y lote de
validación del estado de los vehículos).
"""

import json
import shutil
import zipfile

from pathlib import Path

import pandas as pd

from anotacion import find_label_files, read_export_names, remap_lines
from config import PROJECT_ROOT, load_config, path
from deteccion import CLASS_NAMES, CLASS_TO_IDX
from pipeline import image_path

EXPORT_FORMATS = ["Ultralytics YOLO Detection 1.0", "YOLO 1.1"]
CVAT_ENV_FILE = PROJECT_ROOT / "cvat" / ".env"


def read_cvat_env(env_file=CVAT_ENV_FILE):
    """Credenciales generadas por cvat/cvat.ps1 (cvat/.env, excluido de git)."""
    values = {}
    for line in Path(env_file).read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def connect(retries=5, wait_s=5):
    """Cliente del SDK de CVAT autenticado. Avisa si las versiones de servidor y SDK difieren.

    Reintenta la conexión: la red entre Windows y los contenedores de Docker Desktop sufre
    cortes puntuales ("Connection reset") que se resuelven en unos segundos.
    """
    import time

    import cvat_sdk
    from cvat_sdk import make_client

    env = read_cvat_env()
    for attempt in range(1, retries + 1):
        try:
            client = make_client(env["CVAT_URL"], credentials=(env["CVAT_USER"], env["CVAT_PASSWORD"]))
            break
        except Exception as exc:
            if attempt == retries:
                raise ConnectionError(f"CVAT no responde en {env['CVAT_URL']} tras {retries} intentos: {exc}") from exc
            print(f"CVAT no responde (intento {attempt}/{retries}); reintentando en {wait_s} s...")
            time.sleep(wait_s)
    server_version = client.api_client.server_api.retrieve_about()[0].version
    if server_version.lstrip("v").split("-")[0] != cvat_sdk.__version__:
        print(f"Aviso: servidor CVAT {server_version} y cvat-sdk {cvat_sdk.__version__} no coinciden.")
    return client


def task_url(task):
    return f"{read_cvat_env()['CVAT_URL']}/tasks/{task.id}"


def lote_dir(lote):
    return path("anotacion") / lote


def images_in_lotes(exclude=None):
    """Nombres de imagen ya incluidos en algún lote (para no repetirlos en uno nuevo)."""
    names = set()
    for indice_file in path("anotacion").glob("*/indice.csv"):
        if indice_file.parent.name != exclude:
            names |= set(pd.read_csv(indice_file)["image"])
    return names


def car_state_attribute():
    """Atributo `estado` de la etiqueta car (para validar la clasificación de 06_clasificacion_estado_vehiculos)."""
    from cvat_sdk import models
    from estado_vehiculos import ESTADOS

    return models.AttributeRequest(
        name="estado", mutable=False, input_type="select", default_value="desconocido", values=ESTADOS
    )


def get_or_create_project(client, name=None):
    """Proyecto CVAT con las etiquetas de CLASS_NAMES (lo crea si no existe).

    La etiqueta `car` lleva el atributo `estado` (desconocido / esperando / aparcado / circulando).
    """
    from cvat_sdk import models

    name = name or load_config()["cvat"]["proyecto"]
    project = next((p for p in client.projects.list() if p.name == name), None)
    if project is None:
        return client.projects.create(models.ProjectWriteRequest(
            name=name,
            labels=[
                models.PatchedLabelRequest(
                    name=label, type="rectangle", attributes=[car_state_attribute()] if label == "car" else []
                )
                for label in CLASS_NAMES
            ],
        ))

    missing = set(CLASS_NAMES) - {label.name for label in project.get_labels()}
    if missing:
        raise ValueError(f"El proyecto CVAT '{name}' no tiene las etiquetas {missing}.")
    return project


def create_lote(client, project, lote, selection, segment_size, keep_order=False):
    """Crea la carpeta del lote, su índice y la tarea de CVAT.

    `selection` debe tener las columnas `image` (nombre único), `camera` y `path` (ruta relativa
    de la imagen original), y opcionalmente columnas de contexto que se copian al índice.
    Con keep_order=True CVAT respeta el orden de `selection` (útil para lotes priorizados).
    """
    from cvat_sdk import models

    directory = lote_dir(lote)
    if (directory / "indice.csv").exists():
        raise FileExistsError(f"El lote {lote} ya existe ({directory}). Usa otro nombre de lote.")

    images_dir = directory / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    for row in selection.itertuples():
        shutil.copy2(image_path(row.path), images_dir / row.image)

    context = [c for c in ["timestamp", "timestamp_local", "time_slot_2h", "day_type", "illumination", "weather", "prioridad"]
               if c in selection.columns]
    indice = selection[["image", "camera"] + context].copy()
    indice["source_path"] = selection["path"].values
    indice["lote"] = lote
    indice["label_path"] = ""
    indice["n_cajas"] = pd.NA
    indice["estado"] = "pendiente"
    indice.to_csv(directory / "indice.csv", index=False)

    task = client.tasks.create_from_data(
        spec=models.TaskWriteRequest(name=lote, project_id=project.id, segment_size=segment_size),
        resources=[str(images_dir / name) for name in indice["image"]],
        data_params={"image_quality": 95, "sorting_method": "predefined" if keep_order else "natural"},
    )
    (directory / "cvat_task.json").write_text(json.dumps({"task_id": task.id, "project_id": project.id}, indent=2))
    return task


def load_task(client, lote):
    task_file = lote_dir(lote) / "cvat_task.json"
    if not task_file.exists():
        raise FileNotFoundError(f"El lote {lote} no tiene tarea en CVAT ({task_file}).")
    return client.tasks.retrieve(json.loads(task_file.read_text())["task_id"])


def pre_annotate(client, task, weights, conf, imgsz, force=False):
    """Pre-anotación automática YOLO26 de toda la tarea (sustituye las cajas existentes).

    Por seguridad, se niega a ejecutarse si la tarea ya tiene cajas manuales o semiautomáticas
    (trabajo de revisión humana que se perdería), salvo con force=True.
    """
    import cvat_sdk.auto_annotation as cvataa
    import torch

    from cvat_sdk.core.helpers import DeferredTqdmProgressReporter
    from cvat_yolo26 import Yolo26PreAnnotator

    human = sum(1 for s in task.get_annotations().shapes if str(s.source) != "auto")
    if human and not force:
        raise RuntimeError(
            f"La tarea {task.id} ya tiene {human} cajas revisadas a mano: la pre-anotación las borraría. "
            "No se ejecuta (usa force=True solo si quieres descartar ese trabajo)."
        )

    device = 0 if torch.cuda.is_available() else "cpu"
    function = Yolo26PreAnnotator(weights=weights, imgsz=imgsz, conf=conf, device=device)
    cvataa.annotate_task(client, task.id, function, clear_existing=True, pbar=DeferredTqdmProgressReporter())


def jobs_status(task):
    """Estado de cada job de la tarea con su rango de fotogramas."""
    return pd.DataFrame([
        {
            "job": j.id,
            "desde": j.start_frame,
            "hasta": j.stop_frame,
            "estado": str(getattr(j.state, "value", j.state)),
            "etapa": str(getattr(j.stage, "value", j.stage)),
            "asignado": getattr(j.assignee, "username", None),
        }
        for j in sorted(task.get_jobs(), key=lambda j: j.start_frame)
    ])


def annotation_counts(client, task):
    """Cajas por clase y por origen (auto = pre-anotación, manual/semi-auto = revisión humana)."""
    labels = {label.id: label.name for label in client.projects.retrieve(task.project_id).get_labels()}
    shapes = task.get_annotations().shapes
    counts = pd.DataFrame([{"clase": labels[s.label_id], "origen": str(s.source)} for s in shapes], columns=["clase", "origen"])
    return counts.value_counts().unstack(fill_value=0).reindex(CLASS_NAMES, fill_value=0)


def export_lote(client, task, lote):
    """Exporta las etiquetas de los jobs TERMINADOS del lote.

    Las imágenes de jobs terminados pasan a `revisada` con su .txt en labels/ (vacío si no hay
    objetos, que es un ejemplo negativo válido); las demás siguen `pendiente`. Las clases se
    reasignan por nombre a CLASS_NAMES. Devuelve el índice actualizado.
    """
    directory = lote_dir(lote)
    jobs = jobs_status(task)
    done = jobs[jobs["estado"] == "completed"]
    if done.empty:
        raise RuntimeError("Ningún job del lote está terminado (Menu -> Finish the job en CVAT).")

    formats = {f.name for f in client.api_client.server_api.retrieve_annotation_formats()[0].exporters}
    export_format = next(f for f in EXPORT_FORMATS if f in formats)

    export_dir = directory / "export"
    shutil.rmtree(export_dir, ignore_errors=True)
    export_dir.mkdir(parents=True)
    zip_path = task.export_dataset(export_format, export_dir / f"{lote}.zip", include_images=False)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(export_dir / "unzipped")
    unzipped = export_dir / "unzipped"

    export_names = read_export_names(unzipped)
    label_files = find_label_files(unzipped)

    # Fotograma de CVAT -> nombre de imagen, para saber qué imágenes pertenecen a jobs terminados
    frame_names = [Path(f.name).stem for f in task.get_frames_info()]
    reviewed = {frame_names[i] for row in done.itertuples() for i in range(row.desde, row.hasta + 1)}

    labels_dir = directory / "labels"
    labels_dir.mkdir(exist_ok=True)
    indice = pd.read_csv(directory / "indice.csv", dtype={"camera": str})
    for i, image in enumerate(indice["image"]):
        stem = Path(image).stem
        if stem not in reviewed:
            continue
        raw_lines = label_files[stem].read_text(encoding="utf-8").splitlines() if stem in label_files else []
        lines = remap_lines(raw_lines, export_names, CLASS_TO_IDX)
        (labels_dir / f"{stem}.txt").write_text("\n".join(lines), encoding="utf-8")
        indice.loc[i, ["label_path", "n_cajas", "estado"]] = [f"labels/{stem}.txt", len(lines), "revisada"]

    indice.to_csv(directory / "indice.csv", index=False)
    return indice


# =====================================================
# ESTADO DE LOS VEHÍCULOS (atributo `estado` de car)
# =====================================================

def export_car_states(client, task, lote):
    """Coches con `estado` distinto de desconocido marcados en CVAT -> anotacion/<lote>/estado_vehiculos.csv.

    Sirve como referencia manual para validar la clasificación automática de 06_clasificacion_estado_vehiculos.
    Cajas en coordenadas normalizadas (0-1) respecto al tamaño de la imagen.
    """
    labels = {label.id: label for label in client.projects.retrieve(task.project_id).get_labels()}
    frames = task.get_frames_info()

    rows = []
    for shape in task.get_annotations().shapes:
        label = labels[shape.label_id]
        if label.name != "car":
            continue
        specs = {a.id: a.name for a in label.attributes}
        values = {specs.get(a.spec_id): a.value for a in shape.attributes}
        if values.get("estado", "desconocido") == "desconocido":
            continue
        meta = frames[shape.frame]
        x1, y1, x2, y2 = shape.points
        rows.append({
            "image": Path(meta.name).name,
            "camera": Path(meta.name).stem.split("_", 1)[0],
            "x1": x1 / meta.width, "y1": y1 / meta.height, "x2": x2 / meta.width, "y2": y2 / meta.height,
            "estado": values["estado"],
        })

    states = pd.DataFrame(rows, columns=["image", "camera", "x1", "y1", "x2", "y2", "estado"])
    states.to_csv(lote_dir(lote) / "estado_vehiculos.csv", index=False)
    return states


# =====================================================
# ZONAS DE ESPERA Y APARCAMIENTO POR CÁMARA
# =====================================================

# paso_peatones: paso de cebra que cruzan los peatones (para inferir la fase peatonal y
# para no contar como "esperando" un vehículo detenido sobre el paso)
ZONE_LABELS = ["zona_espera", "zona_aparcamiento", "paso_peatones"]


def get_or_create_zones_project(client, name=None):
    """Proyecto CVAT aparte (etiquetas de polígono) para dibujar las zonas de cada cámara."""
    from cvat_sdk import models

    name = name or load_config()["estado_vehiculos"]["proyecto_zonas"]
    project = next((p for p in client.projects.list() if p.name == name), None)
    if project is None:
        project = client.projects.create(models.ProjectWriteRequest(
            name=name,
            labels=[models.PatchedLabelRequest(name=label, type="polygon") for label in ZONE_LABELS],
        ))
    return project


def create_zones_task(client, project, images):
    """Tarea con una imagen de referencia por cámara (lista de rutas, nombre <cámara>_<timestamp>.jpg)."""
    from cvat_sdk import models

    return client.tasks.create_from_data(
        spec=models.TaskWriteRequest(name="zonas_camaras", project_id=project.id, segment_size=len(images)),
        resources=[str(p) for p in images],
        data_params={"image_quality": 95, "sorting_method": "natural"},
    )


def export_zones(client, task, json_path):
    """Polígonos dibujados en la tarea de zonas -> JSON por cámara con puntos normalizados (0-1)."""
    labels = {label.id: label.name for label in client.projects.retrieve(task.project_id).get_labels()}
    frames = task.get_frames_info()

    zones = {}
    for shape in task.get_annotations().shapes:
        if str(getattr(shape.type, "value", shape.type)) != "polygon":
            continue
        meta = frames[shape.frame]
        camera = Path(meta.name).stem.split("_", 1)[0]
        points = shape.points
        polygon = [(points[i] / meta.width, points[i + 1] / meta.height) for i in range(0, len(points), 2)]
        zones.setdefault(camera, {z: [] for z in ZONE_LABELS})[labels[shape.label_id]].append(polygon)

    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps({
        "descripcion": "Zonas por cámara dibujadas en CVAT (03c_anotacion_zonas_estado_vehiculos). Puntos normalizados (x, y) en 0-1.",
        "tarea_cvat": task.id,
        "camaras": zones,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return zones
