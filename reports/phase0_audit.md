# Auditoria fase 0 - estado actual

Fecha: 2026-09-22. Auditoria de solo lectura; no se modifico codigo. Estados: **FUNCIONA** (verificado), **NO FUNCIONA** (fallo observado), **NO PROBADO** (sin ejecucion integrada) y **DESCONOCIDO** (sin evidencia).

## 1. Arquitectura actual

```text
PostgreSQL + pgvector <- MemoryService (Qwen3 embeddings) <- /memory/query <- memory_node
                                                                  ^
navigation_memory_adapter -- /navigate_to_pose --> Nav2 --> smoother --> /cmd_vel --> Gazebo
                                                                  ^
Gazebo bridge: /clock, /odom, /tf, /joint_states, /scan -> scan_frame_fixer -> /scan_fixed
navigation_memory_node expone /memory/navigation_recommendation, pero el adapter no la consume.
```

El diseno declarado es Memory -> Recommendation -> Adapter -> Nav2. El adapter real consulta directamente `/memory/query` y decide con coincidencias de texto.

## 2. Componentes

| Componente | Estado | Evidencia |
|---|---|---|
| ROS 2 Jazzy / workspace | FUNCIONA | Python de build `/usr/bin/python3`; paquetes auditados resuelven desde `install/`. |
| Interfaces MemoryQuery y NavigationRecommendation | FUNCIONA | `ros2 interface show` mostro definiciones generadas. |
| wheelchair_memory | FUNCIONA (instalacion/parseo) | Ejecutables instalados; modulos validos con `py_compile`. Runtime: NO PROBADO. |
| PostgreSQL | NO FUNCIONA | `pg_isready` a localhost:5433 devolvio `no response`. |
| Contenedor pgvector | NO FUNCIONA | `docker ps` no mostro contenedores. |
| pgvector | DESCONOCIDO | Compose e inicializacion presentes, sin servidor para verificar extension/esquema. |
| Qwen/Qwen3-Embedding-0.6B | NO PROBADO | Configurado CPU, dimension 1024; no se cargo en auditoria. |
| B1/B2/B3/B4 | NO PROBADO | Scripts y CSV existentes; no reproducidos con la BD actual. B3 usa 0.90/0.10; B4 registra peso episodico 0.0. |
| Nav2 / navigation | FUNCIONA (instalacion/launch estatico) | Paquetes instalados y launch carga; runtime NO PROBADO. |
| Grafo ROS, lifecycle y actions | NO PROBADO | `ros2 node/service/action/lifecycle` no devolvieron entidades activas. |
| Bringup | FUNCIONA (instalacion/launch estatico) | scan_frame_fixer instalado; launch carga. Simulacion NO PROBADA. |
| Gazebo / ros_gz | FUNCIONA (instalacion) | Paquetes en `/opt/ros/jazzy`, mundo/modelo presentes. Runtime NO PROBADO. |
| Descripcion robot | FUNCIONA | Xacro genero URDF no vacio. |
| wheelchair_gazebo | NO PROBADO | No se verificaron spawn, sensores ni TF. |
| wheelchair_vla | NO FUNCIONA como componente | Esqueleto sin aplicacion, ejecutables ni metadatos definitivos. |

## 3. Flujo de datos

1. memory_node instancia MemoryService y expone /memory/query.
2. El servicio genera embedding, busca por coseno en memory_episodes, filtra user_id y reordena por 0.9 semantic + 0.1 context.
3. navigation_memory_node puede crear west/central/alternative/direct por /memory/navigation_recommendation.
4. El adapter evita ese servicio, usa un waypoint fijo y envia /navigate_to_pose.
5. Nav2 consume /scan_fixed para AMCL/costmaps; Gazebo recibe /cmd_vel mediante bridge.

## 4. Problemas y riesgos

1. **Bloqueante:** BD inaccesible; no se puede validar retrieval ni nodos de memoria.
2. **Esquema desalineado:** MemoryService.store_memory() usa episodic_embedding; database/init.sql no lo declara.
3. **Integracion diferente a la declarada:** Recommendation no alimenta al adapter.
4. **Baseline ausente:** bringup siempre lanza memoria/adapter y el adapter envia goal automatico.
5. No hay evidencia actual de compute_path_to_pose, navigate_to_pose, lifecycle activo o navegacion segura.
6. package.xml de navigation/bringup no declara todas las dependencias usadas por launch.
7. CSV B1-B4 carecen de metadata de reproducibilidad; no hay registro navegacion -> memoria.
8. Workspaces sucios con cambios preexistentes; no se alteraron.

## 5. Archivos relevantes

