# Cámaras del estudio, captura y condiciones del conjunto de entrenamiento

Situación a 26/10/2026. Este documento recoge la selección de cámaras, la propuesta de captura y las condiciones que deben cumplir la captura y el guardado de las imágenes para obtener un conjunto de entrenamiento de calidad. El análisis cámara a cámara está en [`analisis_camaras_trafico_malaga.md`](analisis_camaras_trafico_malaga.md); el servicio de captura y la depuración, en [`scripts/README.md`](../../scripts/README.md).

## 1. Cámaras del estudio y selección realizada

**Catálogo de partida.** El Ayuntamiento de Málaga publica 134 cámaras de tráfico en sus datos abiertos. Ninguna tiene coordenadas que falten ni identificadores duplicados, y todas tienen URL de imagen. El servidor no ofrece vídeo: publica una imagen fija que se renueva cada 6 s de mediana (medido el 12/10/2026; p10 = 3–4 s, p90 = 8 s). Las imágenes son casi todas de 640×480 px.

**Análisis manual por distrito.** Cada cámara se revisó una a una: semáforos visibles, visibilidad y si es una intersección.

| Distrito | Cámaras | Con semáforo visible | Seleccionadas |
|---|---|---|---|
| 1 Centro | 36 | 31 | 10 |
| 2 Málaga Este | 11 | 7 | 1 |
| 3 Ciudad Jardín | 6 | 6 | 2 |
| 4 Bailén-Miraflores | 10 | 9 | 1 |
| 5 Palma-Palmilla | 4 | 3 | 1 |
| 6 Carretera de Cádiz | 25 | 23 | 3 |
| 7 Cruz de Humilladero | 21 | 19 | 3 |
| 8 Churriana | 4 | 2 | 0 |
| 9 Campanillas | 4 | 2 | 0 |
| 10 Puerto de la Torre | 6 | 6 | 2 |
| 11 Teatinos-Universidad | 7 | 5 | 1 |
| **Total** | **134** | **113** | **24** |

**Selección: 24 cámaras para la captura continua** (`config.yaml` → `captura.camaras`).

- Todas tienen al menos un semáforo visible. La media es de 3,9 por cámara, y dos llegan a 6: 21547 (Manuel Alcántara) y 21598 (Avenida de la Aurora).
- Cubren 9 de los 11 distritos. Churriana y Campanillas quedan fuera: tienen pocas cámaras y solo 2 con semáforo visible en cada distrito.
- Predominan las intersecciones y los ejes con varios semáforos visibles. Cinco cámaras tienen semáforos con poca visibilidad anotada, que se compensa con el resto de semáforos del encuadre.
- La calidad es buena: ninguna cámara entra en la lista negra. La que más falla es la 21545, con un 8,3 % de imágenes diurnas no válidas, frente al límite del 30 %.

| Cámara | Nombre | Distrito | Semáforos visibles | Observaciones |
|---|---|---|---|---|
| 21560 | TV36-HILERA | 1 Centro | 3 | 1 con poca visibilidad · **referencia (6 s)** |
| 75098 | TV94-PLAZA DE LA MARINA - MOLINA LARIO | 1 Centro | 2 | |
| 21564 | TV40-PTE. ARMIÑÁN | 1 Centro | 4 | |
| 78681 | TV136-GALVEZ GINACHERO | 1 Centro | 1 | Bifuncional |
| 21603 | TV79-PABLO PINEDA | 1 Centro | 4 | |
| 21545 | TV06-PSO PARQUE | 1 Centro | 4 | 2 con poca visibilidad · **referencia (6 s)** |
| 21556 | TV17-LA CORACHA | 1 Centro | 5 | |
| 75095 | TV129-GLORIETA ALBERT CAMUS | 1 Centro | 4 | 2 con poca visibilidad |
| 21563 | TV39-MÁRMOLES | 1 Centro | 4 | 1 adicional de bicicleta · **referencia (6 s)** |
| 21547 | TV08-MANUEL ALCANTARA | 1 Centro | 6 | **referencia (6 s)** |
| 21541 | TV02-CTRA ALMERÍA | 2 Málaga Este | 4 | Intersección · **referencia (6 s)** |
| 21616 | TV25-RAMÓN Y CAJAL | 3 Ciudad Jardín | 5 | 2 con poca visibilidad |
| 21568 | TV44-THUILLER | 3 Ciudad Jardín | 4 | |
| 21577 | TV53-C.HAYA - V. INCLÁN | 4 Bailén-Miraflores | 3 | Intersección, avenida amplia |
| 21595 | TV71-VALLE INCLAN | 5 Palma-Palmilla | 4 | |
| 21582 | TV58-ORTEGA GASSET - A7 | 6 Carretera de Cádiz | 3 | |
| 21598 | TV74-AVDA. DE LA AURORA | 6 Carretera de Cádiz | 6 | Intersección entre avenidas |
| 21573 | TV49-PZA BERGAMIN | 6 Carretera de Cádiz | 4 | |
| 21554 | TV15-ANTONIO MACHADO | 7 Cruz de Humilladero | 4 | Fácil visibilidad |
| 75024 | TV92-AVDA SOR TERESA PRAT - FRIGILIANA | 7 Cruz de Humilladero | 2 | Fácil visibilidad |
| 21618 | TV27-GUINDOS | 7 Cruz de Humilladero | 4 | Fácil visibilidad |
| 21580 | TV56-PTO TORRE-OROZCO | 10 Puerto de la Torre | 4 | |
| 21587 | TV63-JUAN FRANCES BOSCA | 10 Puerto de la Torre | 4 | |
| 75093 | TV127-CARRIL DEL CAPITÁN - JUAN DE ROBLES | 11 Teatinos-Universidad | 5 | |

**Cinco cámaras de referencia** (21541, 21545, 21547, 21560 y 21563), cuatro en Centro y una en Málaga Este. En ellas se midió el refresco y son las que se capturan cada 6 s en hora punta, para medir duraciones de fase (OE-4) y seguir vehículos (OE-5).

**Observaciones sobre la selección:**

- **Concentración en Centro.** El 42 % de la selección (10 de 24) está en Centro, y también 4 de las 5 de referencia. Los lotes de anotación lo compensan con un máximo de imágenes por cámara, y los indicadores con el promedio por cámara. Aun así, conviene declararlo como sesgo geográfico en la memoria.
- **Dos usos de "referencia".** En el análisis manual, "Referencia" marca las cámaras de fácil visibilidad (21554, 75024 y 21618). No son las 5 de alta frecuencia. En este documento se llaman "de fácil visibilidad" para distinguirlas.
- Las 110 cámaras no seleccionadas solo tienen 1–2 instantáneas y se excluyen de la evaluación y de los lotes.

**Datos disponibles (a 26/10/2026):**

- 74.508 fotogramas válidos procesados, procedentes de solo 10 días; `raw/` ocupa 9,4 GB (161.598 imágenes).
- La captura ha tenido huecos: nada entre el 8/9 y el 12/10, días parciales entre el 18 y el 22/10, y nada el 23–24/10.
- Hay un único sábado completo y ningún festivo, y todos los días con dato de clima son soleados.

## 2. Propuesta de captura

**Por qué sobran imágenes.** Los lotes de anotación exigen al menos 10 minutos entre dos imágenes de la misma cámara (`cvat.separacion_minima_min`). Dos imágenes más próximas son casi idénticas: no aportan información y, repartidas entre entrenamiento y validación, inflarían las métricas. Por eso, de cada cámara solo puede llegar a un lote una imagen cada 10 minutos, es decir, 144 al día. Hoy una cámara normal guarda unas 2.000 al día y una de referencia hasta 6.300. Más del 90 % de lo guardado nunca podrá entrar en el conjunto de entrenamiento.

| Uso | Qué necesita | Captura y conservación |
|---|---|---|
| **Entrenamiento** (`03`, `04`) | Variedad: muchos días, horas, fines de semana, festivos, noche y lluvia. No volumen. | Rejilla permanente de 1 imagen por cámara cada 10 min en las 24 cámaras (~3.500 al día, ~280 MB). |
| **Indicadores de tráfico** (`05`) | Series densas en periodos representativos. | Ventanas de evaluación acotadas, a 30–60 s. Por ejemplo, 2 semanas seguidas con 2 fines de semana y el festivo del 2/11. |
| **Fases semafóricas y estado de vehículos** (`05`, `06`) | Secuencias continuas a 6 s. | Solo las 5 cámaras de referencia, en hora punta y dentro de las ventanas. |
| **Condiciones adversas** (OE-7) | Lluvia, niebla y noche. | Modo evento: un día con lluvia prevista por AEMET se trata como ventana en las 24 cámaras. La noche ya queda cubierta por la rejilla. |

**Cómo se aplica.** El servicio sigue capturando al ritmo actual, y [`scripts/depurar_raw.py`](../../scripts/README.md#depurar_rawpy) aplica la rejilla después. Así una imagen borrosa no deja una franja sin representante, y abrir o cerrar una ventana de evaluación no exige reiniciar el servicio. Parámetros en `config.yaml` → `retencion`.

| Pieza | Estado |
|---|---|
| Rejilla de 10 min (mejor imagen de cada franja y cámara) | Implementada (`src/retencion.py`) |
| Script de depuración, en simulación por defecto | Implementado (`scripts/depurar_raw.py`) |
| Ventanas de evaluación | Implementadas. La inicial (25/08–26/10/2026) se cerró el 09/11/2026; falta declarar la siguiente. |
| Modo evento por lluvia | Pendiente |
| Salvaguarda de disco en el servicio | Pendiente |
| Sacar `raw/` de OneDrive | Hecho (26/10/2026): *junction* a `C:\Users\loren\tfm-datos\raw` |

**Volumen:** la captura genera unos 2,6 GB al día (medido el 17/10/2026) y quedan 40 GB libres en disco, unos 15 días de margen. Con la rejilla, fuera de las ventanas se conservarían unos 0,3 GB al día. La primera simulación (26/10/2026) liberaría 4,14 GB, el 44 % de `raw/`, al cerrar la ventana inicial. Se aplicó el 09/11/2026: se borraron 67.721 imágenes (4,14 GB).

**Incidencia (6–9/11/2026).** Al mover el proyecto de `Escritorio\MASTER-UIMP\TFM` a `Escritorio\TFM`, el `.venv` quedó dañado y la captura se detuvo del 06/11 a las 18:40 UTC al 09/11 a las 11:22 UTC. Se reinstaló el entorno (PyTorch con CUDA) y se reconfiguró NSSM. Esos días son un hueco más en la cobertura.

## 3. Condiciones y restricciones de la captura y el guardado

### A. Continuidad y fiabilidad de la captura

1. **Servicio siempre activo.** El equipo no debe suspenderse con el servicio en marcha; si no, se pierden días completos, como el 23–24/10. Conviene un informe de cobertura por cámara, día y franja que detecte los huecos en el momento.
2. **Nada de duplicados en origen.** No se guarda la imagen si el servidor no ha publicado una nueva (mismo `Last-Modified`).
3. **Marcas de tiempo en UTC** en el nombre del fichero. La hora local solo se usa para franjas y tipo de día, lo que evita ambigüedades en los cambios de hora, como el del 25/10.
4. **Salvaguarda de disco.** Si el espacio libre baja de un umbral (por ejemplo, 20 GB), solo se guarda la rejilla y se avisa en el log.

### B. Calidad de cada imagen (`config.yaml` → `calidad`)

5. Resolución mínima de 640×480.
6. Brillo entre 30 y 220, con el mínimo exigido solo de día.
7. Nitidez por encima del percentil 5 de la distribución observada. Conviene valorar un umbral por iluminación: hoy se descarta el 20 % de las imágenes nocturnas frente al 1 % de las diurnas, y eso penaliza justo la condición adversa más disponible.
8. Una cámara entra en la lista negra si falla más del 30 % de sus imágenes diurnas. La lista se recalcula en cada ejecución.

### C. Diversidad y no redundancia del conjunto de entrenamiento

9. **Separación mínima de 10 minutos** entre dos imágenes de la misma cámara en cualquier lote. Es la misma franja que usa la rejilla.
10. **Muestreo estratificado** por cámara × franja horaria × tipo de día × iluminación, con un máximo de imágenes por cámara.
11. **Composición objetivo:**
    - Todas las franjas horarias, con más peso en las horas punta.
    - Al menos un 20 % de fines de semana o festivos.
    - Entre un 15 y un 20 % de noche o crepúsculo.
    - Entre un 5 y un 10 % de negativos: imágenes sin objetos relevantes, para reducir falsos positivos.
    - Un lote específico si llueve.
12. **Equilibrio entre cámaras.** Al menos 40 imágenes revisadas por cámara, y ninguna cámara por encima del 10 % del total.
13. **Clases escasas.** Lotes priorizados (`03b`) para semáforos rojos, verdes y peatonales, motos y poca luz. Mínimos orientativos de instancias revisadas: unas 500 en las clases principales y al menos 150 en las escasas. Por debajo de eso, los semáforos peatonales se fusionan con los vehiculares.

### D. Validez de la evaluación

14. **Test con cámaras no vistas.** Alrededor del 15 % de las cámaras (unas 4) se apartan antes de todo y nunca se usan para entrenar ni para elegir el modelo.
15. **Validación cruzada agrupada por cámara.** Una cámara nunca está a la vez en entrenamiento y validación.
16. **Solo etiquetas revisadas por humanos**, para evitar el entrenamiento circular, con el protocolo común de anotación. Se recomienda la doble anotación del ~10 % de las imágenes para medir el acuerdo entre anotadores.

### E. Conservación y trazabilidad

17. **Nunca se borra** una imagen que esté en un lote de anotación.
18. **Las ventanas de evaluación se conservan completas** hasta reprocesarlas con el detector entrenado.
19. **Todo borrado queda registrado** (cámara, imagen, fecha y motivo), y la depuración se ejecuta primero en modo simulación.
20. **Las imágenes no se versionan en git ni se publican.** El repositorio guarda solo índices, etiquetas y resultados.
21. **Privacidad.** Aunque las imágenes proceden de una fuente pública y tienen baja resolución, aparecen personas y vehículos. No se intentará identificar a nadie y las imágenes originales no se difundirán; conviene mencionarlo en la memoria.
