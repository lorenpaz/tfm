# Línea de investigación

## Gap identificado

La revisión del estado del arte ha permitido identificar la ausencia de investigaciones que integren de forma conjunta:

- Detección de peatones.
- Detección de vehículos.
- Detección de semáforos y sus tiempos.

Aunque existen trabajos que abordan uno o dos de estos elementos de manera aislada, no se han encontrado propuestas recientes que integren todos ellos dentro de un único sistema de control inteligente del tráfico basado en visión artificial.

## Objetivos

Realizada la correspondiente investigación sobre la **literatura** en materia de detección de peatones y vehículos para el control inteligente de los tiempos de los semáforos (véase [estado del arte](estado_del_arte.md)), junto con el conocimiento adquirido del estado del arte de la **visión por computación** y sus **tendencias actuales**, se ha considerado iniciar una línea de investigación basada en los siguientes **objetivos**:

- OE-1. Analizar el estado del arte de los sistemas de visión por computador aplicados a la detección de peatones, vehículos y semáforos en entornos urbanos.

- OE-2. Seleccionar y adaptar una arquitectura moderna de detección de objetos, basada en YOLO26, para su aplicación en escenarios de tráfico urbano.

- OE-3. Desarrollar un modelo capaz de detectar simultáneamente peatones, vehículos y elementos semafóricos a partir de secuencias de vídeo procedentes de cámaras de tráfico.

- OE-4. Diseñar un mecanismo de estimación del estado y de los tiempos de los semáforos utilizando la información obtenida mediante visión artificial.

- OE-5. Analizar la relación existente entre la presencia de peatones, el flujo vehicular y los tiempos semafóricos en intersecciones urbanas.

- OE-6. Evaluar el rendimiento del sistema propuesto mediante métricas de precisión, recall, mAP, tiempo de inferencia y capacidad de operación en tiempo real.

- OE-7. Estudiar el comportamiento del sistema.

## Justificación de la selección de YOLO26

Se selecciona **YOLO26** [enero 2026](https://docs.ultralytics.com/es/models/yolo26/) como arquitectura base debido a que representa una de las líneas más recientes dentro de los detectores de objetos en tiempo real.

La elección se fundamenta en los siguientes motivos:

- Arquitectura End-to-End NMS-Free.
- Mayor velocidad de inferencia en CPU.
- Mejor capacidad de detección de objetos pequeños mediante STAL.
- Facilidad de adaptación mediante fine-tuning.
- Adecuación para despliegues en producción y escenarios de tráfico urbano.

Adicionalmente, frente a arquitecturas basadas en Transformers, YOLO26 ofrece menores tiempos de inferencia y menores requisitos computacionales, características especialmente relevantes para aplicaciones de gestión de tráfico en tiempo real.