# CURRENT status notice

Este documento conserva debajo una instantánea histórica del estado previo.
No describe por sí sola la validación vigente del monorepo.
El cierre actual es **PHASE G ENGINEERING VALIDATION CLOSED WITH KNOWN LIMITATION**:
Nav2/lifecycle/discovery tiene causa UNKNOWN y production fix NONE;
N0/N1 integrados post-fix siguen NOT VALIDATED.
Ver [README actual](../../README.md#project-status).
El registro interno de migración y seguridad se conserva como evidencia privada.
La campaña Casa/Mall/Aeropuerto permanece PLANNED.

---

# Estado actual

Actualizado el 2026-09-22 tras Fase 3.

- PostgreSQL/pgvector: FUNCIONA; 50 memorias y vectores de 1024 dimensiones verificados.
- MemoryQuery: FUNCIONA; M001 recuperada como primera memoria en la consulta validada.
- NavigationRecommendation: FUNCIONA; devuelve west, avoidance y clearance desde M001.
- Gazebo, bridge, robot y mapa: FUNCIONAN. Las transformaciones del URDF se alinearon con la geometría física del SDF; base_link -> lidar_link es (0.28, 0, 0.72).
- Nav2: FUNCIONA. Lifecycle activo y NavigateToPose validado con SUCCEEDED al objetivo (2.5, -3.0).
- Baseline MEMORY OFF: FUNCIONA. Registra estado, tiempo, distancia y replanning; muestra de aceptación: 2.370 s, 0.263 m, 2 replannings.
- Memory ON: FUNCIONA. La prueba integrada recuperó M001, generó strategy=west, esperó bt_navigator active y terminó NavigateToPose con SUCCEEDED.
- Registro Memory ON: FUNCIONA. CSV con query, contexto, IDs, scores, estrategia, waypoint y resultado Nav2.
- Estabilidad: FUNCIONA en la repetición final. La memoria se calienta antes del ciclo de vida de Nav2 para evitar pérdida de heartbeats durante carga de embeddings.
- Efecto científico de un waypoint oeste seguro frente al baseline: NO PROBADO. La ejecución exitosa reutiliza el endpoint seguro del baseline y sólo valida la integración técnica.
- Tests: 6 tests, 0 fallos, 2 omitidos para los paquetes validados.

- Fase 4: FUNCIONA. Existe infraestructura declarativa para ejecutar N0 y N1 sobre S001 con misma pose, meta y contexto; la ejecución de aceptación phase4_acceptance_002 terminó SUCCEEDED en ambas condiciones. No se ha realizado análisis comparativo.

- Fase 5: FUNCIONA. El automatizador acepta escenario, condición y número de repeticiones, empareja run_id entre Memory OFF/ON y persiste CSV consolidado, crudo y manifiesto. Muestra S001 phase5_final_001: ambos SUCCEEDED; Memory ON registró M001|M046|M015|M007|M009 y strategy=west. Ampliación documentada en reports/phase5_automation.md; sin análisis comparativo.