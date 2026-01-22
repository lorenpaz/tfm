# Líneas de investigación

Realizada la correspondiente investigación sobre la **literatura** en materia de detección de peatones y vehículos para el control inteligente de los tiempos de los semáforos (véase ), junto con el conocimiento adquirido del estado del arte de la **visión por computación** y sus **tendencias actuales**, se proponen las siguientes **líneas de investigación**.

En las opciones, se contemplan los siguientes **requerimientos**:
    
- Contemplar la utilización de versiones **modernas** de arquitectura y modelos de visión por computación para no encontrar literatura similar.
    
- La detección de los tres tipos de elementos: peatones, vehículos y semáforos.

   - En la literatura señalada, no se localiza una investigación que aúne la detección de esos tres tipos de elementos para mejorar el control inteligente de tiempos de los semáforos. Se encuentran _papers_ sobre detección de uno o dos de los elementos, pero no los tres en conjunto.

- Contemplar experimentos bajo circunstancias adversas (climáticas, estado de las cámaras, etc.).

  - Se han localizado estudios realizados bajo escenarios adversos, como los escenarios de difícil visibilidad, tanto para el control semafórico (véase [ejemplo](https://arxiv.org/abs/2404.08081)), como para otras temáticas, como los coches autónomos (véase [ejemplo](https://ieeexplore.ieee.org/document/11015428)). 

## Opciones

### Opción A
Contemplar como modelo base **YOLO26**, el cual, presenta las siguientes características:

- Modelo reciente ([enero 2026](https://docs.ultralytics.com/es/models/yolo26/))
- Introduce un nuevo diseño denominado __End-to-End NMS-Free__ mejorando cuellos de botella y problemas del NMS clásico (inconsistencia entre frames o latencias mayores en entornos reales, entre otros).
- Un 43% más rápido en CPU que YOLOS anteriores. Véase [enlace](https://docs.ultralytics.com/compare/)
- Incluye mejoras clave para detección de objetos pequeños, como semáforos, gracias a la innovación STAL (Small-Target-Aware Label Assignment).
- Además, se presenta como un modelo bajo una arquitectura preparada para entornos productivos.
- Presenta las siguientes ventajas prácticas frente a los Transformers:
      - Mientras los Transformers pueden superar en precisión, YOLO26 es mejor para producción en tiempo real, especialmente en cámaras urbanas
      - Menor latencia en CPU
      - Más facilidad de fine-tuning para datasets pequeños
      - Más maduro

Elementos diferenciadores:
- No hay literatura en esta temática bajo la nueva arquitectura YOLO26
- Se contemplarían los tres tipos de detecciones y se realizarían experimentos bajo circunstancias adversas
- Se evaluarían los resultados con otros modelos (YOLOs y Transformers)


### Opción B
Contemplar como modelo base **Real-Time Detection Transformer v2 (RT-DETRv2)**, el cual, presenta las siguientes características:

- Supera a YOLO en precisión y velocidad en tiempo real.
- Multiescala optimizada, ideal para peatones y semáforos.
- Recomendado para escenarios complejos (intersecciones, tráfico, aglomeraciones).
- El entrenamiento es más flexible y robusto, adecuado para datasets de entornos urbanos desbalanceados.
- Incluye mejoras clave para detección de objetos pequeños, como semáforos, gracias a la innovación STAL (Small-Target-Aware Label Assignment).
- Además, se presenta como un modelo bajo una arquitectura preparada para entornos productivos.
- Presenta las siguientes ventajas prácticas frente a YOLO:

  - Gran capacidad de detección de objetos pequeños y distantes.
  - Presenta una detección más estable en vídeo por su modelo NMS-free.
  - Mejor detección sólida.
  - Soporta múltiples tamaños en función del hardware.

Elementos diferenciadores:
- No hay literatura en esta temática bajo la nueva arquitectura RT-DETRv2
- Se contemplarían los tres tipos de detecciones y se realizarían experimentos bajo circunstancias adversas
- Se evaluarían los resultados con otros modelos (YOLOs y Transformers)
  
## Propuesta de elección
La elección entre ambas opciones no es sencilla por las pequeñas diferencias que se extraen en la aplicación de éstos a nuestro caso de negocio.


