# Scripts

En la presente carpeta se alojan programas que se ejecutan fuera de los notebooks:
- El servicio de captura continua, especializado en la captura instantánea de imágenes.
- El servicio de medición de refresco, de un solo uso o de diagnóstico, de la situación de un conjutno de cámaras de referencia.

Todos leen la configuración de [`config.yaml`](../config.yaml) y reutilizan los módulos de [`src/`](../src/README.md). Se ejecutan con el Python del `.venv` desde la raíz del proyecto.

| Script | Tipo | Uso |
|---|---|---|
| `captura_camaras.py` | Servicio permanente | `CamarasMalaga` (NSSM), ejecución automática; tras cambios, `Restart-Service CamarasMalaga` (administrador) |
| `medir_refresco.py` | Diagnóstico | `python scripts/medir_refresco.py [--camaras ...] [--duracion 10] [--poll 1] [--guardar-imagenes]` |

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