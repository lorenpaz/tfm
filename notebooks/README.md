# Pipeline de Notbooks

A través de los notebooks alojados en la presente carpeta se implementa el pipeline completo del TFM.
El proceso discurre desde la descarga de imágenes hasta la evaluación de los indicadores de tráfico.
Se ha seguido un enfoque basado en la reutilización de código común (rutas, marcas de tiempo, calidad, detección, fases...).
        - Alojados en [`src/`](../src/README.md).
        - Parámetros de configuración en [`config.yaml`](../config.yaml).

Todos los notebooks se ejecutan desde la misma carpeta a través de la creación de un kernel denominado **Python (TFM)** (`env_tfm`, el `.venv` del proyecto).

## Orden de ejecución y flujo de datos

```
00_Descarga_Imagenes_Malaga ──► raw/ (instantánea de todas las cámaras)
00b_Frecuencia_Refresco ──────► refresco/ (cada cuánto publica cada cámara)
01_EDA_Catalogo_Camaras        (análisis del catálogo, sin salidas)
01_EDA_Calidad_Visual          (análisis de calidad, sin salidas)
        │
02_preprocess_labelled_basic ─────► fases/frames.parquet + fases/blacklist_camaras.csv
02_preprocess_labelled_weather ───► fases/weather.parquet      (necesita frames)
02_preprocess_labelled_detection ─► fases/detections.parquet   (necesita frames)
        │
03_anotacion_cvat ──► anotacion/<lote>/ (imágenes, índice y etiquetas revisadas en CVAT)
03b_lote_prioritario_cvat ──► anotacion/lote_02_prioritario/ (lote que compensa clases escasas)
04_training ────────► runs/ + resultados/metricas_*.csv        (necesita lotes revisados)
05_evaluation ──────► resultados/indicadores_*.csv             (necesita frames y detections)
06_estado_vehiculos ► zonas/zonas_camaras.json + fases/vehiculos_cajas.parquet + resultados/estado_vehiculos.csv
                      (necesita capturas a 6 s de las cámaras de referencia y las zonas dibujadas en CVAT)
```

`weather` y `detection` se pueden ejecutar en cualquier orden: cada fase escribe **solo su propio fichero**, y las fases se unen por `(camera, image)` con `pipeline.load_frames()`. Así ninguna fase puede sobrescribir el trabajo de otra.

## Convenciones comunes

- **Marcas de tiempo:** los nombres de fichero y la columna `timestamp` están en **UTC** (`20260825T144834Z.jpg`). `timestamp_local` (hora de Madrid) se usa solo para las franjas horarias y el tipo de día. Así se evitan las horas ambiguas o inexistentes de los cambios de hora.
- **Diferenciación de la iluminación y clima:** `illumination` (día / crepúsculo / noche) se calcula por **elevación solar** y es independiente del clima (`weather`).
- **Rutas:** las rutas de imagen guardadas en las fases son relativas a la raíz del proyecto.

---

## 00_Descarga_Imagenes_Malaga

**Objetivo:** descargar una imagen de **todas** las cámaras del catálogo (134) como instantánea. La captura continua de las cámaras seleccionadas la hace el servicio [`scripts/captura_camaras.py`](../scripts/README.md).

**Decisiones:**
- Cabeceras de navegador (`User-Agent`, `Referer`): sin ellas el servidor puede bloquear el acceso.
- `URLIMAGEN` se limpia en `catalogo.load_catalog()`: algunas URL traen un tabulador final.
- Reintentos con espera exponencial ante errores.

**Salida:** `raw/<cámara>/<UTC>.jpg` y `metadata/captura_imagenes.csv`.

## 00b_Frecuencia_Refresco

**Objetivo:** saber **cada cuánto publica cada cámara una imagen nueva**, porque de eso depende si se pueden medir las duraciones de las fases semafóricas (OE-4).

**Método:** consulta 5 cámaras de referencia cada segundo durante 10 minutos y compara la cabecera `Last-Modified` del servidor (instante exacto de publicación) y el hash de la imagen (respaldo).

**Resultado:** las 5 cámaras refrescan cada **6 s** de mediana (p10 = 3–4 s, p90 = 8 s), y la imagen tiene unos 3 s de antigüedad al descargarla. Ambos métodos coinciden, así que `Last-Modified` es fiable.

**Decisión derivada:** como un ciclo semafórico dura ~60–120 s, un refresco de 6 s **sí permite medir duraciones de fase**, pero solo si se captura con esa frecuencia. El resumen guardado lo usan `02_basic` (intervalo de muestreo) y `05_evaluation`.

## 01_EDA_Catalogo_Camaras

**Objetivo:** caracterizar el catálogo municipal: número de cámaras, nulos, duplicados y distribución geográfica.

**Decisión:** el CSV no trae columnas `lat`/`lon`. Se derivan de `SDOGEOMETRIA` (`POINT (lon lat)`, EPSG:4326) con `catalogo.load_catalog()`.

## 01_EDA_Calidad_Visual

**Objetivo:** explorar la calidad visual (resolución, brillo y nitidez) para fijar los criterios de `02_basic`. Analiza una muestra de hasta 200 imágenes por cámara.

**Decisiones:**
- El brillo se analiza **por iluminación**: una imagen nocturna oscura es normal y no indica una cámara defectuosa.
- La nitidez se representa en escala logarítmica por su gran dispersión.
- El `quality_score` combina los **percentiles** de brillo y nitidez, no sus valores brutos, cuyas escalas difieren en un orden de magnitud.

## 02_preprocess_labelled_basic

**Objetivo:** primera fase del preprocesamiento. Calcula la calidad y el contexto temporal de cada imagen, filtra las no válidas y muestrea.

**Decisiones:**
- Se recorren carpetas cuyo nombre es un ID de cámara.
- **Brillo mínimo solo de día.** El umbral de nitidez es un **percentil** de la distribución observada (`percentil_nitidez_min`), no un valor fijo.
- **Lista negra por fracción de fallos:** una cámara se descarta solo si falla más del 30 % de sus imágenes **de día**. La lista se recalcula en cada ejecución, de modo que una cámara que mejora vuelve a entrar.
- **Muestreo según el refresco medido:** como máximo un fotograma por cámara cada X segundos, siendo X el refresco de `00b` (6 s). No tiene sentido muestrear más rápido de lo que la cámara publica.
- Los festivos salen de `calendario_festivos_malaga.csv`.

**Resultado:** 42.714 fotogramas válidos de 133 cámaras, sin ninguna cámara en lista negra. La peor, la 21545, falla el 20 % de sus imágenes de día.

## 02_preprocess_labelled_weather

**Objetivo:** etiquetar el clima de cada fotograma con la observación AEMET de la estación más cercana a su cámara.

**Decisiones:**
- La clave se lee con `config.get_secret("AEMET_API_KEY")`, desde la variable de entorno o el `.env` de la raíz (excluido de git).
- El inventario de AEMET da las coordenadas en grados-minutos-segundos (`364000N`); se convierten a grados decimales con `meteo.dms_to_decimal`. Antes se perdían y no se asignaba ninguna estación.
- **Modo automático:** si los fotogramas son de las últimas 24 h se usan observaciones horarias; si no, datos climatológicos **diarios**, situados a mediodía UTC y con una ventana de cruce de ±12 h.
- **Consultas en tramos de 14 días**, porque AEMET limita cada consulta diaria a 15 días.
- **Solo estaciones con datos:** la estación más cercana se elige entre las que tienen observaciones en el periodo. La más cercana a muchas cámaras (MÁLAGA, PUERTO) no publica datos diarios y dejaba el 75 % de los fotogramas como `unknown`.
- Se descartan las estaciones a más de 40 km.
- Las reglas de clasificación están en `meteo.classify_weather`, con prioridad rain > fog > windy > cloudy > sunny.

**Resultado:** el 98,4 % de los fotogramas tiene clima asignado, todo `sunny`, por las estaciones de Aeropuerto, Centro Meteorológico y Rincón de la Victoria. El 1,6 % restante `unknown` corresponde a días que AEMET aún no había publicado. Con datos diarios, la etiqueta describe el día, no el momento exacto de la imagen.

## 02_preprocess_labelled_detection

**Objetivo:** detectar con **YOLO26** preentrenado (COCO) los objetos de cada fotograma y guardar **conteos**: `n_pedestrian`, `n_car`, ..., `n_vehiculos`, semáforos por color. La clase de personas se llama `pedestrian` en todo el proyecto, aunque en COCO se llama `person`.

**Decisiones:**
- Se guardan **conteos**, no presencia 0/1, para calcular densidades reales en `05`.
- El color del semáforo se clasifica **por caja** (HSV). Los semáforos peatonales se separan con una heurística de tamaño y posición.
- Estas detecciones alimentan los indicadores de `05`, **no el entrenamiento**: las cajas para entrenar se revisan por humanos en CVAT (`03`), para evitar el entrenamiento circular.

**Resultado:** 42.686 fotogramas procesados, con una media de 7,4 vehículos y 1,0 personas por imagen.

**Limitación detectada:** la clasificación HSV del color está muy sesgada. Se presupone que confunde el estado ámbar con las carcasas, los reflejos y el alumbrado, así que se lleva a la decisión de **reforzar el etiquetado humano** de los semáforos para mejorar la **fiabilidad**. La solución prevista es el detector entrenado con etiquetas revisadas en CVAT, que aprende el color como clase.

## 03_anotacion_cvat

**Objetivo:** crear lotes de imágenes para anotar en CVAT, pre-anotados con YOLO26 y **revisados por un humano**, para obtener etiquetas de entrenamiento y test fiables.

**Decisiones:**
- **Muestreo estratificado en *round-robin*** entre cámara × franja horaria × tipo de día × iluminación, con un máximo por cámara (`pipeline.stratified_selection`), para que el lote no se concentre en las cámaras u horas con más capturas.
- Las imágenes se copian con un nombre único, `<cámara>_<timestamp>.jpg`, porque los timestamps se repiten entre cámaras. Un lote nuevo excluye las imágenes de lotes anteriores.
- La pre-anotación usa `cvat_sdk.auto_annotation` con la función de [`src/cvat_yolo26.py`](../src/README.md). Los semáforos peatonales los distingue el anotador.
- Un **protocolo de anotación** (tabla en el notebook) fija los criterios comunes: oclusión, color desconocido, peatonales...
- La exportación reasigna las clases **por nombre** (`anotacion.remap_lines`), porque el orden de etiquetas en CVAT puede diferir de `CLASS_NAMES`.
- **Exportación por jobs terminados:** solo las imágenes de jobs marcados como terminados pasan a `revisada`. Así se puede entrenar con lo ya revisado sin esperar a acabar el lote. La exportación se puede repetir a medida que se terminan jobs.
- **Protección del trabajo humano:** la pre-anotación (que sustituye todas las cajas de la tarea) se niega a ejecutarse si la tarea ya tiene cajas manuales o semiautomáticas.
- La lógica de CVAT (crear lote, pre-anotar, estado y exportar) está en `src/cvat_lotes.py`, compartida con `03b`.

## 03b_lote_prioritario_cvat

**Objetivo:** crear un **único job con las imágenes que más equilibran las clases**, ordenadas por prioridad, para que la revisión humana compense los desequilibrios de las pre-anotaciones.

**Diagnóstico de partida:** en los candidatos, los coches son 6 veces más frecuentes que los peatones, 70 veces más que las motos, 410 más que los semáforos peatonales y miles de veces más que los semáforos rojos o verdes. Además, la revisión del job 1 confirma el sesgo de color: las correcciones manuales tienen 11 verdes, 5 rojos y ningún ámbar.

**Decisiones:**
- **Grupos a nivelar:** `pedestrian`, `car`, `bus`, `truck`, `motorcycle`, `semaforo` (cualquier color, porque el color pre-anotado no es fiable), `semaforo_rojo` y `semaforo_verde` (indicios HSV), `semaforo_peatonal` y `poca_luz` (noche o crepúsculo). **El ámbar no se prioriza**, porque está sobrerrepresentado y casi siempre mal clasificado.
- **Selección voraz** (`src/priorizacion.py`): cada imagen se puntúa con Σ peso_grupo · min(n, 3), donde peso = 1 / (1 + instancias ya acumuladas, contando lo anotado en CVAT). Cada imagen elegida reduce el peso de los grupos que cubre. El tope de 3 evita que gane una imagen solo por tener muchos coches. Máximo 5 imágenes por cámara.
- **Un solo job ordenado** (`sorting_method = predefined`): aunque no se termine, lo anotado primero es lo que más equilibra.

## 04_training

**Objetivo:** entrenar YOLO26 con las etiquetas revisadas en CVAT.

**Decisiones:**
- Solo usa imágenes con `estado = revisada`. No se regeneran etiquetas con un detector, así que el mAP mide acierto frente a la realidad, no frente al modelo de partida.
- **Test con cámaras no vistas:** el 15 % de las cámaras se aparta antes de todo.
- **Validación cruzada por cámara (`GroupKFold`):** una cámara nunca está a la vez en entrenamiento y validación, para evitar fuga de información por escenario.
- Métricas globales y **por clase**, alineadas con `ap_class_index` (antes se desalineaban), con detalle de los semáforos por color.
- Modelo `yolo26s.pt` a 640 px con batch 8, ajustado a la GTX 1650 (4 GB).

**Nota:** es necesario que haya un lote revisado y exportado para su ejecución.

## 05_evaluation

**Objetivo:** calcular indicadores de tráfico por cámara, por franja horaria y por contexto (tipo de día, iluminación y clima).

**Decisiones:**
- Ocupación (**vehículos y peatones medios por imagen**) en lugar de "por minuto": con imágenes fijas no se puede medir un flujo sin seguir objetos entre fotogramas.
- **Fracción de tiempo** en cada estado del semáforo. Es estimable con muestras de fase aleatoria, aunque no se puedan medir duraciones.
- Las **duraciones de fase** solo se calculan si el refresco medido es ≤ 10 s, con los timestamps reales. Se descartan las rachas cortadas por huecos de más de 15 s y las censuradas al inicio o al final de la serie.
- Si una imagen tiene semáforos de colores distintos, se marca `mixto` y no se usa para los indicadores de estado.

## 06_estado_vehiculos

**Problema:** la existencia de vehículos aparcados en las inmediaciones de semáforos podría alterar el conteo de los tiempos esperando a los semáforos. En una sola imagen, un coche aparcado y uno detenido en rojo son casi indistinguibles.

** Criterios descartados**
-  La creación de **una clase `parked_car`** para el detector le restaría precisión y no resolvería el problema.
  
**Criterios adoptados** (en `src/estado_vehiculos.py`, con parámetros en `config.yaml` → `estado_vehiculos`):

1. **Zonas por cámara.** Para cada cámara de referencia se dibujan una vez en CVAT polígonos de `zona_espera` (carril de espera hasta la línea de detención), `zona_aparcamiento` (plazas visibles) y `paso_peatones` (paso de cebra).
    - Un vehículo detenido sobre el paso no cuenta como "esperando". Cada vehículo se asigna por el **punto inferior central de su caja**, donde la rueda toca el suelo, que es más estable frente a la perspectiva que el centro de la caja. Si un punto cae en ambas zonas, gana el aparcamiento.
3. **Persistencia temporal.** Con las capturas cada 6 s, las cajas se enlazan entre imágenes consecutivas por solape (IoU ≥ 0,3 para considerar que es el mismo vehículo; ≥ 0,7 para considerar que no se ha movido). Un vehículo **inmóvil más de 300 s** (unos 3 ciclos semafóricos, con sus verdes) está **aparcado**. Uno que espera se detiene en rojo y arranca en verde. Un hueco de más de 15 s entre imágenes corta el seguimiento.
4. **Atributo `estado` en `car` en CVAT** (`desconocido` por defecto, `esperando`, `aparcado`, `circulando`). Es la referencia manual para medir cuánto aciertan las reglas. Se añadió a la etiqueta existente, conservando las anotaciones, y está descrito en el protocolo de anotación de `03`.

**Regla por caja:** *aparcado* si está en `zona_aparcamiento` o lleva inmóvil ≥ 300 s; *esperando* si está en `zona_espera`, detenido y no aparcado; *circulando* en el resto.

**Flujo del notebook:**
1. Crea la tarea de zonas en CVAT (una imagen diurna nítida por cámara de referencia) y exporta los polígonos.
2. Busca **tramos continuos** de imágenes a ≤ 15 s en `raw/` y `refresco/`.
3. Ejecuta YOLO26 y guarda **las cajas**, no solo conteos, en `fases/vehiculos_cajas.parquet`. Es incremental.
4. Sigue, clasifica y resume los vehículos por estado y cámara.
5. Valida contra los coches con `estado` marcado en CVAT. Si hace falta, crea un lote de validación (`lote_03_estado_vehiculos`) con imágenes de las secuencias a 6 s.
