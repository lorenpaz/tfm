"""
Migra los nombres de las capturas antiguas (hora local de Madrid, YYYYMMDD_HHMMSS.jpg)
al formato UTC usado por captura_camaras.py (YYYYMMDDTHHMMSSZ.jpg).

También actualiza los CSV de metadata/ (capture_time en ISO UTC e image_file relativo).
Solo usa la librería estándar, para poder ejecutarse sin el entorno virtual.

Por defecto solo simula. Para aplicar los cambios:
    python scripts/migrar_nombres_utc.py --apply

Se guarda la correspondencia nombre_antiguo -> nombre_nuevo en
data/malaga/metadata/migracion_utc_<fecha>.csv para poder deshacer la migración.
"""

import argparse
import csv
import re

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent.parent / "data" / "malaga"
RAW_DIR = BASE_DIR / "raw"
METADATA_DIR = BASE_DIR / "metadata"

LOCAL_TZ = ZoneInfo("Europe/Madrid")
OLD_STAMP = re.compile(r"^\d{8}_\d{6}$")
FILENAME_FORMAT = "%Y%m%dT%H%M%SZ"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
PLAN_FIELDS = ["camera_id", "old_name", "new_name", "capture_time_utc", "ambiguous", "conflict"]


def local_to_utc(stamp):
    """'20260825_164834' (hora local Madrid) -> (datetime UTC, hora ambigua/inexistente por cambio de hora)."""
    naive = datetime.strptime(stamp, "%Y%m%d_%H%M%S")
    local = naive.replace(tzinfo=LOCAL_TZ)
    ambiguous = local.utcoffset() != naive.replace(tzinfo=LOCAL_TZ, fold=1).utcoffset()
    return local.astimezone(timezone.utc), ambiguous


def plan_renames():
    plan = []

    for camera_dir in sorted(p for p in RAW_DIR.iterdir() if p.is_dir()):
        for image in sorted(camera_dir.glob("*.jpg")):
            if not OLD_STAMP.match(image.stem):
                continue

            utc, ambiguous = local_to_utc(image.stem)
            target = camera_dir / f"{utc.strftime(FILENAME_FORMAT)}.jpg"

            plan.append({
                "camera_id": camera_dir.name,
                "old_name": image.name,
                "new_name": target.name,
                "capture_time_utc": utc.strftime(ISO_FORMAT),
                "ambiguous": ambiguous,
                "conflict": target.exists(),
            })

    return plan


def migrate_metadata(plan, apply):
    """Convierte capture_time a ISO UTC e image_file a ruta relativa en los CSV de metadata."""
    lookup = {(r["camera_id"], r["old_name"]): r["new_name"] for r in plan}

    for csv_file in sorted(METADATA_DIR.glob("capturas_*.csv")):
        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fields = list(reader.fieldnames or [])
            rows = list(reader)

        if "capture_time" not in fields:
            continue

        converted = 0
        for row in rows:
            if not OLD_STAMP.match(row["capture_time"] or ""):
                continue

            row["capture_time"] = local_to_utc(row["capture_time"])[0].strftime(ISO_FORMAT)
            if row.get("image_file"):
                old_name = Path(row["image_file"].replace("\\", "/")).name
                new_name = lookup.get((row["camera_id"], old_name), old_name)
                row["image_file"] = f"raw/{row['camera_id']}/{new_name}"
            converted += 1

        if not converted:
            print(f"{csv_file.name}: ya migrado")
            continue

        if "server_last_modified" not in fields:
            fields.insert(fields.index("capture_time") + 1, "server_last_modified")

        print(f"{csv_file.name}: {converted} filas a convertir")

        if apply:
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="aplica los cambios (por defecto solo simula)")
    args = parser.parse_args()

    plan = plan_renames()
    conflicts = [r for r in plan if r["conflict"]]

    if not plan:
        print("No hay ficheros con el formato antiguo.")
    else:
        print(f"Ficheros a renombrar: {len(plan)} en {len({r['camera_id'] for r in plan})} cámaras")
        print(f"Horas ambiguas (cambio de hora): {sum(r['ambiguous'] for r in plan)}")
        print(f"Conflictos (destino ya existe): {len(conflicts)}")
        for r in plan[:3]:
            print(f"  {r['camera_id']}/{r['old_name']} -> {r['new_name']}")

    migrate_metadata(plan, args.apply)

    if not args.apply:
        print("\nSimulación: no se ha modificado nada. Usa --apply para aplicar.")
        return

    if not plan:
        return

    mapping_file = METADATA_DIR / f"migracion_utc_{datetime.now(timezone.utc).strftime(FILENAME_FORMAT)}.csv"
    with open(mapping_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PLAN_FIELDS)
        writer.writeheader()
        writer.writerows(plan)

    renamed = 0
    for r in plan:
        if r["conflict"]:
            continue
        camera_dir = RAW_DIR / r["camera_id"]
        (camera_dir / r["old_name"]).rename(camera_dir / r["new_name"])
        renamed += 1

    print(f"\nRenombrados: {renamed}. Correspondencia guardada en {mapping_file}")


if __name__ == "__main__":
    main()
