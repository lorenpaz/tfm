# Estado del arte en la detección de peatones, vehículos y estimación de tiempos de los semáforos

## Introducción
A continuación, se expondrá un listado de las **referencias científicas** encontradas en el campo de la visión computacional para abordar el caso de uso de la detección de peatones, vehículos y estimación de tiempos de espera de los semáforos mediante el uso de las cámaras de tráfico de una ciudad.

## Leyenda
- Columna 'Referencias':
    - 1 = Detección de peatones
    - 2 = Detección de vehículos
    - 3 = Tiempos de espera de semáforos

## Listado de artículos científicos (más reciente a más antiguo)

| Título | Autores | Fecha | Resumen | Comentarios | Limitaciones identificadas | Referencias | Modelo |
|--------|---------|-------|---------|-------------|----------------------------|-------------|--------|
| [YOLOv8-Based Real-Time Pedestrian Detection Model for Urban Traffic Surveillance Systems](https://www.joiv.org/index.php/joiv/article/view/5291) (*JOIV: International Journal on Informatics Visualization*) | Anmar B. Salih et al. | Marzo 2026 | PD-YOLOv8: versión optimizada de YOLOv8 para vigilancia urbana, entrenada con *City Street View* (2.528 imágenes extraídas de vídeo de tráfico). Obtiene 79,65% de precisión, 76,07% de recall, 82,40% mAP@0.5 y 64,80% mAP@0.5:0.95, mejorando a YOLOv5 y YOLOv8 base. | - Orientado a detección de peatones en entornos urbanos reales<br>- Mejora de precisión y mAP con respecto a modelos base<br>- Implementación práctica en un sistema web de vigilancia (cruce del MRT Bukit Bintang, Kuala Lumpur) | - No aborda control adaptativo de semáforos<br>- Centrado exclusivamente en peatones<br>- No integra información multimodal de tráfico | 1 | YOLOv8 |
| [A pedestrian detection model based on YOLO for dense scenes](https://doi.org/10.1007/s11801-026-4274-2) (*Optoelectronics Letters*, 22(4), 229–235) | Shujian Xing, Furong Wang, Hong Wang | 2026 | Modelo basado en YOLO para escenarios densos con oclusiones: convoluciones deformables, atención multidimensional y una pérdida IoU de diferencia diagonal. Alcanza 75,1% mAP@0.5 en WiderPerson (+1,8 puntos frente a YOLOv5). | - Aborda alta densidad peatonal y oclusiones<br>- Mejora frente a YOLOv5 en el dataset WiderPerson<br>- Complementa trabajos sobre escenarios complejos | - No aborda gestión del tráfico<br>- No contempla vehículos ni semáforos<br>- Validación focalizada en detección peatonal | 1 | YOLO |
| ⚠ Vision-Based Traffic Signal Light Detection for Intelligent Signal Timing Systems | Yinan Zhang et al. | 2026 (IEEE Access) | Propuesta de YOLO-MR para detección de semáforos con atención multiescala y módulos ligeros, integrada en un marco de optimización de tiempos semafóricos. | - Se alinea con estimación y gestión de tiempos de semáforos<br>- Va más allá de la detección aislada del semáforo<br>- Enfoque orientado al control inteligente de intersecciones | - No contempla detección de peatones<br>- No realiza control completo de la intersección<br>- Dependencia de la calidad visual del semáforo | 3 | YOLOv8 |
| ⚠ [An intelligent traffic management framework using YOLO driven vehicle detection and Q-learning based reinforcement signal optimization](https://doi.org/10.1007/s11760-026-05470-8) (*Signal, Image and Video Processing*) | Pendiente de verificar | Junio 2026 | Combina detección de vehículos basada en YOLO con aprendizaje por refuerzo (Q-learning, agentes distribuidos por intersección) para ajustar dinámicamente el control semafórico en función del estado observado del tráfico. Cifras pendientes de consultar en el texto completo. | - Línea más avanzada que sistemas puramente basados en densidad<br>- Muy relevante para trabajos futuros y tendencias de investigación<br>- Integra visión artificial y control inteligente | - Complejidad computacional elevada<br>- Dependencia de simulaciones y entrenamiento RL<br>- Escasa atención explícita a peatones | 2,3 | YOLO + Reinforcement Learning |
| [Smart Traffic Surveillance System with Adaptive Traffic Control Signal using YOLO](https://fci.stafpu.bu.edu.eg/Artificial%20Intelligence/6732/publications/sara%20mahmoud%20mostafa%20sweidan_Smart%20traffic%20management%20system%20using%20YOLOv11.pdf) | S. Nandhini, M. Magesh Kumar, M. Mownika, K. Ranganayagi, R. J. Pavithra | 2 de Julio 2025 | Control inteligente de semáforos mediante detección de vehículos en tiempo real con YOLO: adapta la duración del verde según la densidad, simula el flujo vehicular y reduce tiempos de espera y consumo de combustible. | - Ajuste dinámico de los tiempos semafóricos<br>- Comparación con YOLOv5 y Faster R-CNN<br>- Orientado a reducción de congestión | - Dataset limitado<br>- No contempla condiciones ambientales<br>- No considera detección de peatones | 2,3 | YOLO |
| [YOLO‑APD: Enhancing YOLOv8 for Robust Pedestrian Detection on Complex Road Geometries](https://doi.org/10.14445/22312803/IJCTT-V73I6P108) | Aquino Joctum, John Kandiri | 29 de Junio 2025 | Arquitectura mejorada de YOLOv8 con atención SimAM, módulos C3Ghost y SimSPPF. Alcanza 77,7% mAP y >96% de recall a 100 FPS en escenarios urbanos complejos, orientado a vehículos autónomos. | - Escenarios urbanos complejos<br>- Condiciones reales de tráfico y ambientales<br>- Comparación con múltiples modelos (YOLOv8, YOLOv7, Faster R-CNN, entre otros) | - No aborda control del tráfico<br>- Enfoque centrado en detección<br>- No integra estimación de tiempos semafóricos | 1,2 | YOLOv8 |
| [Research on Vehicle and Pedestrian Detection Based on Improved RT-DETR](http://ijanmc.org/202502/pdf/2025-02-09.pdf) | Jingshu Li, Jianguo Wang | Junio 2025 | Mejora de RT-DETR mediante un módulo de atención SimAM para la detección de objetivos pequeños. Obtiene 73,6% de precisión en BDD100K, 3,7 puntos más que RT-DETR base. | - Mejor rendimiento en objetivos pequeños<br>- Uso del dataset BDD100K<br>- Comparación con RT-DETR base | - No contempla gestión del tráfico<br>- Falta de validación operativa en intersecciones<br>- Comparación limitada al modelo base | 1,2 | RT-DETR (Transformer) |
| [Vehicle and Pedestrian Detection in Extreme Weather Based on Improved Rt-Detr](https://doi.org/10.1109/CCDC65474.2025.11090313) | M. Liu, R. Zhang, C. Gao, S. Zhang | Mayo 2025 | RT-DETR mejorado con un módulo de características multiescala para la detección de vehículos y peatones bajo condiciones meteorológicas extremas, mejorando la precisión con baja carga computacional. | - Considera clima extremo<br>- Mejora el tratamiento multiescala<br>- Mantiene baja carga computacional | - No aborda control semafórico<br>- Comparativa reducida frente a otros modelos modernos (solo RT-DETR base)<br>- Sin integración en sistemas ITS completos | 1,2 | RT-DETR (Transformer) |
| [Quantum‑Enhanced Transformer Network Model for Traffic Congestion Prediction in Smart Transportation Systems](https://doi.org/10.1007/s13177-025-00494-9) | Satendra Chandra Pandey, Vasanthi Kumari | 2 Mayo 2025 | TransTCGNet: combina convoluciones temporales y mecanismos Transformer optimizados con un algoritmo cuántico para predecir congestión. Reporta un 99% de *accuracy*. | - Predicción avanzada de congestión<br>- Tráfico real<br>- Comparación con otros modelos | - No aborda detección visual de peatones o vehículos<br>- Complejidad elevada de implementación<br>- Escasa validación sobre sistemas semafóricos reales | 2,3 | Transformer |
| [AI‑Driven Smart Traffic Management System: An Adaptive Approach Using YOLO and OpenCV](https://www.researchgate.net/publication/391493060_AI-Driven_Smart_Traffic_Management_System_An_Adaptive_Approach_Using_YOLO_and_OpenCV) | Vitthal B. Kamble et al. | 30 Abril 2025 | Sistema adaptativo de control semafórico con YOLO y OpenCV: detecta y cuenta vehículos por carril y ajusta dinámicamente los tiempos de semáforo. | - Ajuste dinámico de semáforos<br>- Implementación sencilla y reproducible<br>- Comparación con sistema tradicional | - No contempla peatones<br>- No contempla condiciones meteorológicas<br>- Utiliza YOLOv4 frente a arquitecturas más modernas | 2,3 | YOLOv4 |
| [Real-time traffic light detection based on lightweight improved RT-DETR](https://link.springer.com/article/10.1007/s11554-025-01652-8) | Chaoli Tang, Yun Li, Lei Wang, Wenyan Li | 15 Marzo 2025 | GAD-DETR: modelo ligero derivado de RT-DETR para detección de semáforos en tiempo real (arquitectura GRELAN basada en GhostNet + RepConv, con mejoras para objetos pequeños). Alcanza 95,9% mAP a 117,8 FPS. | - Alta velocidad de inferencia (117,8 FPS)<br>- Especializado en objetos pequeños<br>- Arquitectura ligera | - No contempla peatones ni vehículos<br>- No contempla gestión semafórica adaptativa<br>- Validación limitada a detección visual | 3 | RT-DETR (Transformer) |
| [Urban Signalized Intersection Traffic State Prediction: A Spatial–Temporal Graph Model Integrating the Cell Transmission Model and Transformer](https://doi.org/10.3390/app15052377) | Anran Li, Zhenlin Xu, Wenhao Li, Yanyan Chen, Yuyan Pan | 23 Febrero 2025 | Modelo CeT que integra un grafo espacio-temporal, Transformer y el *Cell Transmission Model* para predecir el recuento vehicular en intersecciones. Reduce MAE y RMSE en ~11–13% frente a SVR, LSTM y otros. | - Integración de grafos espacio-temporales y Transformer<br>- Mejora métricas MAE y RMSE<br>- Adecuado para predicción de tráfico urbano | - No contempla detección de peatones<br>- Sin procesamiento de información visual<br>- No realiza control adaptativo de semáforos | 2 | Transformer |
| [Transformer‑based short‑term traffic forecasting model considering traffic spatiotemporal correlation](https://doi.org/10.3389/fnbot.2025.1527908) | Ande Chang, Yuting Ji, Yiming Bie | 22 Enero 2025 | Trafficformer: captura patrones espacio-temporales con Transformer y enmascarado espacial para predecir la velocidad y el flujo de tráfico, superando a seis métodos de referencia. | - Captura relaciones espacio-temporales complejas<br>- Supera varios métodos de referencia<br>- Aplicable a sistemas ITS | - No contempla detección visual<br>- No considera peatones<br>- No propone control semafórico adaptativo | 2,3 | Transformer |

## Análisis de la literatura científica

Recuento sobre los **12 trabajos verificados** (se excluye YOLO-MR hasta confirmar su existencia). Cada característica se cuenta con el criterio indicado:

| Característica | Nº de estudios | Criterio aplicado | Trabajos |
|---------------|:--------------:|-------------------|----------|
| Detección de peatones | 5 | Detección visual de personas | Salih, Xing, YOLO-APD, Li & Wang, Liu |
| Detección de vehículos | 6 | Detección visual de vehículos | SIVP 2026, Nandhini, YOLO-APD, Li & Wang, Liu, Kamble |
| Detección de semáforos | 1 | Detección visual del semáforo y su estado | Tang (GAD-DETR) |
| Control adaptativo de tiempos | 3 | Modifica los tiempos semafóricos | SIVP 2026, Nandhini, Kamble |
| Condiciones climáticas adversas | 2 | Evalúa explícitamente lluvia, niebla, noche, etc. | YOLO-APD, Liu |
| Integración peatones + vehículos | 3 | Detecta ambos en el mismo modelo | YOLO-APD, Li & Wang, Liu |
| Integración vehículos + semáforos | 3 | Detección de vehículos + control semafórico | SIVP 2026, Nandhini, Kamble |
| Integración peatones + vehículos + semáforos | 0 | Las tres en un mismo sistema | — |
| Validación con cámaras urbanas fijas reales | 1 | Imágenes de cámaras de tráfico de una ciudad (no vehículo propio ni benchmark) | Salih |

## Análisis del estado del arte

El análisis de la literatura científica reciente permite identificar tres grandes líneas de trabajo:

1. Detección de peatones y vehículos mediante arquitecturas YOLO y RT-DETR.
2. Predicción y modelado del tráfico mediante Transformers.
3. Control inteligente de semáforos basado en visión artificial.

Los trabajos centrados en detección de objetos presentan elevadas tasas de precisión y rendimiento en tiempo real, especialmente aquellos basados en YOLO, en su versión 8, y sus variantes (p. ej. 77,7% mAP a 100 FPS en YOLO-APD o 82,4% mAP@0.5 en PD-YOLOv8). Sin embargo, suelen centrarse exclusivamente en tareas de detección sin integrar mecanismos de control semafórico.

Por otra parte, los modelos basados en Transformers muestran resultados prometedores para la predicción del estado del tráfico y la congestión, aunque generalmente no suelen utilizar información visual procedente de cámaras urbanas en tiempo real.

Finalmente, los estudios orientados al control adaptativo de semáforos utilizan principalmente la densidad de vehículos como variable de entrada, prestando escasa atención a la presencia de peatones o a escenarios climáticos adversos.

En consecuencia, se observa una falta de investigaciones que **integren simultáneamente**:
- Detección de peatones.
- Detección de vehículos.
- Detección de semáforos y sus tiempos.
- Optimización de tiempos semafóricos.
- Uso de cámaras urbanas reales.
- Evaluación bajo distintas condiciones ambientales.

Estas carencias constituyen una **base** para evaluar el principal cometido de investigación a realizar.