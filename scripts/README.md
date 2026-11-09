# Scripts

En la presente carpeta se alojan programas que se ejecutan fuera de los notebooks:
- El servicio de captura continua, especializado en la captura instantánea de imágenes.
- El servicio de medición de refresco, de un solo uso o de diagnóstico, de la situación de un conjutno de cámaras de referencia.
- El script de depuración de `raw/`, que conserva la rejilla de entrenamiento y borra lo redundante (en modo simulación por defecto).

Todos leen la configuración de [`config.yaml`](../config.yaml) y reutilizan los módulos de [`src/`](../src/README.md). Se ejecutan con el Python del `.venv` desde la raíz del proyecto.

| Script | Tipo | Uso |
|---|---|---|
| `captura_camaras.py` | Servicio permanente | `CamarasMalaga` (NSSM), ejecución automática; tras cambios, `Restart-Service CamarasMalaga` (administrador) |
| `medir_refresco.py` | Diagnóstico | `python scripts/medir_refresco.py [--camaras ...] [--duracion 10] [--poll 1] [--guardar-imagenes]` |
| `depurar_raw.py` | Mantenimiento | `python scripts/depurar_raw.py` (simulación) · `python scripts/depurar_raw.py --aplicar` (borra) |

---

## captura_camaras.py

**Objetivo:** captura de forma continua las **24 cámaras** seleccionadas (`config.yaml` → `captura.camaras`) y guarda cada imagen en `data/malaga/raw/<cámara>/<UTC>.jpg`. Cada intento de captura añade una fila a `data/malaga/metadata/capturas_<fecha UTC>.csv`.

| Cámaras | Hora punta (07–10, 13–16, 17–20 h) | Resto del día |
|---|---|---|
| 5 de referencia (`captura.alta_frecuencia`) | **cada 6 s** | cada 60 s |
| Las otras 19 | cada 30 s | cada 60 s |

Volumen estimado: **~3 GB/día** (imágenes de ~63 KB).

**Ejecución:** como servicio de Windows **`CamarasMalaga`**, gestionado con NSSM: arranca con el sistema y se reinicia solo si falla.
- Ejecutable: `.venv\Scripts\python.exe`
- Argumento: `scripts\captura_camaras.py`
- Directorio de trabajo: `scripts\`
- Salida estándar y errores: `data\malaga\logs\stdout.log` y `stderr.log`. El log propio va a `capturas.log`.

Para cambiar la ruta o el intérprete del servicio hacen falta permisos de administrador: `nssm set CamarasMalaga <parámetro> <valor>` y después `nssm restart CamarasMalaga`. Si se recrea el `.venv`, el servicio falla al arrancar hasta que vuelvan a estar instaladas las dependencias.

**Decisiones:**
- **5 cámaras de referencia cada 6 s en hora punta.** Es la frecuencia de refresco medida (ver `medir_refresco.py`) y permite medir duraciones de fase semafórica (OE-4), porque un ciclo de 60–120 s queda muestreado con 10–20 imágenes. Se limita a esas cámaras y a la hora punta porque capturar las 24 cámaras cada 6 s todo el día supondría ~21 GB/día y llenaría el disco en día y medio.
- **Planificación por cámara, sin bloqueos.** Cada cámara tiene su propio intervalo y su descarga se lanza en paralelo, en un hilo propio (12 hilos). Algunas descargas tardan varios segundos, o agotan los 15 s de espera; esas solo retrasan a su cámara. En una versión con tandas sincronizadas, las cámaras de 6 s llegaban a esperar 15 s.
- La siguiente captura se programa **desde el inicio** de la actual, para mantener la cadencia. Nunca se solapan dos descargas de la misma cámara.
- **Descarte de duplicados.** Si el `Last-Modified` del servidor no ha cambiado desde la captura anterior, la cámara aún no ha publicado imagen nueva: no se guarda y se registra con `status = SIN_CAMBIOS` (`captura.descartar_sin_cambios`).
- **Nombres y metadatos en UTC** (`20261017T081230Z.jpg`) para evitar horas duplicadas o inexistentes en los cambios de hora. La hora de Madrid solo se usa para decidir si es hora punta.
- Guarda la cabecera **`Last-Modified`** (`server_last_modified`): es el instante real de publicación de la imagen.
- **Log compacto.** Los errores se registran siempre; las capturas, en una línea de resumen por minuto ("Último minuto: N capturas, M sin cambios, K errores"), porque a 6 s una línea por captura generaría ~30.000 líneas al día.
- Reintentos con espera exponencial ante errores 429/5xx y cabeceras de navegador, porque sin ellas el servidor responde 403. Hay una sesión HTTP por hilo.
- Las rutas se resuelven desde `config.yaml`, no de forma absoluta, para que el proyecto funcione en cualquier ubicación.

Las imágenes se escriben en `data/malaga/raw/`, que es un *junction* a `C:\Users\loren\tfm-datos\raw`, fuera de OneDrive (ver [`data/malaga/README.md`](../data/malaga/README.md)). El servicio no necesita ningún cambio para usarlo.

Los cambios de `config.yaml` → `captura` y de este script solo se aplican tras reiniciar el servicio (`Restart-Service CamarasMalaga` en una consola de administrador).

## medir_refresco.py

**Objetivo:** mide **cada cuánto publica cada cámara una imagen nueva**. Consulta varias cámaras en paralelo cada `--poll` segundos durante `--duracion` minutos y registra en cada consulta la cabecera `Last-Modified` y el SHA-1 de la imagen. También se usa desde `00b_medicion_refresco_camaras.ipynb`, que importa sus funciones.

**Salidas** (en `data/malaga/refresco/`):
- `refresco_<UTC>.csv`: una fila por consulta.
- `refresco_<UTC>_resumen.csv`: intervalos entre imágenes nuevas por cámara.
- Con `--guardar-imagenes`, las imágenes nuevas en `refresco_<UTC>/<cámara>/`.

**Decisiones:**
- **Dos métodos independientes.** `Last-Modified` da el instante exacto de publicación. El hash detecta cambios de contenido, con una precisión limitada al intervalo de consulta. Si coinciden, la cabecera es fiable.
- Se usan peticiones **GET**: en este servidor, HEAD no devuelve `Last-Modified`.
- Por defecto mide las 5 cámaras de referencia de `config.yaml` → `refresco.camaras_referencia`.

**Resultado:** refresco mediano de **6 s** en las 5 cámaras (p10 = 3–4 s, p90 = 8 s), con unos 3 s de antigüedad de la imagen al descargarla. Ambos métodos coinciden.
## depurar_raw.py

**Objetivo:** liberar espacio en `data/malaga/raw/` sin perder lo que sirve. Conserva la **rejilla de entrenamiento** y lo que aún hace falta, y propone borrar el resto.

**Por qué:** los lotes de anotación exigen al menos 10 minutos entre dos imágenes de la misma cámara (`cvat.separacion_minima_min`). Por eso, de cada cámara solo puede llegar a entrenamiento una imagen cada 10 minutos (144 al día). Una cámara normal guarda unas 2.000 al día y una de referencia hasta 6.300. Con 24 cámaras la captura ocupa ~2,6 GB/día (medido el 17/10/2026).

**Rejilla:** el día se divide en franjas fijas de `retencion.franja_min` minutos (10). De cada cámara y franja se conserva la imagen de mayor `quality_score` entre los fotogramas válidos (fase `frames` de `02a`) que `02c` pudo leer. Si la franja no tiene ninguno, se conserva su primera imagen, para no perder la estadística de fallos de la cámara. Son unas 3.500 imágenes al día, unos 280 MB.

**Decisión por imagen** (`src/retencion.py`, la primera regla que se cumple):

| Orden | Motivo | Acción | Condición |
|---|---|---|---|
| 1 | `en_lote` | conservar | Está en un lote de anotación (`anotacion/*/indice.csv`). Sin excepciones: es trabajo humano. |
| 2 | `reciente` | conservar | Tiene menos de `retencion.dias_gracia` días (7). |
| 3 | `pendiente_02` | conservar | Es posterior a la última ejecución de `02` (último `timestamp` de `frames.parquet`). |
| 4 | `pendiente_06` | conservar | Pertenece a una secuencia a 6 s de las cámaras de referencia que `06` aún no ha procesado. |
| 5 | `ilegible` | borrar | `02a` la registró, pero `02c` no la pudo leer. |
| 6 | `rejilla` | conservar | Es la representante de su franja de 10 minutos. |
| 7 | `ventana` | conservar | Su día local está en una ventana de evaluación (`retencion.ventanas_evaluacion`). |
| 8 | `redundante` | borrar | El resto. |

**Ventanas de evaluación:** son periodos `[inicio, fin]` (fechas locales, ambas incluidas) que se conservan completos para los indicadores de `05` y las secuencias de `06`. La configuración inicial declara una sola ventana, del 25/08 al 26/10/2026, que **protege todo lo capturado hasta ahora**: los indicadores de semáforo actuales salen de la clasificación HSV, que no es fiable, y hay que recalcularlos con el detector entrenado en `04` sobre esas mismas imágenes. Cuando se hayan recalculado, se puede acortar o retirar la ventana. Las ventanas nuevas se añaden a la lista, por ejemplo `["2026-10-31", "2026-11-03"]` para cubrir el fin de semana y el festivo del 2/11.

**Salidas** (en `data/malaga/logs/`, fuera de git):
- `depuracion_<UTC>_simulacion.csv`: el plan, con las imágenes que se borrarían y el motivo.
- `depuracion_<UTC>_aplicado.csv`: el registro de lo borrado, solo con `--aplicar`.

**Decisiones:**
- **Simulación por defecto.** Borrar exige `--aplicar`. La simulación indica también cuánto ocupan las imágenes protegidas solo por las ventanas, para decidir cuándo cerrarlas.
- **La captura no cambia.** El servicio sigue capturando al ritmo normal y la selección se hace después. Así una imagen borrosa no deja la franja sin representante, y las ventanas de evaluación no exigen reconfigurar ni reiniciar el servicio.
- Solo se tocan las imágenes de `raw/`. Las mediciones de `refresco/` y las copias de `anotacion/*/images/` no se depuran.
- Las fases (`frames`, `detections`, `vehiculos_cajas`) no se modifican. Si se vuelve a ejecutar `02` después de una depuración, solo verá las imágenes conservadas.

**Resultado de la primera simulación (26/10/2026):**

| Acción | Motivo | Imágenes | Espacio |
|---|---|---|---|
| conservar | `ventana` | 67.670 | 4,14 GB |
| conservar | `reciente` | 50.866 | 2,76 GB |
| conservar | `pendiente_02` | 31.517 | 1,77 GB |
| conservar | `pendiente_06` | 5.642 | 0,36 GB |
| conservar | `rejilla` | 5.452 | 0,33 GB |
| conservar | `en_lote` | 400 | 0,02 GB |
| borrar | `ilegible` | 51 | 0,00 GB |
| **Total** | | **161.598** | **9,38 GB** |

Con la ventana inicial solo se liberarían las 51 imágenes ilegibles. Cerrando esa ventana se liberarían 4,14 GB, el 44 % de `raw/`. Además, 1,77 GB están retenidos solo porque `02` no se ejecuta desde el 17/10, y otros 0,36 GB porque `06` tampoco: al volver a ejecutar ambas fases, esas imágenes también pasan a ser depurables.

**Primera depuración real (09/11/2026),** tras cerrar la ventana inicial (`ventanas_evaluacion: []`). Se borraron 67.721 imágenes (4,14 GB): 67.670 redundantes y 51 ilegibles, todas del 25/08 al 17/10 y ninguna de un lote. El registro está en `logs/depuracion_20261109T113524Z_aplicado.csv`.

| Acción | Motivo | Imágenes | Espacio |
|---|---|---|---|
| conservar | `pendiente_02` | 219.955 | 12,39 GB |
| conservar | `reciente` | 91.988 | 5,62 GB |
| conservar | `pendiente_06` | 5.642 | 0,36 GB |
| conservar | `rejilla` | 5.452 | 0,33 GB |
| conservar | `en_lote` | 400 | 0,02 GB |
| borrar | `redundante` + `ilegible` | 67.721 | 4,14 GB |
| **Total antes de borrar** | | **391.158** | **22,86 GB** |

Ahora el grueso de `raw/` (12,4 GB) está retenido porque `02` no se ejecuta desde el 17/10. Volver a ejecutar `02a` y `02c` es lo que más espacio liberaría en la siguiente depuración. Antes conviene declarar la próxima ventana de evaluación, para que sus días se conserven completos.

**Pendiente:**
- **Salvaguarda de disco en el servicio:** si el espacio libre baja de un umbral, guardar solo la rejilla y avisar en el log.
- **Modo evento:** declarar automáticamente una ventana de evaluación en los días con lluvia prevista por AEMET.
- **Ejecución programada**, por ejemplo una tarea diaria de Windows con `--aplicar`, cuando la regla de ventanas esté decidida.
