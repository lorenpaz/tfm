"""
Lectura de las exportaciones de CVAT en formato YOLO y reasignación de clases.

CVAT numera las clases según el orden de etiquetas del proyecto, que no tiene por qué
coincidir con CLASS_NAMES. Las etiquetas se reasignan por NOMBRE.

TFM - Máster en Inteligencia Artificial
Autor: Lorenzo Jose de la Paz Suarez
"""

from pathlib import Path


def read_export_names(export_dir):
    """Nombres de clase del export: data.yaml (Ultralytics YOLO) u obj.names (YOLO 1.1)."""
    export_dir = Path(export_dir)

    data_yaml = export_dir / "data.yaml"
    if data_yaml.exists():
        import yaml

        names = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))["names"]
        return names if isinstance(names, list) else [names[k] for k in sorted(names)]

    obj_names = export_dir / "obj.names"
    if obj_names.exists():
        return [line.strip() for line in obj_names.read_text(encoding="utf-8").splitlines() if line.strip()]

    raise FileNotFoundError(f"No se encuentra data.yaml ni obj.names en {export_dir}")


def find_label_files(export_dir):
    """{stem: ruta} de los .txt de etiquetas (en subcarpetas; en la raíz solo hay listas de ficheros)."""
    export_dir = Path(export_dir)
    return {p.stem: p for p in export_dir.rglob("*.txt") if p.parent != export_dir}


def remap_lines(lines, export_names, class_to_idx):
    """Reasigna el índice de clase de cada línea YOLO ('cls cx cy w h') según el nombre.

    Lanza ValueError si el export contiene una clase que no está en CLASS_NAMES.
    Las líneas vacías o mal formadas se descartan.
    """
    remapped = []
    for line in lines:
        parts = line.split()
        if len(parts) != 5:
            continue
        name = export_names[int(parts[0])]
        if name not in class_to_idx:
            raise ValueError(f"Clase '{name}' del export de CVAT no está en CLASS_NAMES")
        remapped.append(" ".join([str(class_to_idx[name])] + parts[1:]))
    return remapped
