# Pipeline de notebooks

Los notebooks de esta carpeta implementan el pipeline completo del TFM, desde la descarga de imágenes hasta la evaluación de los indicadores de tráfico. Se reutiliza código común (rutas, marcas de tiempo, calidad, detección, fases...):
- Código común en [`src/`](../src/README.md).
- Parámetros de configuración en [`config.yaml`](../config.yaml).

Todos los notebooks se ejecutan desde esta carpeta con el kernel **Python (TFM)** (`env_tfm`, el `.venv` del proyecto). La relación de cada notebook con los objetivos OE-1…OE-7 está en [`lineas-investigacion.md`](../lineas-investigacion.md#trazabilidad-entre-objetivos-y-notebooks).

## Orden de ejecución y flujo de datos

```
00a_captura_instantanea_catalogo ──► raw/ (instantánea de todas las cámaras)
00b_medicion_refresco_camaras ─────► refresco/ (cada cuánto publica cada cámara)
01a_eda_catalogo_camaras             (análisis del catálogo, sin salidas)
01b_eda_calidad_visual               (análisis de calidad, sin salidas)
        │
02a_preproceso_calidad_contexto ───► fases/frames.parquet + fases/blacklist_camaras.csv
02b_preproceso_meteorologia_aemet ─► fases/weather.parquet      (necesita frames)
02c_preproceso_deteccion_yolo26 ───► fases/detections.parquet   (necesita frames)
        │
03a_anotacion_lote_estratificado ──► anotacion/<lote>/ (imágenes, índice y etiquetas revisadas en CVAT)
03b_anotacion_lote_prioritario ────► anotacion/<lote_prioritario>/ (lote que compensa clases escasas)
03c_anotacion_zonas_estado_vehiculos ► zonas/zonas_camaras.json + anotacion/lote_03_estado_vehiculos/
        │
04_entrenamiento_yolo26 ───────────► runs/ + resultados/metricas_*.csv   (necesita lotes revisados)
05_evaluacion_indicadores_trafico ─► resultados/indicadores_*.csv        (necesita frames y detections)
06_clasificacion_estado_vehiculos ─► fases/vehiculos_cajas.parquet + resultados/estado_vehiculos.csv
                                     (necesita capturas a 6 s de las cámaras de referencia y las zonas de 03c)
```

`02b` y `02c` se pueden ejecutar en cualquier orden: cada fase escribe **solo su propio fichero**, y las fases se unen por `(camera, image)` con `pipeline.load_frames()`. Así ninguna fase puede sobrescribir el trabajo de otra.

## Convenciones comunes

- **Marcas de tiempo:** los nombres de fichero y la columna `timestamp` están en **UTC** (`20260825T144834Z.jpg`). `timestamp_local` (hora de Madrid) se usa solo para las franjas horarias y el tipo de día. Así se evitan las horas ambiguas o inexistentes de los cambios de hora.
- **Iluminación y clima por separado:** `illumination` (día / crepúsculo / noche) se calcula por **elevación solar** y es independiente del clima (`weather`).
- **Rutas:** las rutas de imagen guardadas en las fases son relativas a la raíz del proyecto.
- **Cámaras:** `03a`, `03b` y `05` trabajan solo con las 24 cámaras del servicio de captura (`pipeline.only_service_cameras`). Las demás tienen 1–2 instantáneas de `00a`.

---

## 00a_captura_instantanea_catalogo

**Objetivo:** descargar una imagen de **todas** las cámaras del catálogo (134) como instantánea. La captura continua de las cámaras seleccionadas la hace el servicio [`scripts/captura_camaras.py`](../scripts/README.md).

**Decisiones:**
- Cabeceras de navegador (`User-Agent`, `Referer`): sin ellas el servidor responde 403.
- `URLIMAGEN` se limpia en `catalogo.load_catalog()`: algunas URL traen un tabulador final.
- Reintentos con espera exponencial ante errores.

**Resultado:** 134 de 134 cámaras descargadas (12/10/2026) en `raw/<cámara>/<UTC>.jpg`, con sus metadatos en `metadata/captura_imagenes.csv`.

## 00b_medicion_refresco_camaras

**Objetivo:** saber **cada cuánto publica cada cámara una imagen nueva**, porque de eso depende si se pueden medir las duraciones de las fases semafóricas (OE-4).

**Decisiones:** se consultan 5 cámaras de referencia cada segundo durante 10 minutos y se comparan la cabecera `Last-Modified` del servidor (instante exacto de publicación) y el hash de la imagen (respaldo).

**Resultado:** las 5 cámaras refrescan cada **6 s** de mediana (p10 = 3–4 s, p90 = 8 s), y la imagen tiene unos 3 s de antigüedad al descargarla. Ambos métodos coinciden, así que `Last-Modified` es fiable. Como un ciclo semafórico dura ~60–120 s, un refresco de 6 s **sí permite medir duraciones de fase**, pero solo si se captura con esa frecuencia. El resumen guardado lo usan `02a` (intervalo de muestreo) y `05`.

## 01a_eda_catalogo_camaras

**Objetivo:** caracterizar el catálogo municipal: número de cámaras, nulos, duplicados y distribución geográfica.

**Decisiones:** el CSV no trae columnas `lat`/`lon`. Se derivan de `SDOGEOMETRIA` (`POINT (lon lat)`, EPSG:4326) con `catalogo.load_catalog()`.

**Resultado:** 134 cámaras, ninguna duplicada ni sin coordenadas. Cuatro columnas están vacías. La cobertura por distrito queda pendiente: el catálogo no trae el distrito.

## 01b_eda_calidad_visual

**Objetivo:** explorar la calidad visual (resolución, brillo y nitidez) para fijar los criterios de `02a`. Analiza una muestra de hasta 200 imágenes por cámara.

**Decisiones:**
- El brillo se analiza **por iluminación**: una imagen nocturna oscura es normal y no indica una cámara defectuosa.
- La nitidez se representa en escala logarítmica por su gran dispersión.
- El `quality_score` combina los **percentiles** de brillo y nitidez, no sus valores brutos, cuyas escalas difieren en un orden de magnitud.

**Resultado:** el 95 % de las 5.041 imágenes de la muestra es válido, y ninguna cámara entra en la lista negra.

## 02a_preproceso_calidad_contexto

**Objetivo:** primera fase del preprocesamiento. Calcula la calidad y el contexto temporal de cada imagen, filtra las no válidas y muestrea.

**Decisiones:**
- Se recorren las carpetas cuyo nombre es un ID de cámara.
- **Brillo mínimo solo de día.** El umbral de nitidez es un **percentil** de la distribución observada (`percentil_nitidez_min`), no un valor fijo.
- **Lista negra por fracción de fallos:** una cámara se descarta solo si falla más del 30 % de sus imágenes **de día**. La lista se recalcula en cada ejecución, de modo que una cámara que mejora vuelve a entrar.
- **Muestreo según el refresco medido:** como máximo un fotograma por cámara cada X segundos, siendo X el refresco de `00b` (6 s). No tiene sentido muestrear más rápido de lo que la cámara publica.
- Los festivos salen de `calendario_festivos_malaga.csv`.

**Resultado (datos hasta el 17/10/2026):** 74.508 fotogramas válidos de 78.957 imágenes, sin ninguna cámara en lista negra. La peor, la 21545, falla el 8,3 % de sus imágenes de día. Se descarta el 20 % de las imágenes nocturnas frente al 1 % de las diurnas, y los fotogramas proceden de solo 10 días.

## 02b_preproceso_meteorologia_aemet

**Objetivo:** etiquetar el clima de cada fotograma con la observación AEMET de la estación más cercana a su cámara.

**Decisiones:**
- La clave se lee con `config.get_secret("AEMET_API_KEY")`, desde la variable de entorno o el `.env` de la raíz (excluido de git).
- El inventario de AEMET da las coordenadas en grados-minutos-segundos (`364000N`); se convierten a grados decimales con `meteo.dms_to_decimal`. Antes se perdían y no se asignaba ninguna estación.
- **Modo automático:** si los fotogramas son de las últimas 24 h se usan observaciones horarias; si no, datos climatológicos **diarios**, situados a mediodía UTC y con una ventana de cruce de ±12 h.
- **Consultas en tramos de 14 días**, porque AEMET limita cada consulta diaria a 15 días.
- **Solo estaciones con datos:** la estación más cercana se elige entre las que tienen observaciones en el periodo. La más cercana a muchas cámaras (MÁLAGA, PUERTO) no publica datos diarios y dejaba el 75 % de los fotogramas como `unknown`.
- Se descartan las estaciones a más de 40 km.
- Las reglas de clasificación están en `meteo.classify_weather`, con prioridad rain > fog > windy > cloudy > sunny.

**Resultado:** el 77,1 % de los fotogramas tiene clima asignado, todo `sunny`, por las estaciones de Aeropuerto, Centro Meteorológico y Rincón de la Victoria. El 22,9 % restante, `unknown`, corresponde a días que AEMET aún no había publicado. Con datos diarios, la etiqueta describe el día, no el momento exacto de la imagen.

## 02c_preproceso_deteccion_yolo26

**Objetivo:** detectar con **YOLO26** preentrenado (COCO) los objetos de cada fotograma y guardar **conteos**: `n_pedestrian`, `n_car`, ..., `n_vehiculos` y semáforos por color. La clase de personas se llama `pedestrian` en todo el proyecto, aunque en COCO se llama `person`.

**Decisiones:**
- Se guardan **conteos**, no presencia 0/1, para calcular densidades reales en `05`.
- El color del semáforo se clasifica **por caja** (HSV). Los semáforos peatonales se separan con una heurística de tamaño y posición.
- Estas detecciones alimentan los indicadores de `05` y la priorización de `03b`, **no el entrenamiento**: las cajas para entrenar se revisan por humanos en CVAT (`03a`, `03b`), para evitar el entrenamiento circular.

**Resultado:** 74.454 fotogramas procesados, con una media de 6,4 coches y 1,2 personas por imagen.

**Limitación detectada:** la clasificación HSV del color está muy sesgada (26.642 ámbar frente a 325 rojos). Se presupone que confunde el ámbar con las carcasas, los reflejos y el alumbrado, así que se decide **reforzar el etiquetado humano** de los semáforos para mejorar la **fiabilidad**. La solución prevista es el detector entrenado con etiquetas revisadas en CVAT, que aprende el color como clase.

## 03a_anotacion_lote_estratificado

**Objetivo:** crear lotes de imágenes para anotar en CVAT, pre-anotados con YOLO26 y **revisados por un humano**, para obtener etiquetas de entrenamiento y test fiables.

**Decisiones:**
- **Muestreo estratificado en *round-robin*** entre cámara × franja horaria × tipo de día × iluminación, con un máximo por cámara (`pipeline.stratified_selection`), para que el lote no se concentre en las cámaras u horas con más capturas. Al menos 10 minutos entre dos imágenes de la misma cámara.
- Las imágenes se copian con un nombre único, `<cámara>_<timestamp>.jpg`, porque los timestamps se repiten entre cámaras. Un lote nuevo excluye las imágenes de lotes anteriores.
- La pre-anotación usa `cvat_sdk.auto_annotation` con la función de [`src/cvat_yolo26.py`](../src/README.md). Los semáforos peatonales los distingue el anotador.
- Un **protocolo de anotación** (tabla en el notebook) fija los criterios comunes: oclusión, color desconocido, peatonales...
- La exportación reasigna las clases **por nombre** (`anotacion.remap_lines`), porque el orden de etiquetas en CVAT puede diferir de `CLASS_NAMES`.
- **Exportación por jobs terminados:** solo las imágenes de jobs marcados como terminados pasan a `revisada`. Así se puede entrenar con lo ya revisado sin esperar a acabar el lote. La exportación se puede repetir a medida que se terminan jobs.
- **Protección del trabajo humano:** la pre-anotación (que sustituye todas las cajas de la tarea) se niega a ejecutarse si la tarea ya tiene cajas manuales o semiautomáticas.
- La lógica de CVAT (crear lote, pre-anotar, estado y exportar) está en `src/cvat_lotes.py`, compartida con `03b` y `03c`.

**Resultado:** `lote_01` con 300 imágenes (6 jobs de 50). El job 1 está en revisión y todavía no hay ningún job terminado.

## 03b_anotacion_lote_prioritario

**Objetivo:** crear un **único job con las imágenes que más equilibran las clases**, ordenadas por prioridad, para que la revisión humana compense los desequilibrios de las pre-anotaciones.

**Decisiones:**
- **Grupos a nivelar:** `pedestrian`, `car`, `bus`, `truck`, `motorcycle`, `semaforo` (cualquier color, porque el color pre-anotado no es fiable), `semaforo_rojo` y `semaforo_verde` (indicios HSV), `semaforo_peatonal` y `poca_luz` (noche o crepúsculo). **El ámbar no se prioriza**, porque está sobrerrepresentado y casi siempre mal clasificado.
- **Selección voraz** (`src/priorizacion.py`): cada imagen se puntúa con Σ peso_grupo · min(n, 3), donde peso = 1 / (1 + instancias ya acumuladas, contando lo anotado en CVAT). Cada imagen elegida reduce el peso de los grupos que cubre. El tope de 3 evita que gane una imagen solo por tener muchos coches. Máximo 5 imágenes por cámara.
- **Un solo job ordenado** (`sorting_method = predefined`): aunque no se termine, lo anotado primero es lo que más equilibra.

**Resultado:** en los candidatos, los coches son 6 veces más frecuentes que los peatones, 70 veces más que las motos, 410 más que los semáforos peatonales y miles de veces más que los semáforos rojos o verdes. La revisión del job 1 confirma el sesgo de color: las correcciones manuales tienen 11 verdes, 5 rojos y ningún ámbar. `lote_02_prioritario` (100 imágenes) sube los semáforos peatonales de 1 a 58 y las imágenes con poca luz de 0 a 61.

## 03c_anotacion_zonas_estado_vehiculos

**Objetivo:** reunir la anotación manual que necesita `06`: las zonas por cámara y un lote de validación con el estado de cada coche.

**Decisiones:**
- **Zonas por cámara.** Para cada cámara de referencia se dibujan una vez en CVAT polígonos de `zona_espera` (carril de espera hasta la línea de detención), `zona_aparcamiento` (plazas visibles) y `paso_peatones` (paso de cebra). Se exportan a `zonas/zonas_camaras.json`, versionado en git.
- **Atributo `estado` en `car` en CVAT** (`desconocido` por defecto, `esperando`, `aparcado`, `circulando`). Es la referencia manual para medir cuánto aciertan las reglas de `06`. Se añadió a la etiqueta existente, conservando las anotaciones, y está descrito en el protocolo de anotación de `03a`.
- **Lote de validación** (`lote_03_estado_vehiculos`): 10 imágenes por cámara de referencia, repartidas a lo largo de las secuencias a 6 s. Es también un lote de entrenamiento más.
- **Separado de `06` (18/10/2026):** las celdas que crean tareas en CVAT y exportan trabajo humano pertenecen a la fase de anotación y se ejecutan una vez. El seguimiento y la clasificación son análisis que se repiten con cada captura nueva y no tocan CVAT. Las secuencias a 6 s las calculan ambos con `estado_vehiculos.continuous_sequences`.

**Resultado:** la tarea de zonas (tarea 3) está creada, pero todavía sin polígonos. El lote de validación no se ha creado.

## 04_entrenamiento_yolo26

**Objetivo:** entrenar YOLO26 con las etiquetas revisadas en CVAT.

**Decisiones:**
- Solo usa imágenes con `estado = revisada`. No se regeneran etiquetas con un detector, así que el mAP mide acierto frente a la realidad, no frente al modelo de partida.
- **Test con cámaras no vistas:** el 15 % de las cámaras se aparta antes de todo.
- **Validación cruzada por cámara (`GroupKFold`):** una cámara nunca está a la vez en entrenamiento y validación, para evitar fuga de información por escenario.
- Métricas globales y **por clase**, alineadas con `ap_class_index` (antes se desalineaban), con detalle de los semáforos por color.
- Modelo `yolo26s.pt` a 640 px con batch 8, ajustado a la GTX 1650 (4 GB).

**Resultado:** pendiente. Para ejecutarlo hace falta un lote revisado y exportado.

## 05_evaluacion_indicadores_trafico

**Objetivo:** calcular indicadores de tráfico por cámara, por franja horaria y por contexto (tipo de día, iluminación y clima).

**Decisiones:**
- Ocupación (**vehículos y peatones medios por imagen**) en lugar de "por minuto": con imágenes fijas no se puede medir un flujo sin seguir objetos entre fotogramas.
- **Fracción de tiempo** en cada estado del semáforo. Es estimable con muestras de fase aleatoria, aunque no se puedan medir duraciones.
- Las **duraciones de fase** solo se calculan si el refresco medido es ≤ 10 s, con los timestamps reales. Se descartan las rachas cortadas por huecos de más de 15 s y las censuradas al inicio o al final de la serie.
- Si una imagen tiene semáforos de colores distintos, se marca `mixto` y no se usa para los indicadores de estado.
- Los indicadores por franja y contexto se calculan por cámara y después se promedian entre cámaras (`by_camera_then_mean`), para que las 5 cámaras de referencia no dominen.

**Resultado:** 7,5 vehículos y 1,1 peatones por imagen de media en las 24 cámaras. Los indicadores de estado del semáforo no son válidos todavía: heredan el sesgo ámbar de `02c`.

## 06_clasificacion_estado_vehiculos

**Objetivo:** distinguir los vehículos que esperan al semáforo de los aparcados y los que circulan. La existencia de vehículos aparcados cerca de los semáforos altera el conteo de los vehículos que esperan, y en una sola imagen un coche aparcado y uno detenido en rojo son casi indistinguibles.

**Decisiones** (en `src/estado_vehiculos.py`, con parámetros en `config.yaml` → `estado_vehiculos`):
- **Descartado:** una clase `parked_car` para el detector, que le restaría precisión y no resolvería el problema.
- **Zonas por cámara** (de `03c`). Cada vehículo se asigna por el **punto inferior central de su caja**, donde la rueda toca el suelo, que es más estable frente a la perspectiva que el centro de la caja. Un vehículo detenido sobre el paso de peatones no cuenta como "esperando". Si un punto cae en varias zonas, gana el aparcamiento.
- **Persistencia temporal.** Con las capturas cada 6 s, las cajas se enlazan entre imágenes consecutivas por solape (IoU ≥ 0,3 para considerar que es el mismo vehículo; ≥ 0,7 para considerar que no se ha movido). Un vehículo **inmóvil más de 300 s** (unos 3 ciclos semafóricos, con sus verdes) está **aparcado**. Uno que espera se detiene en rojo y arranca en verde. Un hueco de más de 15 s entre imágenes corta el seguimiento.
- **Regla por caja:** *aparcado* si está en `zona_aparcamiento` o lleva inmóvil ≥ 300 s; *esperando* si está en `zona_espera`, detenido y no aparcado; *circulando* en el resto.
- Se guardan **las cajas**, no solo conteos, en `fases/vehiculos_cajas.parquet`, de forma incremental.

**Resultado:** 4.760 cajas de vehículos clasificadas, todas como `circulando`, porque aún no hay zonas dibujadas. La validación contra CVAT queda pendiente del lote de `03c`.
