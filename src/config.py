"""Carga de config.yaml y resolución de rutas del proyecto."""

from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.yaml"


@lru_cache(maxsize=1)
def load_config():
    import yaml

    return yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))


def path(key):
    """Ruta absoluta de una entrada de `rutas` en config.yaml (p. ej. path("raw"))."""
    return PROJECT_ROOT / load_config()["rutas"][key]


def relative(p):
    """Ruta relativa a la raíz del proyecto en formato POSIX (la que se guarda en las fases)."""
    return Path(p).resolve().relative_to(PROJECT_ROOT).as_posix()
