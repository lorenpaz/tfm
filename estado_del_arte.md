# Estado del arte en la detección de peatones, vehículos y estimación de tiempos de los semáforos

## Introducción
A continuación, se expondrá un listado de las **referencias científicas** encontradas en el campo de la visión computacional con el uso de los algoritmos YOLO o Transformers para abordar el caso de uso de la detección de peatones, vehículos y estimación de tiempos de espera de los semáforos mediante el uso de las cámaras de tráfico de una ciudad.

## Leyenda
- Columna 'Referencias':
    - 1 = Detección de peatones
    - 2 = Detección de vehículos
    - 3 = Tiempos de espera de semáforos

## Listado de artículos científicos

| Título | Autores | Fecha | Resumen | Referencias | Modelo |
|--------|---------|-------|---------|-------------|----------|
| [YOLO‑APD: Enhancing YOLOv8 for Robust Pedestrian Detection on Complex Road Geometries](https://doi.org/10.14445/22312803/IJCTT-V73I6P108) | Aquino Joctum, John Kandiri | 29 de Junio 2025 (Fecha de publicación) | Arquitectura mejorada de YOLOv8 con atención SimAM, módulos C3Ghost y SimSPPF, alcanzando 77.7% mAP y >96% recall, procesando a 100 fps en escenarios urbanos complejos, de cara a mejorar sistemas de vehículos autónomos. | 1,2 | YOLO |
| [AI‑Driven Smart Traffic Management System: An Adaptive Approach Using YOLO and OpenCV](https://www.researchgate.net/publication/391493060_AI-Driven_Smart_Traffic_Management_System_An_Adaptive_Approach_Using_YOLO_and_OpenCV) | Vitthal B. Kamble et al. | 30 Abril 2025 (Fecha de publicación) | Sistema de gestión de semáforos adaptativo con YOLO y OpenCV: detecta y cuenta vehículos por carril, ajusta dinámicamente los tiempos de semáforo para optimizar flujo de tráfico. | 1,2,3 | YOLO |
| [Smart Traffic Surveillance System with Adaptive Traffic Control Signal using YOLO](https://fci.stafpu.bu.edu.eg/Artificial%20Intelligence/6732/publications/sara%20mahmoud%20mostafa%20sweidan_Smart%20traffic%20management%20system%20using%20YOLOv11.pdf) | S. Nandhini, M. Magesh Kumar, M. Mownika, K. Ranganayagi, R. J. Pavithra | 2 de Julio 2025 (Fecha de publicación) | Control inteligente de semáforos mediante detección de vehículos en tiempo real con YOLO: adapta duración de verde con base en densidad, simula flujo vehicular y reduce tiempos de espera y consumo de combustible. | 1,2,3 | YOLO |
| [Urban Signalized Intersection Traffic State Prediction: A Spatial–Temporal Graph Model Integrating the Cell Transmission Model and Transformer](https://doi.org/10.3390/app15052377) | Anran Li, Zhenlin Xu, Wenhao Li, Yanyan Chen, Yuyan Pan | 23 Febrero 2025 (Fecha de publicación) | Modelo CeT que integra grafo espacio-temporal con Transformer y el Cell Transmission Model para predecir recuento vehicular en intersecciones. Reducciones de ~11–13% en MAE y RMSE. | 2,3 | Transformer |
| [Transformer‑based short‑term traffic forecasting model considering traffic spatiotemporal correlation](https://doi.org/10.3389/fnbot.2025.1527908) | Ande Chang, Yuting Ji, Yiming Bie | 22 Enero 2025 (Fecha de publicación) | Trafficformer: captura patrones espacio-temporales del tráfico con Transformer y enmascarado espacial, prediciendo velocidad vial con precisión superior a seis métodos base. | 2,3 | Transformer |
| [Quantum‑Enhanced Transformer Network Model for Traffic Congestion Prediction in Smart Transportation Systems](https://doi.org/10.1007/s13177-025-00494-9) | Satendra Chandra Pandey & Vasanthi Kumari | 2 Mayo 2025 (Fecha de publicación) | TransTCGNet: combina convoluciones temporales y mecanismos Transformer optimizados con algoritmo cuántico para predecir congestión. Reporta 99% en accuracy. | 1,2,3 | Transformer |
| [Synchronous End‑to‑End Vehicle Pedestrian Detection Algorithm Based on Improved YOLOv8 in Complex Scenarios](https://doi.org/10.3390/s24186116) | Shi Lei, He Yi, Jeffrey S. Sarmiento | 22 Septiembre 2024 (Fecha de publicación) | Mejora de YOLOv8 con convolución deformable y atención; aumenta precisión en detección de vehículos y peatones en un 11.76%, mAP +6.27%, con velocidad 41 fps. | 1,2 | YOLO |
| [A CNN‑BASED MODEL FOR DYNAMIC TRAFFIC SIGNAL TIMING ESTIMATION AT SIMPLE URBAN INTERSECTIONS](https://www.arpnjournals.org/jeas/research_papers/rp_2022/jeas_0122_8822.pdf) | Camilo A. Laiton‑Bonadiez, German Sánchez‑Torres, Carlos Henriquez‑Miranda | Enero 2022 (Fecha de publicación) | Propone modelo CNN que estima en tiempo real ciclos de semáforo basados en volumen vehicular y basado en fórmula de Webster, con reducción del 60% en tiempo de espera. | 1,2,3 | CNN |
