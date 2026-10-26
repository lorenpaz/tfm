"""
Carga de config.yaml, claves privadas (.env) y resolución de rutas del proyecto

TFM - Máster en Inteligencia Artificial
Autor: Lorenzo Jose de la Paz Suarez
"""

import os

from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.yaml"
ENV_FILE = PROJECT_ROOT / ".env"


def get_secret(name, env_file=ENV_FILE):
    """Clave privada (p. ej. AEMET_API_KEY): variable de entorno o, si no existe, el fichero .env.
    El .env de la raíz del proyecto está excluido de git (ver .env.example).
    Devuelve "" si no se encuentra.
    """
    if os.environ.get(name):
        return os.environ[name]

    env_file = Path(env_file)
    if not env_file.exists():
        return ""

    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip("\"'")
    return ""


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
