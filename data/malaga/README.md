# Cámaras de tráfico de Málaga

Esta carpeta contiene los datos del caso de estudio: el catálogo municipal de cámaras de tráfico, las imágenes capturadas y las salidas de cada fase del pipeline. Las rutas se configuran en [`config.yaml`](../../config.yaml) (sección `rutas`).

**Convención de tiempo:** todas las marcas de tiempo (nombres de imagen, metadatos, fases) están en **UTC**. La hora de Madrid solo aparece en la columna `timestamp_local`.

---

## Ficheros de referencia

| Fichero | Contenido |
|---|---|
| `da_camarasTrafico-4326.csv` | **Catálogo oficial** de las 134 cámaras de tráfico del Ayuntamiento de Málaga (datos abiertos). Columnas clave: `ID`, `NOMBRE`, `DIRECCION`, `SDOGEOMETRIA` (coordenadas `POINT (lon lat)`, EPSG:4326) y `URLIMAGEN` (imagen en tiempo real). Se lee siempre con `catalogo.load_catalog()`, que obtiene `lat`/`lon` y limpia las URL (algunas traen un tabulador final). |
| `da_camarasTrafico-4326.geojson` | Mismo catálogo en formato GeoJSON, orientado a geometría espacial. |
| `analisis_camaras_trafico_malaga.md` | Análisis manual de las cámaras **por distrito**: enlace, número de semáforos visibles y observaciones de visibilidad. Sirvió para elegir las 24 cámaras de la captura continua (`config.yaml` → `captura.camaras`) y las 5 de referencia para medir el refresco. |
| `calendario_festivos_malaga.csv` | Festivos de 2026 y 2027 (nacionales, autonómicos y locales de Málaga): `Fecha`, `Festividad`, `Ambito`. Se usa para el `day_type` (`festivo` / `fin_de_semana` / `laborable`). |

## Imágenes y captura

### `raw/`
Imágenes capturadas, una carpeta por cámara: `raw/<ID_cámara>/<YYYYMMDDTHHMMSSZ>.jpg` (UTC, 640×480). Hay 134 carpetas:
- Las 24 cámaras seleccionadas reciben capturas continuas del servicio `scripts/captura_camaras.py`: cada 30 s en hora punta y cada 60 s el resto del tiempo. Las **5 de referencia** (21541, 21545, 21547, 21560 y 21563) se capturan **cada 6 s en hora punta**, para poder medir duraciones de fase. No se guardan las capturas en las que la cámara aún no ha publicado imagen nueva.
- Las demás solo tienen las instantáneas de `00_Descarga_Imagenes_Malaga`.

### `metadata/`
| Fichero | Contenido |
|---|---|
| `capturas_YYYYMMDD.csv` | Una fila por intento de captura del servicio, un fichero por día UTC. Columnas: `camera_id`, `camera_name`, `capture_time` (ISO UTC), `server_last_modified` (instante real de la imagen según el servidor), `image_file` (ruta relativa a esta carpeta, `raw/...`) y `status`: `OK`, `SIN_CAMBIOS` (mismo `Last-Modified` que la captura anterior; no se guarda imagen) o el error. |
| `captura_imagenes.csv` | Resultado de la última instantánea de todas las cámaras (`00_Descarga_Imagenes_Malaga`). |

### `logs/`
Logs del servicio de captura (NSSM): `capturas.log` (log propio, en UTC), `stdout.log` y `stderr.log` (salida y errores del proceso).

### `refresco/`
Mediciones de la frecuencia real de refresco de las cámaras (`00b_Frecuencia_Refresco` / `scripts/medir_refresco.py`):

| Fichero | Contenido |
|---|---|
| `refresco_<UTC>.csv` | Una fila por consulta: `camera_id`, `requested_at`, `status`, `last_modified` (cabecera del servidor), `sha1` y `size` de la imagen, y `elapsed_ms`. |
| `refresco_<UTC>_resumen.csv` | Intervalo entre imágenes nuevas por cámara y método (`last_modified` / `hash`): mediana, p10, p90 y antigüedad de la imagen al descargarla. **Lo leen `02_preprocess_labelled_basic` y `05_evaluation`.** |
| `refresco_<UTC>/<cámara>/` | Cada imagen nueva detectada durante la medición (~100 por cámara en 10 min). Útil para ver el ciclo semafórico a alta frecuencia. |

## Salidas del preprocesamiento

### `fases/`
Una salida por notebook 02. Se unen por `(camera, image)` con `pipeline.load_frames()`.

| Fichero | Generado por | Contenido |
|---|---|---|
| `frames.parquet` | `02_preprocess_labelled_basic` | Fotogramas válidos: ruta, `timestamp` (UTC), `timestamp_local`, `time_slot_2h`, `day_type`, `illumination`, resolución, brillo, nitidez y `quality_score`. |
| `blacklist_camaras.csv` | `02_preprocess_labelled_basic` | Por cámara: imágenes de día, fracción de fallos y si entra en la lista negra (>30 %). |
| `weather.parquet` | `02_preprocess_labelled_weather` | `weather` y la observación AEMET asignada: estación, distancia, diferencia temporal, precipitación, viento, humedad, temperatura... |
| `detections.parquet` | `02_preprocess_labelled_detection` | Conteos YOLO26 por fotograma (`n_pedestrian`, `n_car`, ..., `n_vehiculos`, semáforos por color). |
| `vehiculos_cajas.parquet` | `06_estado_vehiculos` | **Cajas** YOLO26 (clase, `x1..y2` en px, tamaño de imagen) de las secuencias a 6 s de las cámaras de referencia, para seguir vehículos entre imágenes. Hay una fila con `clase` vacía por imagen procesada, para registrar también las imágenes sin detecciones. Es incremental. |

### `weather_cache/`
Respuestas de AEMET guardadas para no repetir descargas: el inventario de estaciones y las observaciones diarias en tramos de 14 días (el límite de AEMET es 15). Si una respuesta es errónea, se borra su fichero para que se vuelva a descargar.

## Anotación y resultados

### `anotacion/<lote>/`
Lotes de anotación de `03_anotacion_cvat`:

| Fichero | Contenido |
|---|---|
| `images/` | Copias de las imágenes del lote con nombre único `<cámara>_<timestamp>.jpg` (los timestamps se repiten entre cámaras). |
| `indice.csv` | Una fila por imagen: contexto (franja, tipo de día, iluminación), `prioridad` (solo en lotes priorizados; 1 = la primera del job), `source_path` (imagen original), `label_path`, `n_cajas` y `estado` (`pendiente` → `revisada` cuando su job se termina y se exporta). **`04_training` solo usa las revisadas.** |
| `cvat_task.json` | IDs de la tarea y del proyecto en CVAT del lote. |
| `labels/` | Etiquetas YOLO revisadas, con las clases ya reasignadas a `CLASS_NAMES`. Se crea al exportar. |
| `export/` | Zip exportado de CVAT y su contenido (temporal). |

Cuando se exportan los estados marcados en CVAT, cada lote incluye también `estado_vehiculos.csv`: los coches con atributo `estado`, con caja normalizada (0-1) y estado manual.

### `zonas/`
| Fichero | Contenido |
|---|---|
| `zonas_camaras.json` | Polígonos `zona_espera`, `zona_aparcamiento` y `paso_peatones` por cámara de referencia, con puntos normalizados (0-1). Se dibujan en CVAT (tarea 3) y los exporta `06_estado_vehiculos`. |
| `cvat_task.json` | Identificador de la tarea de zonas en CVAT. |
| `imagenes/` | Copia de la imagen de referencia de cada cámara (la diurna de más calidad). No versionada. |

### `resultados/`
- Indicadores de `05_evaluation`: `indicadores_por_camara.csv`, `indicadores_por_franja.csv` e `indicadores_por_contexto.csv` (por tipo de día, iluminación y clima).
- `estado_vehiculos.csv` (`06`): una fila por caja de vehículo seguida, con `track`, zona, si está detenido, segundos inmóvil y estado.
- Aquí se guardarán también las métricas de `04_training` (`metricas_map_por_clase.csv`, `metricas_test_por_clase.csv`).
