# Código común (`src/`)

Módulos compartidos por los notebooks y los scripts. Concentran la lógica que antes estaba duplicada en varios notebooks: rutas, marcas de tiempo, calidad, detección, fases del pipeline... Así hay una sola implementación de cada cosa, que además se puede probar con tests.

**Cómo se usan:** los notebooks y scripts añaden esta carpeta al `sys.path` y la importan directamente:

```python
PROJECT_ROOT = Path.cwd().resolve().parent          # desde notebooks/
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from config import load_config, path
```

**Tests:** [`tests/`](../tests) cubre las funciones donde un error pasaría desapercibido: marcas de tiempo, conversión UTC en los cambios de hora, coordenadas de AEMET, reasignación de clases de CVAT y claves del `.env`. Se ejecutan con `.venv\Scripts\python.exe -m pytest tests` (31 tests, incluidos el seguimiento y la clasificación del estado de los vehículos y la separación mínima en la selección de lotes).

## Dependencias entre módulos

```
config ◄── catalogo
       ◄── pipeline
deteccion ◄── cvat_yolo26 ◄── cvat_lotes ──► anotacion, pipeline, config
priorizacion (independiente: solo pandas/numpy)
estado_vehiculos (independiente: solo librería estándar)
tiempo, calidad, meteo, anotacion: independientes (tiempo, meteo y anotacion solo usan la librería estándar)
```

---

## config.py — configuración, rutas y claves

| Función | Descripción |
|---|---|
| `load_config()` | Lee `config.yaml` (una sola vez, con caché). |
| `path(clave)` | Ruta absoluta de una entrada de `rutas` (p. ej. `path("raw")`). |
| `relative(p)` | Ruta relativa a la raíz del proyecto, en formato POSIX. Es la que se guarda en las fases. |
| `get_secret(nombre)` | Clave privada: primero la variable de entorno y, si no existe, el fichero `.env` de la raíz (excluido de git; plantilla en `.env.example`). Se usa para `AEMET_API_KEY`. |

**Decisión:** un único `config.yaml` para rutas, cámaras, umbrales, modelos y zona horaria, en lugar de constantes repetidas en cada notebook. Las claves privadas nunca van en `config.yaml` ni en el código.

## tiempo.py — marcas de tiempo e iluminación

| Función | Descripción |
|---|---|
| `parse_timestamp_from_name(nombre)` | UTC a partir del nombre de la imagen (`20260825T144834Z`, con o sin prefijo de cámara). El soporte del formato antiguo en hora local se retiró junto con el script de migración. |
| `to_local(ts_utc)` | UTC → hora de Madrid. Tiene en cuenta los cambios de hora. |
| `time_slot_2h(ts_local)` | Franja horaria de 2 h (`"16:00-18:00"`). |
| `day_type(ts_local, festivos)` | `festivo`, `fin_de_semana` o `laborable`. |
| `load_holidays(csv)` | Fechas del calendario de festivos. |
| `solar_elevation(ts_utc, lat, lon)` | Elevación del sol en grados (algoritmo aproximado de la NOAA, error < 1°). |
| `illumination(ts_utc, lat, lon)` | `dia` (sol sobre el horizonte), `crepusculo` (entre 0° y −6°) o `noche`. |

**Decisiones:**
- **UTC en todo el almacenamiento** y hora local solo para franjas y tipo de día.
- La iluminación se calcula por **posición solar**, no por hora fija ni por brillo de la imagen: cambia con la estación y es independiente del clima.
- El módulo solo usa la librería estándar, para poder probarlo sin dependencias.

## calidad.py — calidad visual y lista negra

| Función | Descripción |
|---|---|
| `list_camera_images(raw_dir)` | Imágenes de `raw/<ID>/`. Ignora carpetas que no son cámaras, como `.ipynb_checkpoints`. |
| `image_metrics(ruta)` | Resolución, brillo medio y nitidez (varianza del Laplaciano). |
| `add_quality(df, cfg)` | Criterios de validez y `quality_score`. |
| `camera_blacklist(df, max_fallos)` | Fracción de imágenes de día no válidas por cámara y si entra en la lista negra. |

**Decisiones:**
- El **brillo mínimo solo se exige de día**: las imágenes nocturnas son oscuras por naturaleza.
- El **umbral de nitidez es un percentil** de la distribución observada; un valor fijo como 25 no filtraba nada con valores típicos de ~4000.
- `quality_score` combina los **percentiles** de brillo y nitidez para que ambos tengan la misma escala. Con los valores brutos, la nitidez dominaba.
- La lista negra exige **más de un 30 % de fallos diurnos**. Antes, una sola imagen mala descartaba la cámara.

## catalogo.py — catálogo de cámaras

| Función | Descripción |
|---|---|
| `parse_point(geom)` | `(lat, lon)` de una geometría WKT `POINT (lon lat)`. |
| `load_catalog()` | Catálogo con `ID` como texto, `URLIMAGEN` sin espacios ni tabuladores y columnas `lat`/`lon`. |

**Decisión:** un único punto de lectura del catálogo, que corrige sus problemas: no trae columnas de coordenadas y algunas URL tienen un tabulador final que provocaba 404.

## meteo.py — AEMET y clasificación meteorológica

| Función | Descripción |
|---|---|
| `dms_to_decimal(valor)` | Coordenada del inventario de AEMET (`364000N`, `0042900W`) a grados decimales. |
| `haversine_km(...)` | Distancia entre dos puntos en km. |
| `classify_weather(prec, vis, hr, wind, nub)` | `rain` > `fog` > `windy` > `cloudy` > `sunny`, por orden de prioridad. Ignora los valores nulos. |

**Decisión:** las reglas de clima viven en una función pura, probada con tests. La iluminación (noche) no forma parte del clima.

## pipeline.py — fases del preprocesamiento

| Función | Descripción |
|---|---|
| `save_phase(df, nombre)` / `load_phase(nombre)` | Escriben y leen `data/malaga/fases/<nombre>.parquet`. Comprueban que existan las claves `(camera, image)` y que no haya duplicados. |
| `load_frames(*fases)` | Fase `frames` unida con las fases indicadas que existan (`weather`, `detections`). |
| `image_path(rel)` | Ruta absoluta de una imagen guardada como ruta relativa. |
| `measured_refresh_s()` | Refresco mediano de la última medición de `00b` (o `None`). |
| `sampling_seconds()` | Intervalo de muestreo: el refresco medido o el valor por defecto de `config.yaml`. |
| `sample_every(df, s)` | Como máximo un fotograma por cámara cada `s` segundos. |
| `service_cameras()` / `only_service_cameras(df)` | Cámaras del servicio de captura (24) y filtro para quedarse solo con ellas. Lo usan `03`, `03b` y `05`: las demás solo tienen 1–2 instantáneas. |
| `stratified_selection(df, estratos, n, max_por_camara, semilla, min_gap_s)` | Selección en *round-robin* entre estratos para los lotes de CVAT, con un mínimo de `min_gap_s` segundos entre imágenes de la misma cámara para evitar casi-duplicados. |

**Decisión:** **una salida por fase** en lugar de un único CSV que reescribían tres notebooks. Antes, el resultado dependía del orden de ejecución y una fase podía pisar el trabajo de otra. Ahora las fases son independientes y se unen al leerlas.

## anotacion.py — exportaciones de CVAT

| Función | Descripción |
|---|---|
| `read_export_names(dir)` | Nombres de clase del export: `data.yaml` (Ultralytics YOLO) u `obj.names` (YOLO 1.1). |
| `find_label_files(dir)` | Ficheros `.txt` de etiquetas del export. Excluye las listas de ficheros de la raíz. |
| `remap_lines(lineas, nombres, clase_a_idx)` | Reasigna el índice de clase de cada línea YOLO **por nombre**. Falla si aparece una clase desconocida. |

**Decisión:** CVAT numera las clases según el orden de etiquetas de su proyecto. Reasignarlas por nombre evita entrenar con clases intercambiadas sin que nadie lo note.

## deteccion.py — clases del detector y YOLO26

| Elemento | Descripción |
|---|---|
| `CLASS_NAMES` | Las 11 clases del detector, cuyo orden define el índice YOLO: `pedestrian`, `car`, `bus`, `truck`, `motorcycle`, `traffic_light_red/yellow/green/unknown` y `pedestrian_light_red/green`. Es la **fuente única** para CVAT y el entrenamiento. `pedestrian` corresponde a la clase COCO `person` (renombrada el 17/10/2026; en CVAT se renombró la etiqueta conservando su identificador, así que las anotaciones existentes no se perdieron). |
| `predict_boxes(modelo, img)` | Inferencia YOLO26 con pesos COCO: cajas con las clases de `CLASS_NAMES` y el color del semáforo por caja. |
| `classify_traffic_light_color(img, caja)` | Color dominante en HSV (rojo, ámbar o verde), o `None`. |
| `is_pedestrian_light(caja, forma)` | Heurística: caja pequeña en la mitad inferior de la imagen. |
| `frame_counts(cajas, forma)` | Conteos por clase y `n_vehiculos`. (`pedestrian_group` se retiró por redundante: equivalía a `n_pedestrian >= 3`.) |

**Decisiones:**
- `traffic_light_unknown` existe para los semáforos vistos de lado, de espaldas o apagados, en lugar de forzar un color.
- Los peatonales no tienen ámbar: una caja ámbar se mantiene como semáforo vehicular.
- **Limitación conocida:** la clasificación HSV confunde con ámbar casi todos los semáforos (14.113 cajas ámbar frente a 160 rojas y verdes en la ejecución actual). Por eso las etiquetas de entrenamiento las revisa un humano en CVAT, y el modelo entrenado aprende el color como clase.

## cvat_yolo26.py — pre-anotación automática en CVAT

`Yolo26PreAnnotator` es una función de auto-anotación compatible con `cvat_sdk.auto_annotation`. Declara las 11 etiquetas de `CLASS_NAMES` y, para cada imagen de la tarea, devuelve las cajas de `predict_boxes`. Se usa desde `03a_anotacion_lote_estratificado` y también desde la CLI de CVAT (`cvat-cli task auto-annotate <id> --function-module cvat_yolo26`).

**Decisión:** las cajas de YOLO26 son solo un **punto de partida**; un humano las corrige en CVAT. Así se evita el entrenamiento circular, que se daba al entrenar con etiquetas generadas por el propio detector.

## cvat_lotes.py — lotes de anotación en CVAT

| Función | Descripción |
|---|---|
| `connect()` | Cliente de CVAT con las credenciales de `cvat/.env`. Reintenta ante cortes puntuales de la red de Docker Desktop. |
| `get_or_create_project(client)` | Proyecto con las etiquetas de `CLASS_NAMES`. |
| `create_lote(client, project, lote, seleccion, segment_size, keep_order)` | Copia las imágenes, escribe `indice.csv` y crea la tarea. Con `keep_order=True` respeta el orden de la selección (lotes priorizados). |
| `pre_annotate(client, task, ...)` | Pre-anotación YOLO26 de la tarea. **Se niega si hay cajas revisadas a mano**, porque las borraría. |
| `jobs_status(task)` / `annotation_counts(client, task)` | Estado y rango de cada job; cajas por clase y origen (`auto`, `manual`, `semi-auto`). |
| `export_lote(client, task, lote)` | Exporta **solo los jobs terminados**, reasigna las clases por nombre y marca esas imágenes como `revisada`. |

| `export_car_states(client, task, lote)` | Coches con `estado` marcado en CVAT → `anotacion/<lote>/estado_vehiculos.csv`, la referencia manual para validar `06`. |
| `get_or_create_zones_project` / `create_zones_task` / `export_zones` | Proyecto aparte con etiquetas de polígono (`zona_espera`, `zona_aparcamiento`, `paso_peatones`), tarea con una imagen por cámara y exportación de los polígonos a `zonas_camaras.json` (coordenadas normalizadas). |

**Decisión:** un único módulo para la gestión de lotes, compartido por `03a`, `03b`, `03c` y `06`, con dos protecciones: no borrar trabajo humano y no exportar jobs sin terminar. Los proyectos nuevos crean la etiqueta `car` con el atributo `estado`.

## priorizacion.py — lotes que compensan desequilibrios

| Función | Descripción |
|---|---|
| `group_counts(frames)` | Instancias por grupo y fotograma (objetos, semáforos de cualquier color, indicios de rojo/verde, peatonales, poca luz). |
| `class_balance(counts)` | Diagnóstico: instancias, imágenes con el grupo y ratio frente al mayoritario. |
| `annotated_group_totals(cajas_por_clase)` | Convierte lo ya anotado en CVAT en totales por grupo. |
| `greedy_balanced_selection(frames, counts, n, max_por_camara, initial_totals, min_gap_s)` | Selección voraz: la imagen que más aporta a los grupos escasos, con peso 1/(1 + acumulado) y sin imágenes de la misma cámara a menos de `min_gap_s` segundos. |

**Decisión:** el color de los semáforos pre-anotado no es fiable, así que se prioriza "tener semáforos" (de cualquier color) y los escasos indicios de rojo o verde. El ámbar no se prioriza.

## estado_vehiculos.py — esperando, aparcado o circulando

| Función | Descripción |
|---|---|
| `load_zones(json)` | Zonas por cámara dibujadas en CVAT (polígonos normalizados). |
| `point_in_polygon(x, y, poligono)` | Comprobación por *ray casting*. |
| `box_zone(caja, ancho, alto, zonas)` | Zona del **punto inferior central** de la caja, con prioridad aparcamiento > espera > `paso_peatones`. Un vehículo sobre el paso de peatones no cuenta como esperando. |
| `iou(a, b)` | Solape entre dos cajas. |
| `track_vehicles(fotogramas, iou_enlace, iou_inmovil, max_hueco_s)` | Enlaza las cajas entre imágenes consecutivas de una cámara (emparejamiento voraz por IoU) e indica para cada una si está detenida y desde cuándo está inmóvil. |
| `classify_state(zona, detenido, segundos_inmovil, aparcado_tras_s)` | Aparcado (zona de aparcamiento o ≥ 300 s inmóvil), esperando (zona de espera y detenido) o circulando. |
| `list_reference_images(camaras)` | Imágenes de las cámaras de referencia en `raw/` y `refresco/`, sin duplicados por instante. |
| `continuous_sequences(imagenes, max_hueco_s)` | Solo las imágenes de tramos continuos (vecina a ≤ `max_hueco_s`). La comparten `03c` (lote de validación) y `06`. |

**Decisión:** en una sola imagen no se distingue un coche aparcado de uno que espera, así que se combinan **zonas fijas por cámara** y **persistencia temporal** con las capturas a 6 s, en lugar de una clase nueva del detector. El atributo `estado` de CVAT sirve para medir el acierto. Detalle y resultados en [`notebooks/README.md`](../notebooks/README.md#06_clasificacion_estado_vehiculos).

## main.py

Punto de entrada reservado para el sistema final (análisis de tiempos de espera). Por ahora está vacío: todo el flujo se ejecuta desde los notebooks.
