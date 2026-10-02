# SPEC_TFM.md
# Especificación para la redacción de la memoria del TFM

## 1. Identidad del trabajo

Título de trabajo:

**Optimización de la Asistencia Robótica mediante Sistemas de Memoria de Largo Plazo Basados en RAG Multimodal y Bases de Datos Vectoriales**

Tipo de trabajo:

Trabajo Fin de Máster del Máster Universitario en Big Data y Ciencia de Datos.

Dominio:

- robótica asistiva;
- navegación autónoma;
- memoria de largo plazo;
- recuperación contextual de información;
- RAG;
- bases de datos vectoriales;
- ROS 2;
- Nav2;
- simulación robótica.

El trabajo se realiza exclusivamente en simulación.

No existe robot físico dentro del alcance experimental del TFM.

---

# 2. Objetivo científico central

El TFM estudia si incorporar una memoria personalizada, contextual y
longitudinal a un sistema de navegación robótica asistiva permite
adaptar mejor las decisiones de navegación al usuario y al contexto.

La contribución principal NO es desarrollar:

- un nuevo LLM;
- un nuevo VLA;
- un nuevo algoritmo de planificación;
- un nuevo algoritmo SLAM;
- un sustituto de Nav2.

La contribución principal es:

> diseñar, implementar e integrar un sistema de memoria de largo plazo
> capaz de recuperar experiencias y preferencias relevantes y utilizar
> esa información para adaptar decisiones de navegación de un robot
> asistivo manteniendo Nav2 como responsable de la ejecución segura.

---

# 3. Pregunta de investigación

Pregunta principal:

> ¿El uso de una memoria personalizada y contextual mejora la adaptación
> de la navegación de un robot asistivo respecto a un sistema equivalente
> que no utiliza memoria?

La memoria debe construirse alrededor de esta pregunta.

No desplazar el foco hacia:

- rendimiento puro de Nav2;
- reconocimiento facial;
- generación de lenguaje;
- percepción como contribución principal;
- optimización de trayectorias clásica;
- comparación de algoritmos de planificación.

Esos componentes pueden aparecer como infraestructura o contexto, pero
no como contribución científica central.

---

# 4. Hipótesis

## H1

La utilización de memoria contextual y personalizada permite producir
decisiones de navegación más adaptadas al usuario que una configuración
equivalente sin acceso a memoria.

## H2

La incorporación explícita de contexto de usuario, localización, tarea y
objetivo mejora la relevancia de las memorias recuperadas respecto a una
recuperación basada únicamente en similitud semántica.

## H3

La recuperación de experiencias episódicas previas permite seleccionar
estrategias de navegación coherentes con preferencias previamente
observadas del usuario.

Estas hipótesis deben mantenerse diferenciadas de los resultados.

Hasta disponer de la campaña experimental final no escribir:

- "se demuestra H1";
- "se confirma H2";
- "la memoria mejora...";
- porcentajes de mejora;
- conclusiones cuantitativas no obtenidas.

---

# 5. Principio arquitectónico fundamental

Arquitectura conceptual del sistema con memoria:

User
  ↓
Context Builder
  ↓
Memory Retrieval
  ↓
Navigation Recommendation
  ↓
Assistive Behavior Tree
  ↓
Nav2
  ↓
Robot / Gazebo

La memoria recupera información considerando potencialmente:

- consulta semántica;
- user_id;
- location;
- task;
- goal;
- experiencias episódicas;
- preferencias previas.

La recomendación obtenida puede traducirse en una estrategia de
navegación.

Ejemplo conceptual:

memoria relevante
→ preferencia por mayor espacio lateral
→ estrategia "west"
→ waypoint intermedio
→ Nav2 ejecuta waypoint
→ Nav2 ejecuta destino final.

REGLA CRÍTICA:

La memoria nunca sustituye las funciones de seguridad y navegación de
Nav2.

El sistema de memoria propone/adapta una estrategia de alto nivel.

Nav2 continúa siendo responsable de:

- planificación;
- control;
- evitación de obstáculos;
- navegación;
- recuperación;
- ejecución segura de los goals.

No escribir que el RAG "controla el robot directamente".

---

# 6. Arquitectura experimental N0/N1

El experimento compara dos configuraciones equivalentes.

## N0 — baseline sin memoria

User/request
  ↓
Assistive Behavior Tree
  ↓
Nav2
  ↓
final goal

Características:

- no realiza consultas a memoria;
- no obtiene recomendaciones;
- no utiliza waypoint derivado de memoria;
- navega directamente al objetivo común.

## N1 — navegación con memoria

User/request
  ↓
QueryMemory
  ↓
NavigationRecommendation
  ↓
ResolveStrategyWaypoint
  ↓
Nav2 waypoint
  ↓
Nav2 final goal

Si no existe una estrategia aplicable:

N1 puede navegar directamente al final.

Si el waypoint falla:

el goal final no debe enviarse.

La comparación científica debe mantener constantes, salvo la
intervención de memoria:

- escenario;
- posición inicial;
- objetivo;
- configuración Nav2;
- estado del entorno;
- parámetros relevantes;
- criterio de éxito.

---

# 7. Behavior Tree

Existe un Behavior Tree de alto nivel específico del sistema asistivo.

NO confundirlo con el Behavior Tree interno de Nav2.

Existen dos niveles:

## Nivel 1 — Assistive BT

Decide el flujo experimental:

- memoria OFF / ON;
- consulta;
- recomendación;
- resolución de estrategia;
- waypoint;
- navegación final;
- finalización/logging.

## Nivel 2 — Nav2 BT

Nav2 conserva su propio árbol de comportamiento para ejecutar la
navegación.

La memoria no reemplaza el Nav2 BT.

Esta separación debe explicarse claramente en la memoria.

---

# 8. Sistema de memoria

Tecnologías principales:

- PostgreSQL;
- pgvector;
- embeddings;
- recuperación semántica;
- scoring contextual.

Dataset experimental actual:

50 memorias.

Cada memoria puede contener información como:

- usuario;
- localización;
- tarea;
- objetivo;
- observación;
- acción;
- resultado;
- preferencia.

Servicios ROS 2 principales:

## MemoryQuery

Entrada conceptual:

- query;
- user_id;
- location;
- task;
- goal;
- k.

Salida:

- memory_ids;
- summaries;
- observations;
- actions;
- outcomes;
- preferences;
- semantic_scores;
- context_scores;
- final_scores.

## NavigationRecommendation

Entrada:

- query;
- user_id;
- location;
- task;
- goal;
- k.

Salida conceptual:

- strategy;
- avoid_obstacle;
- prefer_clearance;
- source_memory;
- reason;
- observation;
- action;
- outcome;
- preference;
- scores.

---

# 9. Recuperación contextual

No describir el sistema simplemente como búsqueda vectorial.

El objetivo es combinar:

similaridad semántica

con señales contextuales relacionadas con:

- usuario;
- ubicación;
- tarea;
- objetivo.

Representación conceptual:

final_score =
    semantic_component
    +
    contextual_component

La fórmula exacta debe obtenerse SIEMPRE del código/documentación actual
antes de incluirla en la memoria.

Nunca inventar pesos.

---

# 10. Evidencia técnica actualmente disponible

Existe evidencia de ingeniería para una consulta canónica con contexto:

usuario:
U01

localización:
salon

tarea:
navegacion

objetivo:
dormitorio

consulta:
"navegar evitando la mesa"

k:
3

Resultado de recuperación observado:

M001
M046
M002

La memoria M001 contiene conceptualmente:

observación:
"Paso estrecho junto a la mesa."

acción:
"Ruta oeste evitando la mesa."

resultado:
"Navegacion correcta."

preferencia:
"Prefiere mayor espacio lateral."

La recomendación correspondiente produjo:

strategy = west

y activó indicadores relacionados con:

- evitación del obstáculo;
- preferencia por mayor clearance.

Esta evidencia sirve como validación funcional del pipeline.

NO presentarla como resultado de eficacia científica N0 vs N1.

---

# 11. Validaciones de ingeniería

Distinguir siempre:

## Validación de ingeniería

Pregunta:

"¿Funciona el sistema como fue diseñado?"

Incluye:

- tests unitarios;
- tests de servicios;
- recuperación correcta;
- recommendation correcta;
- contratos de logging;
- Behavior Tree;
- readiness;
- PostgreSQL;
- integridad del dataset;
- builds.

## Evaluación científica

Pregunta:

"¿La memoria mejora la adaptación respecto al baseline?"

Incluye:

- comparación N0/N1;
- múltiples escenarios;
- repeticiones;
- métricas;
- análisis estadístico/descriptivo;
- interpretación.

NO mezclar ambas categorías.

Los tests exitosos NO prueban H1/H2/H3 por sí mismos.

---

# 12. Readiness y limitación conocida

Se implementó una protección de readiness antes del envío de goals.

Se comprueba el estado de los nodos Nav2 relevantes antes de enviar un
goal.

Ante fallo de readiness:

- el goal no debe enviarse;
- el sistema falla de forma cerrada;
- se registra failure_stage = readiness.

Esta modificación surgió tras detectar que una comprobación inicial de
readiness no garantizaba que todos los nodos siguieran disponibles en el
momento del envío del goal.

Existe una limitación técnica conocida relacionada con estabilidad de
Nav2/lifecycle/discovery.

El root cause NO ha sido demostrado.

No afirmar:

- bug de DDS;
- bug de map_server;
- race condition concreta;
- falta de recursos;
- problema de Gazebo;

como causa demostrada.

La formulación correcta es:

> Durante la validación integrada se observaron episodios de
> indisponibilidad de servicios/lifecycle de Nav2 cuya causa raíz no pudo
> determinarse de forma concluyente.

La protección de readiness evita enviar goals cuando detecta ese estado,
pero no constituye una solución a la causa subyacente.

---

# 13. Política experimental ante fallos de infraestructura

Un intento afectado por un fallo de infraestructura independiente de la
intervención experimental debe marcarse como:

INFRASTRUCTURE INVALID

No utilizarlo para concluir si N0 o N1 es mejor.

La política de:

- retries;
- timeout;
- exclusión;
- número de repeticiones;

debe definirse ANTES de la campaña final y aplicarse exactamente igual a
N0 y N1.

No eliminar silenciosamente ejecuciones fallidas.

---

# 14. Métricas

Métricas principales previstas:

## Success rate

Proporción de ejecuciones válidas que alcanzan correctamente el objetivo.

## Navigation time

Tiempo desde el primer goal enviado a Nav2 hasta la finalización de la
ejecución.

En N1 incluye, cuando existe:

waypoint + final goal.

No incluye el tiempo previo de retrieval si se mantiene el contrato
actual.

## Distance

Distancia recorrida obtenida mediante odometría.

## Context compliance

Métrica central para determinar si la navegación elegida es coherente
con la preferencia/contexto esperado del escenario.

Debe definirse mediante ground truth independiente del sistema de
memoria.

## Minimum clearance

Distancia mínima respecto a obstáculos.

NO presentar resultados de esta métrica hasta que su mecanismo de
medición esté implementado y validado.

Métricas secundarias:

- replanning_count;
- strategy_applied;
- intervention_appropriate;
- waypoint_result;
- final_result.

Posible métrica futura:

- memory_latency_ms.

---

# 15. Logging experimental

Existe un contrato común de logging para N0 y N1.

Características:

- una fila por ejecución;
- mismo esquema;
- 35 columnas;
- run_id independiente;
- campos de memoria N/A cuando N0 no utiliza memoria.

No cambiar nombres o semántica de métricas en la memoria sin verificar
el contrato actual del código.

---

# 16. Escenarios experimentales

Se plantean al menos tres familias de escenarios.

## S1 — Home / static-personal

Entorno doméstico.

Ejemplo:

paso cercano a una mesa frente a ruta alternativa con mayor espacio
lateral.

Objetivo:

evaluar adaptación a preferencias personales de navegación.

## S2 — Mall / semi-dynamic

Entorno tipo centro comercial.

Elementos:

- zonas congestionadas;
- obstáculos/personas dinámicas;
- alternativas de ruta.

Objetivo:

evaluar utilización de memoria contextual en un entorno menos estático.

## S3 — Airport / dynamic

Entorno tipo aeropuerto.

Elementos:

- flujos dinámicos;
- obstáculos móviles;
- rutas alternativas;
- experiencia previa relevante.

Objetivo:

evaluar recuperación de experiencias y adaptación en un contexto
dinámico.

IMPORTANTE:

Estos escenarios pueden estar PLANNED y no necesariamente implementados
todavía.

Nunca describir como implementado aquello que siga en planificación.

---

# 17. Entorno tecnológico

Entorno principal:

- Windows 11 como sistema host;
- WSL2;
- Ubuntu 24.04;
- ROS 2 Jazzy;
- Gazebo Harmonic;
- Nav2;
- Python 3.12 para entorno de memoria;
- PostgreSQL;
- pgvector;
- Docker;
- C++ y Python;
- colcon.

Verificar versiones concretas en el repositorio antes de escribirlas como
definitivas.

---

# 18. Estructura ROS 2

El proyecto contiene paquetes como:

- wheelchair_description;
- wheelchair_gazebo;
- wheelchair_navigation;
- wheelchair_bringup;
- wheelchair_interfaces;
- wheelchair_memory;
- wheelchair_vla;
- wheelchair_api;
- wheelchair_assistive_bt.

No describir todos con el mismo nivel de detalle.

Dar prioridad a los que participan directamente en la contribución:

wheelchair_memory
wheelchair_assistive_bt
wheelchair_navigation
wheelchair_bringup
wheelchair_interfaces

Los demás pueden describirse como infraestructura cuando corresponda.

---

# 19. Reconocimiento facial

Existe trabajo relacionado con identificación/reconocimiento del usuario.

Tecnología utilizada:

InsightFace / FaceAnalysis.

TensorFlow se utiliza en otros componentes históricos, por ejemplo
detección de sonrisa.

El reconocimiento facial NO debe dominar la memoria del TFM.

Su función conceptual es:

identificar al usuario
→ recuperar su contexto/preferencias
→ permitir personalización.

Presentarlo como componente auxiliar del contexto si finalmente forma
parte del sistema evaluado.

No convertir el TFM en un trabajo sobre reconocimiento facial.

---

# 20. RAG y VLA

Usar estos términos con precisión.

## RAG

La recuperación de memorias relevantes proporciona contexto adicional
para tomar una decisión.

Explicar:

consulta
→ embedding
→ recuperación
→ contextualización
→ recomendación.

No afirmar que cualquier búsqueda vectorial es automáticamente un
sistema RAG completo sin explicar cómo se utiliza el contexto recuperado.

## VLA

El contexto histórico del proyecto incluye Vision-Language-Action.

Sin embargo, la contribución experimental actual está centrada en
memoria contextual aplicada a navegación.

No afirmar que se ha entrenado o desarrollado un nuevo modelo VLA.

Si VLA aparece en estado del arte, explicar su relación con agentes
robóticos multimodales y memoria, no presentarlo como implementación
principal si no lo es.

---

# 21. Estructura propuesta de la memoria

## 1. Introducción

1.1 Contexto y motivación  
1.2 Problema  
1.3 Objetivos  
1.4 Pregunta de investigación  
1.5 Hipótesis  
1.6 Contribuciones  
1.7 Estructura del documento

## 2. Estado del arte

2.1 Robótica asistiva  
2.2 Navegación autónoma en robótica asistiva  
2.3 Navegación en entornos estáticos y dinámicos  
2.4 Robótica sensible al contexto  
2.5 Memoria en agentes y robots  
2.6 Memoria episódica y personalizada  
2.7 RAG y bases de datos vectoriales  
2.8 Modelos fundacionales / VLA en robótica  
2.9 Behavior Trees y arquitecturas de navegación  
2.10 Limitaciones de los trabajos existentes  
2.11 Posicionamiento del TFM

El estado del arte debe conducir progresivamente al gap:

navegación
→ contexto
→ memoria
→ recuperación
→ personalización
→ integración con navegación segura.

## 3. Arquitectura del sistema

3.1 Visión general  
3.2 Arquitectura software  
3.3 ROS 2 y paquetes  
3.4 Gazebo y robot simulado  
3.5 Nav2  
3.6 Sistema de memoria  
3.7 PostgreSQL y pgvector  
3.8 Servicios ROS 2  
3.9 Assistive Behavior Tree  
3.10 Integración memoria → estrategia → Nav2  
3.11 Seguridad y readiness

## 4. Metodología de memoria contextual

4.1 Representación de una memoria  
4.2 Dataset de memorias  
4.3 Embeddings  
4.4 Recuperación semántica  
4.5 Scoring contextual  
4.6 Recuperación híbrida  
4.7 Generación de recomendación  
4.8 Conversión de recomendación en estrategia  
4.9 Gestión de experiencias longitudinales

## 5. Metodología experimental

5.1 Pregunta e hipótesis  
5.2 Baseline N0  
5.3 Sistema N1  
5.4 Variables independientes/dependientes  
5.5 Escenarios  
5.6 Métricas  
5.7 Logging  
5.8 Número de ejecuciones  
5.9 Política de fallos de infraestructura  
5.10 Procedimiento experimental  
5.11 Reproducibilidad

## 6. Validación técnica

6.1 Tests del sistema de memoria  
6.2 Tests de retrieval  
6.3 Tests de recommendation  
6.4 Tests del Behavior Tree  
6.5 Contrato de logging  
6.6 Readiness  
6.7 Integración con Nav2  
6.8 Limitaciones técnicas

## 7. Resultados experimentales

NO escribir hasta tener campaña final.

Posteriormente:

7.1 Resultados S1  
7.2 Resultados S2  
7.3 Resultados S3  
7.4 Comparación N0/N1  
7.5 Análisis por métricas  
7.6 Relación con hipótesis

## 8. Discusión

Interpretar resultados sin exagerar causalidad.

Separar:

- qué indican los datos;
- posibles explicaciones;
- limitaciones;
- amenazas a la validez.

## 9. Conclusiones y trabajo futuro

Responder explícitamente a la pregunta de investigación.

Sólo hacerlo después de disponer de resultados.

---

# 22. Estado del arte — reglas de fuentes

NUNCA inventar referencias bibliográficas.

Toda afirmación científica importante debe estar respaldada por una
fuente real.

Priorizar:

- artículos peer-reviewed;
- IEEE;
- ACM;
- Springer;
- Elsevier;
- arXiv sólo cuando sea apropiado;
- documentación oficial para ROS 2/Nav2/Gazebo/PostgreSQL/pgvector.

Distinguir:

FUENTE CIENTÍFICA
vs
DOCUMENTACIÓN TÉCNICA.

No usar documentación de ROS como evidencia de una afirmación científica
sobre comportamiento humano o robótica asistiva.

No generar DOI ficticios.

No inventar autores.

Si una referencia no está disponible:

escribir:

[CITA PENDIENTE]

en vez de inventarla.

---

# 23. Regla de trazabilidad para Copilot

Antes de escribir una afirmación sobre la implementación, buscar
evidencia en el repositorio.

Orden de prioridad:

1. código actual;
2. tests actuales;
3. configuración actual;
4. resultados experimentales guardados;
5. documentación actual;
6. informes históricos.

Si código y documentación se contradicen:

NO decidir silenciosamente.

Marcar:

[VERIFICAR: contradicción código/documentación]

---

# 24. Etiquetas obligatorias durante la redacción

Mientras la memoria esté en desarrollo utilizar:

[CITA PENDIENTE]

para afirmaciones que necesitan bibliografía.

[RESULTADO PENDIENTE]

para resultados experimentales todavía no disponibles.

[VERIFICAR EN CÓDIGO]

para detalles de implementación no confirmados.

[DECISIÓN PENDIENTE]

para decisiones metodológicas aún abiertas.

[FIGURA PENDIENTE]

para diagramas todavía no creados.

[TABLA PENDIENTE]

para tablas todavía no generadas.

Estas etiquetas deben eliminarse únicamente cuando exista evidencia.

---

# 25. Estilo de escritura

Idioma:

español académico.

Tono:

- técnico;
- preciso;
- impersonal o primera persona plural académica según guía del máster;
- sin lenguaje promocional.

Evitar:

"revolucionario"
"innovador" sin evidencia
"óptimo"
"inteligente" como término vago
"mejora significativamente" sin prueba estadística
"demuestra" cuando sólo existe evidencia preliminar.

Preferir:

"se propone"
"se implementa"
"se evalúa"
"se observa"
"los resultados sugieren"
"en las condiciones evaluadas"

según corresponda.

---

# 26. Diferenciar hecho, diseño y resultado

Copilot debe distinguir siempre:

IMPLEMENTED
→ existe en código.

VALIDATED
→ existe evidencia técnica de que funciona.

PLANNED
→ está previsto pero no implementado/validado.

EXPERIMENTALLY DEMONSTRATED
→ existe evidencia de campaña científica.

Nunca convertir:

PLANNED → IMPLEMENTED

ni:

VALIDATED → EXPERIMENTALLY DEMONSTRATED.

---

# 27. Diagramas

Figuras recomendadas:

1. Arquitectura global.
2. Flujo N0.
3. Flujo N1.
4. Arquitectura del sistema de memoria.
5. Pipeline de retrieval.
6. Assistive BT vs Nav2 BT.
7. Modelo de datos de memoria.
8. Arquitectura ROS 2.
9. Diseño experimental.
10. Escenarios S1/S2/S3.

Cada figura debe responder a una pregunta concreta.

Evitar diagramas decorativos.

---

# 28. Tablas recomendadas

- comparación N0/N1;
- campos de memoria;
- servicios ROS;
- paquetes ROS;
- variables experimentales;
- métricas;
- escenarios;
- tests de validación;
- resultados por escenario;
- amenazas a la validez.

---

# 29. Resultados históricos B1-B4

Existen experimentos históricos de retrieval denominados B1-B4.

NO copiar cifras desde memoria del asistente o documentación secundaria
sin comprobar los archivos de resultados reales.

Usarlos principalmente para analizar:

- semantic retrieval;
- contextual scoring;
- configuración de pesos;
- evolución del retrieval.

Distinguir estos experimentos de la campaña final N0/N1.

---

# 30. Reproducibilidad

La memoria debe explicar que existe un repositorio público preparado de
forma limpia.

No describir el historial privado de migración salvo que sea relevante
metodológicamente.

La reproducibilidad debe centrarse en:

- dependencias;
- configuración;
- PostgreSQL;
- pgvector;
- dataset;
- build ROS 2;
- launch;
- configuración experimental;
- seeds;
- escenarios;
- ejecución N0/N1;
- logs;
- análisis.

---

# 31. Seguridad y limitaciones

Documentar explícitamente:

- memoria no sustituye Nav2;
- readiness;
- fallos de infraestructura;
- simulación frente a robot real;
- tamaño limitado del dataset;
- escenarios simulados;
- dependencia de embeddings;
- generalización limitada;
- posibles limitaciones del ground truth contextual.

No convertir una limitación en una conclusión negativa automática.

---

# 32. Amenazas a la validez

Preparar subsección con:

## Validez interna

- estabilidad infraestructura;
- igualdad N0/N1;
- determinismo;
- configuración de escenarios.

## Validez externa

- sólo simulación;
- número de escenarios;
- ausencia de usuarios reales;
- generalización a otros robots/entornos.

## Validez de constructo

- cómo se define "adaptación";
- context_compliance;
- intervention_appropriate;
- calidad del ground truth.

## Validez estadística

- número de repeticiones;
- variabilidad;
- tratamiento de intentos inválidos.

No redactar conclusiones definitivas hasta conocer la campaña.

---

# 33. Regla fundamental contra alucinaciones

Copilot NO debe completar huecos con valores plausibles.

Si desconoce:

- versión;
- parámetro;
- resultado;
- número de tests;
- peso;
- fórmula;
- arquitectura;
- fecha;
- paper;
- DOI;
- métrica;

debe escribir:

[VERIFICAR]

o preguntar/consultar el repositorio.

Nunca inventar un valor para que el texto "quede mejor".

---

# 34. Workflow de escritura

Para cada sección:

1. Leer SPEC_TFM.md.
2. Identificar archivos del repositorio relevantes.
3. Extraer hechos verificables.
4. Separar implementación, validación y planificación.
5. Identificar bibliografía necesaria.
6. Redactar esquema.
7. Redactar sección.
8. Añadir [CITA PENDIENTE] cuando corresponda.
9. Añadir [RESULTADO PENDIENTE] cuando corresponda.
10. Revisar que ninguna afirmación exceda la evidencia.
11. Indicar al final qué puntos necesitan verificación.

---

# 35. Instrucción para generar capítulos

Cuando se solicite redactar un capítulo:

NO generar inmediatamente texto largo.

Primero devolver:

## Evidence used

Archivos del repositorio consultados.

## Proposed outline

Estructura propuesta.

## Missing evidence

Información necesaria que no está disponible.

## Citations needed

Qué afirmaciones requieren bibliografía externa.

Sólo después redactar el capítulo solicitado.

---

# 36. Regla para resultados

El capítulo de resultados debe construirse EXCLUSIVAMENTE desde archivos
generados por la campaña experimental final.

Nunca usar:

- smoke tests;
- pruebas manuales;
- logs de debugging;
- pruebas de integración;
- ejecuciones históricas inválidas;

como si fueran observaciones experimentales válidas.

Cada tabla/figura debe poder trazarse hasta los archivos de resultados.

---

# 37. Regla para conclusiones

Las conclusiones deben responder:

1. ¿Qué se construyó?
2. ¿Qué se validó técnicamente?
3. ¿Qué ocurrió experimentalmente?
4. ¿Qué hipótesis fueron apoyadas o no por los datos?
5. ¿Cuáles son las limitaciones?
6. ¿Qué trabajo futuro queda?

No responder H1/H2/H3 hasta disponer de evidencia experimental.

---

# 38. Estado actual de redacción

Se puede comenzar YA con:

- Introducción;
- motivación;
- definición del problema;
- objetivos;
- pregunta de investigación;
- hipótesis;
- parte del estado del arte;
- arquitectura;
- sistema de memoria;
- diseño N0/N1;
- Behavior Tree;
- metodología experimental prevista;
- reproducibilidad;
- metodología de validación técnica.

Se debe esperar o dejar placeholders en:

- resultados finales N0/N1;
- análisis estadístico final;
- discusión basada en resultados;
- aceptación/rechazo de hipótesis;
- conclusiones experimentales definitivas.

---

# 39. Objetivo de calidad

La memoria final debe permitir que un lector entienda claramente:

1. cuál es el problema;
2. por qué la memoria puede ser útil en navegación asistiva;
3. cuál es el gap;
4. qué sistema se ha construido;
5. cómo funciona la memoria;
6. cómo se integra sin sustituir Nav2;
7. cómo se compara N0 frente a N1;
8. cómo se mide adaptación;
9. qué evidencia técnica existe;
10. qué muestran finalmente los experimentos.

La narrativa central debe mantenerse durante todo el documento:

**contexto → memoria → recuperación → recomendación →
adaptación de navegación → evaluación N0/N1.**

# POLÍTICA DE AUTORÍA Y USO DE IA

La memoria del TFM debe reflejar la redacción, razonamiento y decisiones
de la autora.

Copilot actúa como herramienta de apoyo y NO como autor del documento.

## Copilot SÍ puede

- analizar el repositorio;
- localizar evidencia técnica;
- explicar código a la autora;
- proponer esquemas de secciones;
- detectar información que falta;
- proponer preguntas que la autora debería responder;
- revisar coherencia técnica;
- señalar contradicciones;
- identificar afirmaciones que necesitan referencias;
- revisar ortografía y gramática de texto escrito por la autora;
- sugerir mejoras puntuales de claridad;
- comprobar que una explicación coincide con el código;
- ayudar a organizar tablas y figuras;
- comprobar consistencia terminológica.

## Copilot NO debe

- redactar capítulos completos desde cero;
- generar párrafos para que la autora los presente directamente como propios;
- reescribir automáticamente una sección completa para "hacerla más humana";
- intentar evadir detectores de IA;
- introducir deliberadamente errores, irregularidades o muletillas para
  alterar una puntuación de detección;
- inventar experiencias personales de la autora;
- inventar decisiones de desarrollo;
- inventar resultados;
- inventar bibliografía;
- transformar automáticamente texto generado por IA con el objetivo de
  ocultar su origen.

## Workflow obligatorio

Para cada apartado:

1. Copilot analiza el repositorio y las fuentes disponibles.
2. Copilot devuelve hechos, evidencia y preguntas.
3. La autora redacta un primer borrador con sus propias palabras.
4. Copilot revisa el borrador.
5. Copilot señala problemas concretos sin sustituir automáticamente todo
   el texto.
6. La autora decide y realiza la redacción definitiva.

La prioridad es preservar la autoría intelectual y textual de la autora.