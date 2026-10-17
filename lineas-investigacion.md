# Línea de investigación

## Gap identificado

La revisión del estado del arte ha permitido identificar la ausencia de investigaciones que integren de forma conjunta:

- Detección de peatones.
- Detección de vehículos.
- Detección de semáforos y sus tiempos.

Aunque existen trabajos que abordan uno o dos de estos elementos de manera aislada, no se han encontrado propuestas recientes que integren todos ellos dentro de un único sistema de control inteligente del tráfico basado en visión artificial.

## Elementos diferenciadores

- La utilización de versiones **modernas** de arquitecturas y modelos de visión por computación, sobre las que todavía no hay literatura en esta temática.

- La **detección** de los tres tipos de elementos: **peatones**, **vehículos** y **semáforos**.

    - En la literatura señalada no se localiza una investigación que aúne la detección de esos tres tipos de elementos para mejorar el control inteligente de tiempos de los semáforos. Se encuentran _papers_ sobre detección de uno o dos de los elementos, pero no de los tres en conjunto.

- La evaluación de escenarios bajo **circunstancias adversas** (climáticas, iluminación, estado de las cámaras, etc.).

    - Se han localizado estudios realizados bajo escenarios adversos, como los de difícil visibilidad, tanto para el control semafórico (véase [ejemplo](https://arxiv.org/abs/2404.08081)) como para otras temáticas, como los coches autónomos (véase [ejemplo](https://ieeexplore.ieee.org/document/11015428)).

## Objetivos

Realizada la correspondiente investigación sobre la **literatura** en materia de detección de peatones y vehículos para el control inteligente de los tiempos de los semáforos (véase [estado del arte](estado_del_arte.md)), junto con el conocimiento adquirido del estado del arte de la **visión por computación** y sus **tendencias actuales**, se ha considerado iniciar una línea de investigación basada en los siguientes **objetivos**:

- OE-1. Analizar el estado del arte de los sistemas de visión por computador aplicados a la detección de peatones, vehículos y semáforos en entornos urbanos.

- OE-2. Seleccionar y adaptar una arquitectura moderna de detección de objetos, basada en YOLO26, para su aplicación en escenarios de tráfico urbano.

- OE-3. Desarrollar un modelo capaz de detectar simultáneamente peatones, vehículos y elementos semafóricos a partir de secuencias de vídeo procedentes de cámaras de tráfico.

- OE-4. Diseñar un mecanismo de estimación del estado y de los tiempos de los semáforos utilizando la información obtenida mediante visión artificial.

- OE-5. Analizar la relación existente entre la presencia de peatones, el flujo vehicular y los tiempos semafóricos en intersecciones urbanas.

- OE-6. Evaluar el rendimiento del sistema propuesto mediante métricas de precisión, recall, mAP, tiempo de inferencia y capacidad de operación en tiempo real.

- OE-7. Estudiar el comportamiento del sistema.

### Trazabilidad entre objetivos y notebooks

| Objetivo | Dónde se aborda |
|---|---|
| OE-1 | [estado_del_arte.md](estado_del_arte.md) |
| OE-2 | `02c_preproceso_deteccion_yolo26` (YOLO26 preentrenado como punto de partida), `04_entrenamiento_yolo26` (ajuste fino) |
| OE-3 | `03a_anotacion_lote_estratificado`, `03b_anotacion_lote_prioritario` (conjunto revisado por humanos), `04_entrenamiento_yolo26` |
| OE-4 | `00b_medicion_refresco_camaras` (viabilidad de medir fases), `02c_preproceso_deteccion_yolo26` (color del semáforo), `05_evaluacion_indicadores_trafico` (fracción de tiempo y duraciones de fase) |
| OE-5 | `05_evaluacion_indicadores_trafico`, `03c_anotacion_zonas_estado_vehiculos` y `06_clasificacion_estado_vehiculos` (cola real frente a vehículos aparcados) |
| OE-6 | `04_entrenamiento_yolo26` (mAP, precisión y recall por clase sobre cámaras no vistas) |
| OE-7 | `01b_eda_calidad_visual`, `02a_preproceso_calidad_contexto`, `02b_preproceso_meteorologia_aemet` (iluminación, clima y calidad de cámara como contextos de evaluación), `05_evaluacion_indicadores_trafico` (indicadores por contexto) |

`00a_captura_instantanea_catalogo` y `01a_eda_catalogo_camaras` son la base de datos común a todos los objetivos.

## Opciones evaluadas para el modelado de la investigación

### Opción A: YOLO26

- Modelo reciente ([enero 2026](https://docs.ultralytics.com/es/models/yolo26/)).
- Introduce un nuevo diseño denominado __End-to-End NMS-Free__, que mejora cuellos de botella y problemas del NMS clásico (inconsistencia entre frames o latencias mayores en entornos reales, entre otros).
- Un 43 % más rápido en CPU que los YOLO anteriores. Véase [enlace](https://docs.ultralytics.com/compare/).
- Incluye mejoras clave para la detección de objetos pequeños, como semáforos, gracias a STAL (Small-Target-Aware Label Assignment).
- Arquitectura preparada para entornos productivos.
- Ventajas prácticas frente a los Transformers:
    - Mientras los Transformers pueden superar en precisión, YOLO26 es mejor para producción en tiempo real, especialmente en cámaras urbanas.
    - Menor latencia en CPU.
    - Más facilidad de ajuste fino para conjuntos de datos pequeños.
    - Más maduro.

Elementos diferenciadores:
- No hay literatura en esta temática bajo la nueva arquitectura YOLO26.
- Se contemplarían los tres tipos de detecciones y se realizarían experimentos bajo circunstancias adversas.

### Opción B: RT-DETRv2

- Supera a YOLO en precisión y velocidad en tiempo real.
- Multiescala optimizada, ideal para peatones y semáforos.
- Recomendado para escenarios complejos (intersecciones, tráfico, aglomeraciones).
- Entrenamiento más flexible y robusto, adecuado para conjuntos de datos urbanos desbalanceados.
- Ventajas prácticas frente a YOLO:
    - Gran capacidad de detección de objetos pequeños y distantes.
    - Detección más estable en vídeo por su diseño NMS-free.
    - Soporta múltiples tamaños en función del hardware.

Elementos diferenciadores:
- No hay literatura en esta temática bajo la nueva arquitectura RT-DETRv2.
- Se contemplarían los tres tipos de detecciones y se realizarían experimentos bajo circunstancias adversas.
- Se evaluarían los resultados con otros modelos (YOLO y Transformers).

## Justificación de la selección de YOLO26

Se selecciona **YOLO26** ([enero 2026](https://docs.ultralytics.com/es/models/yolo26/)) como arquitectura base debido a que representa una de las líneas más recientes dentro de los detectores de objetos en tiempo real.

La elección se fundamenta en los siguientes motivos:

- Arquitectura End-to-End NMS-Free.
- Mayor velocidad de inferencia en CPU.
- Mejor capacidad de detección de objetos pequeños mediante STAL.
- Facilidad de adaptación mediante ajuste fino.
- Adecuación para despliegues en producción y escenarios de tráfico urbano.

Adicionalmente, frente a arquitecturas basadas en Transformers, YOLO26 ofrece menores tiempos de inferencia y menores requisitos computacionales, características especialmente relevantes para aplicaciones de gestión de tráfico en tiempo real.
