# CVAT (servidor de anotación local)

[CVAT](https://github.com/cvat-ai/cvat) es la herramienta con la que se **revisan y corrigen a mano** las cajas pre-anotadas por YOLO26 antes de entrenar. Es lo que evita el entrenamiento circular: entrenar con etiquetas generadas por el propio detector. Se ejecuta en local con Docker y se usa desde [`notebooks/03_anotacion_cvat.ipynb`](../notebooks/README.md#03_anotacion_cvat).

## Acceso y versionado
- **Interfaz web:** http://localhost:8080
- **Usuario:** `admin`, con la contraseña de `cvat/.env`.
- **Versión:** CVAT **v2.78.0**, igual que `cvat-sdk==2.78.0` en `requirements.txt`.

## Contenido de la carpeta

| Fichero / carpeta | Versionado | Contenido |
|---|---|---|
| `cvat.ps1` | Sí | Script de gestión del servidor (ver abajo). |
| `cvat-server/` | No | Repositorio oficial de CVAT, clonado en la etiqueta `v2.78.0`. Contiene el `docker-compose.yml` que levanta los contenedores. Lo crea `cvat.ps1 instalar`. |
| `.env` | No | Credenciales generadas al instalar: `CVAT_URL`, `CVAT_USER`, `CVAT_EMAIL` y `CVAT_PASSWORD` (aleatoria, 20 caracteres). La lee `03_anotacion_cvat`. |

## Ejecutable Windows PowerShell

**`cvat.ps1`** se ejecuta desde la raíz del proyecto, con Docker Desktop abierto:

| Comando | Qué hace |
|---|---|
| `.\cvat\cvat.ps1 instalar` | Clona CVAT v2.78.0 en `cvat-server/` (si no existe), arranca los contenedores, espera a que responda la API y crea el superusuario. Solo la primera vez. |
| `.\cvat\cvat.ps1 arrancar` | `docker compose up -d` y espera a la API. |
| `.\cvat\cvat.ps1 parar` | `docker compose stop`: detiene los contenedores **conservando** proyectos, tareas y anotaciones. |
| `.\cvat\cvat.ps1 estado` | Estado de los contenedores y de la API. |
| `.\cvat\cvat.ps1 superusuario` | Crea el usuario `admin` con la contraseña de `.env`, y genera el `.env` si no existe. |
| `.\cvat\cvat.ps1 logs` | Últimas 100 líneas del log de `cvat_server`. |

**Decisiones del script:**
- **Versión fijada** (`$CvatVersion = "v2.78.0"`) mediante `CVAT_VERSION`, para usar las imágenes publicadas de esa versión de forma explícita.
- **Espera de hasta 15 minutos** a la API. El primer arranque aplica las migraciones de la base de datos y tarda más de 5 minutos; con la espera anterior, la instalación daba error aunque CVAT terminaba arrancando bien.
- **Credenciales fuera del código.** La contraseña se genera al azar, se guarda en `.env` (excluido de git) y se pasa al contenedor como variable de entorno.
- Los comandos externos (`git`, `docker`) se ejecutan con una función que comprueba su código de salida.
- El fichero está guardado en **UTF-8 con BOM**.
- 
## Contenerización

`docker compose` levanta unos 17 contenedores: el servidor (`cvat_server`), la interfaz (`cvat_ui`), la base de datos PostgreSQL (`cvat_db`), Redis, los *workers* de importación, exportación y anotación, `traefik` como proxy en el puerto 8080, y otros.

- CVAT solo está disponible mientras Docker Desktop esté en marcha. La política `restart: always` está activada, permitiendo **arrancar solo al abrir Docker Desktop**. .
- Los datos se guardan en **volúmenes de Docker** (`cvat_cvat_db`, `cvat_cvat_data`, ...). Sobreviven a `parar` y a reinicios. Para una limpieza completa: **`docker compose down -v`**, incluyendo **todas las anotaciones**.

## Uso en el TFM

1. `03_anotacion_cvat` crea el proyecto **"TFM Malaga - semaforos, peatones y vehiculos"**, con las 11 etiquetas de `src/deteccion.py`, y una tarea por lote dividida en jobs de 50 imágenes.
2. La pre-anotación YOLO26 sube las cajas a la tarea con `source = auto`.
3. **Revisión humana** en la web: corregir cajas y colores, cambiar los semáforos peatonales a `pedestrian_light_*` y marcar cada job como terminado (*Menu → Finish the job*). Los criterios están en la sección 6 del notebook.
4. El notebook exporta en formato *Ultralytics YOLO Detection 1.0* **los jobs terminados**; sus imágenes ya sirven para `04_training`. Se puede exportar varias veces, a medida que se terminan jobs.

`03b_lote_prioritario_cvat` crea además lotes de **un único job ordenado por prioridad**, con las imágenes que más compensan las clases escasas.

**Nota:** la pre-anotación sustituye todas las cajas de una tarea, así que el código protege la tarea si ya tiene cajas revisadas a mano.

| Tarea | Lote | Imágenes | Jobs | Estado |
|---|---|---|---|---|
| 1 | `lote_01` (estratificado) | 300 | 6 de 50 | Job 1 en revisión (104 cajas humanas); resto pendiente |
| 2 | `lote_02_prioritario` | 100 | 1 (job 7), ordenado por prioridad | Pre-anotado, pendiente de revisión |

## Notas

- En el primer uso de Docker Desktop hay que aceptar su acuerdo de licencia, así como su primer arranque tarda unos minutos más. Consultar en `.\cvat\cvat.ps1 estado` o `logs`.
- **Recordatorio:** el servidor y `cvat-sdk` deben tener la misma versión.
