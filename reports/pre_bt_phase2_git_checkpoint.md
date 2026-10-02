# Checkpoint Git reproducible previo a BT Phase 2

Fecha de inspección: 2026-09-29  
Alcance: inspección de solo lectura. No se ejecutaron `git add`, `git commit`, `git restore`, `git reset`, `git checkout`, `git clean` ni borrados.

## 1. Repositorios inspeccionados

La búsqueda bajo `/home/iratxefagoaga/workspace` encontró repositorios Git en:

- `/home/iratxefagoaga/workspace/tfm-robot-memory`
- `/home/iratxefagoaga/workspace/tfm`
- `/home/iratxefagoaga/workspace/ros2_ws/src/turtlebot3`
- `/home/iratxefagoaga/workspace/ros2_ws/src/gazebo_models`

Los dos últimos no están implicados por los paquetes, lanzamientos o informes de este TFM y no se inspeccionaron en detalle. El directorio solicitado `/home/iratxefagoaga/workspace/tfm/ros2` **no es un repositorio Git independiente**: su `git rev-parse --show-toplevel` devuelve `/home/iratxefagoaga/workspace/tfm`.

### 1.1 Repositorio principal TFM

- Directorio inspeccionado: `/home/iratxefagoaga/workspace/tfm/ros2`
- Raíz Git real: `/home/iratxefagoaga/workspace/tfm`
- Rama: `nav2_rebuild`
- HEAD: `7d204073b9d04ee1138478e2be0eb60d430086b5`
- Seguimiento remoto: la rama está un commit por delante de `origin/nav2_rebuild`.
- Estado: **dirty**, sin cambios staged.
- `git log --oneline -10` disponible hasta el historial corto de 8 commits, comenzando en `7d20407 corrección back para dar de alta a usuarios` y con `8347a70 Navegación correcta`.
- `git diff --stat`: 47 archivos tracked, 2378 inserciones y 2893 eliminaciones. Además hay múltiples archivos/directorios untracked.
- `git diff --cached` y `git diff --cached --stat`: sin salida; el índice está vacío.
- `git diff` fue ejecutado y revisado por grupos relevantes. El conjunto completo es muy grande y contiene cambios ajenos a BT Phase 1.

El repositorio superior también incluye cambios de la aplicación (`app/`) y `.vscode/`; no deben mezclarse con los commits ROS del TFM sin una auditoría propia.

### 1.2 Repositorio de memoria

- Raíz Git: `/home/iratxefagoaga/workspace/tfm-robot-memory`
- Rama: `main`
- HEAD: `ff4da5df476f54ccba0b19e7f7cf5f1b57f39c6f`
- Seguimiento remoto: actualizado respecto de `origin/main`.
- Estado: **dirty**, sin cambios staged.
- `git log --oneline -10`: sólo existe `ff4da5d Commit inicial incluye experimentos iniciales y configuración`.
- `git diff --stat`: 6 archivos tracked, 25 inserciones y 8 eliminaciones.
- `git diff --cached` y `git diff --cached --stat`: sin salida; el índice está vacío.

Cambios tracked observados:

- `database/init.sql`: añade `episodic_embedding VECTOR(1024)`.
- `experiments/README.md`: documenta infraestructura de Fase 4.
- `experiments/optimize_context_weights.py`: renombra el CSV de salida B3.
- `experiments/results/Nuevo Documento de texto.txt`: cambio de terminadores de línea sobre una captura de consulta.
- Dos ficheros `Zone.Identifier` del dataset aparecen borrados.

Hay además documentación, escenarios, configuraciones, scripts y resultados untracked.

## 2. Clasificación de cambios

La clasificación siguiente usa los informes `blocker1_design.md`, `blocker1_validation.md`, `behavior_tree_architecture_design.md`, `bt_phase1_implementation.md`, `bt_phase1_validation.md` y `final_readiness_audit.md`, junto con el diff real. Cuando el historial no permite demostrar el origen, se marca explícitamente como ambiguo.

### A. Cambios anteriores ya validados del TFM — confirmados por documentación, pero actualmente no versionados

En el repositorio `tfm`:

- Cambios tracked de infraestructura Nav2/Gazebo/robot/mapa: `ros2/src/wheelchair_navigation/config/nav2_params.yaml`, `launch/navigation.launch.py`, `maps/apartment.pgm`, `maps/apartment.yaml`; `ros2/src/wheelchair_gazebo/worlds/apartment.world` y modelos; `wheelchair_description/urdf/*`; y componentes de `wheelchair_bringup`.
- Archivos untracked de baseline/fases previas: `baseline.launch.py`, `baseline_experiment.launch.py`, `memory_on.launch.py`, `memory_on_experiment.launch.py`, `baseline_runner.py` y las interfaces `MemoryQuery.srv`, `NavigationRecommendation.srv`.
- Paquete untracked `src/wheelchair_memory/`, salvo las copias y `__pycache__` que se clasifican abajo como temporales.

Los informes de fases anteriores acreditan que una parte de estos cambios fue implementada/validada antes de BT Phase 1. Sin embargo, el working tree no contiene una delimitación Git previa (no había commit/stage), por lo que no se puede convertir toda esta lista en una atribución individual inequívoca únicamente desde Git.

En `tfm-robot-memory`:

- `SPEC.md`, `AGENT.md`, `docs/`, la infraestructura de escenarios/configuración/scripts y varios informes corresponden documentalmente a las fases 0–5, Blocker 1 y Blocker 2.
- La adición de `episodic_embedding` y el cambio del nombre de salida B3 son cambios de diseño/experimentos anteriores a BT Phase 1 según su contenido, no cambios BT.

### B. Blocker 1 — atribución confirmada

El informe de diseño y validación de Blocker 1 identifica este conjunto funcional:

- `tfm/ros2/src/wheelchair_memory/wheelchair_memory/navigation_adapter.py`
- `tfm/ros2/src/wheelchair_bringup/launch/memory_on_experiment.launch.py`
- `tfm/ros2/src/wheelchair_bringup/scripts/baseline_runner.py`
- `tfm-robot-memory/experiments/scripts/run_navigation_scenario.py`
- documentación de Blocker 1: `tfm-robot-memory/reports/blocker1_design.md`, `reports/blocker1_validation.md`, y la entrada pertinente de `reports/implementation_log.md`.

La comparación de `navigation_adapter.py` con `navigation_adapter.py.before_waypoint` confirma una implementación posterior que incorpora una secuencia waypoint → meta final, `strategy_waypoint_offsets`, trazabilidad de estrategia/waypoint y la política de no enviar la meta final si el waypoint no alcanza `SUCCEEDED`.

No deben entrar en este commit las copias `*.bak`, `*.before_waypoint`, `setup.py.save` o `__pycache__`.

### C. Behavior Tree Phase 1 — atribución confirmada

BT Phase 1 creó únicamente el siguiente paquete bajo el repositorio `tfm`:

- `ros2/src/wheelchair_assistive_bt/CMakeLists.txt`
- `ros2/src/wheelchair_assistive_bt/package.xml`
- `ros2/src/wheelchair_assistive_bt/src/assistive_bt_orchestrator.cpp`
- `ros2/src/wheelchair_assistive_bt/behavior_trees/n0_assistive_navigation.xml`
- `ros2/src/wheelchair_assistive_bt/launch/bt_n0_smoke.launch.py`

El único archivo adicional detectado dentro del paquete es generado e ignorado:

- `ros2/src/wheelchair_assistive_bt/launch/__pycache__/bt_n0_smoke.launch.cpython-312.pyc`

No hay evidencia de que BT Phase 1 modificara archivos fuera de `src/wheelchair_assistive_bt/`. En particular, no modificó `navigation_adapter.py`, `memory_node.py`, `navigation_memory_node.py`, Nav2, el mundo, el mapa, sensores, interfaces, escenarios o datasets. Estos archivos ya estaban modificados/untracked antes de la creación del paquete BT, como también dejan constancia los informes BT Phase 1.

### D. Documentación asociada

Documentación confirmada de BT Phase 1 en `tfm-robot-memory`:

- `reports/bt_phase1_implementation.md`
- `reports/bt_phase1_validation.md`

Documentación de análisis/diseño previa, no implementación BT Phase 1:

- `reports/behavior_tree_architecture_design.md`

Documentación Blocker 1:

- `reports/blocker1_design.md`
- `reports/blocker1_validation.md`

`reports/pre_bt_phase2_git_checkpoint.md` es el informe de este checkpoint y debería revisarse como documentación de control antes de decidir si se versiona.

Los directorios `docs/` y `reports/` son untracked en el repositorio de memoria. No es seguro tratarlos como un único cambio atómico: contienen documentación de múltiples fases y resultados de auditorías distintas.

### E. Temporales, generados y resultados

No se eliminó nada. Se detectaron los siguientes grupos:

- ROS generados: `ros2/build/`, `ros2/install/`, `ros2/log/`; ya están ignorados por el `.gitignore` del repositorio `tfm`.
- Python generado: `__pycache__/` y `*.pyc` dentro de `wheelchair_memory`, `wheelchair_assistive_bt` y `experiments`; están ignorados por las reglas existentes.
- Copias de trabajo no versionables sin justificación: `navigation_adapter.py.bak`, `navigation_adapter.py.before_waypoint`, `navigation_memory_node.py.bak`, `memory_node.py.bak`, `setup.py.save`, `bringup.launch.py.bak`, `nav2_params.yaml.bak`.
- Copia de seguridad de árbol completo: `ros2_backup_navigation_20260826_145914/`; no debe confirmarse como parte del código fuente.
- Metadatos Windows ADS: todos los nombres con `Zone.Identifier`, incluyendo variantes repetidas y `lidar_link:`. No son fuente ni resultados científicos.
- Resultados no rastreados en memoria: `experiments/results/baseline_navigation_results.csv`, `memory_on_navigation_results.csv`, `phase4/`, `phase5/`, `statistical_analysis/`. Deben conservarse ahora; su contenido debe revisarse y decidirse explícitamente si constituye evidencia científica inmutable a versionar o output reproducible que debe almacenarse fuera del repositorio. No se clasifican como output BT Phase 1: sus smoke tests se registraron en `/tmp` y no en estos directorios.
- El archivo tracked `experiments/results/Nuevo Documento de texto.txt` parece una captura manual de salida ROS con cambios de finales de línea; no es un resultado experimental estructurado.
- No se detectaron artefactos `/tmp` persistentes en los repositorios. PostgreSQL runtime, virtual environments y caches de modelos no aparecieron como cambios Git, pero deben seguir excluidos.

### F. Recomendaciones para `.gitignore` (no aplicadas)

En `tfm/.gitignore`, las reglas para `build/`, `install/`, `log/` y `__pycache__/` ya cubren los artefactos ROS/Python observados. Tras revisión humana, se recomienda añadir reglas específicas para:

```gitignore
# Local backups and editor/Windows metadata
*.bak
*.save
*.before_waypoint
*:Zone.Identifier
ros2_backup_*/
```

No se recomienda ignorar globalmente `*.csv`, `docs/`, `reports/`, `experiments/scenarios/` ni `experiments/configs/`: pueden ser evidencia o configuración reproducible del TFM. Para resultados/logs, decidir primero una política: versionar únicamente CSV/manifiestos finales inmutables y excluir logs transitorios, o publicar ambos como artefactos versionados con metadatos de ejecución.

En `tfm-robot-memory/.gitignore`, ya se cubren `.venv/`, `__pycache__/`, `*.py[cod]`, modelos, checkpoints, `build/`, `install/`, `log/` y `postgres-data/`. Recomendaciones condicionales:

```gitignore
# Only if runtime logs are not retained as evidence
experiments/results/**/*.log
# Windows metadata
*:Zone.Identifier
```

No añadir `experiments/results/` completo sin decidir la política de trazabilidad experimental, porque contendría resultados que pueden ser evidencia del TFM.

### G. Cambios de origen incierto o no separables aún

- Los cambios tracked masivos en `.vscode/` y `app/` pertenecen al repositorio superior pero están fuera del alcance ROS/BT; su origen no se determinó.
- Los cambios de mundo, modelo, URDF, mapa, Nav2 y bringup están documentados como trabajo anterior del TFM, pero no se puede asignar cada línea a una fase concreta con el historial actual.
- `wheelchair_memory` e interfaces son untracked como bloques completos. Algunos archivos son necesarios para Blocker 1 y fases anteriores, pero no hay una base Git contra la que separar por líneas las fases 0–3 y Blocker 1.
- `database/init.sql` contiene un cambio de esquema episódico que no está relacionado con BT Phase 1 ni con Blocker 1; requiere revisión independiente antes de confirmarlo.
- Los resultados untracked de fases 4/5/análisis estadístico carecen de una clasificación Git previa. Preservarlos, pero no confirmar ni ignorar masivamente hasta validar su procedencia y su política de publicación.
- La conversión de terminadores de línea genera ruido y `git diff --check` mostró trailing whitespace en varios archivos, especialmente `.vscode`, app y material de experimentos. No es atribuible a BT Phase 1.

## 3. Cambios en world/map/Nav2/config/dataset/resultados

- Mundo/robot/mapa/Nav2/config: existen modificaciones locales en `wheelchair_gazebo`, `wheelchair_description`, `wheelchair_navigation` y `wheelchair_bringup`. BT Phase 1 no las modificó. Antes de cualquier commit deben aislarse como trabajo validado anterior o como cambios ambiguos.
- Dataset: los CSV de seed/query no cambiaron como contenido tracked; se borraron dos metadatos `Zone.Identifier` y existen dos metadatos equivalentes untracked. No se debe versionar ese ruido de metadatos.
- Base de datos: `database/init.sql` modifica el esquema añadiendo un embedding episódico; no corresponde a BT Phase 1.
- Resultados: existen CSV/directorios untracked de navegación y experimentos; no se sobrescribieron ni se generaron desde BT Phase 1. El smoke BT usó ejecución temporal, no una campaña experimental final.

## 4. Secuencia de commits propuesta, después de revisión humana

La secuencia es una propuesta; no se ejecutó ningún `git add` ni commit. Dado que el repositorio `tfm` tiene cambios no relacionados, cada paso debe hacerse con listas de archivos explícitas y sólo tras confirmar el diff de esa lista.

### Commit 1

- REPOSITORY: `/home/iratxefagoaga/workspace/tfm`
- FILES: interfaces `MemoryQuery.srv`, `NavigationRecommendation.srv`; paquete `wheelchair_memory` excluyendo copias/pycache; launch/runners de baseline y Memory ON; cambios mínimos de CMake/package que sean necesarios para esos ejecutables.
- PURPOSE: preservar los cambios funcionales previos de memoria, interfaces y baseline como una unidad revisable.
- COMMIT MESSAGE: `feat(memory): add retrieval and navigation integration services`
- LIMIT: no incluir aún si los cambios de infraestructura Nav2/Gazebo no han sido revisados y atribuibles.

### Commit 2

- REPOSITORIES: `/home/iratxefagoaga/workspace/tfm` y `/home/iratxefagoaga/workspace/tfm-robot-memory` (dos commits coordinados, uno por repositorio).
- FILES (tfm): `navigation_adapter.py`, `memory_on_experiment.launch.py`, `baseline_runner.py`.
- FILES (tfm-robot-memory): `experiments/scripts/run_navigation_scenario.py`.
- PURPOSE: aplicar la recomendación de estrategia mediante un waypoint Nav2 y conservar el esquema de resultados comparable.
- COMMIT MESSAGES:
  - `fix(navigation): apply memory strategy waypoint through Nav2`
  - `feat(experiments): record memory waypoint navigation outcomes`

### Commit 3

- REPOSITORY: `/home/iratxefagoaga/workspace/tfm-robot-memory`
- FILES: `reports/blocker1_design.md`, `reports/blocker1_validation.md` y, si su diff se limita a Blocker 1, la sección verificable de `reports/implementation_log.md`.
- PURPOSE: documentar diseño, política de fallo y evidencia de Blocker 1.
- COMMIT MESSAGE: `docs(navigation): document memory waypoint blocker validation`

### Commit 4

- REPOSITORY: `/home/iratxefagoaga/workspace/tfm`
- FILES: exactamente los cinco archivos fuente del paquete `src/wheelchair_assistive_bt/` enumerados en la sección C; excluir `__pycache__`.
- PURPOSE: incorporar la orquestación N0 explícita con BehaviorTree.CPP sin tocar memoria ni Nav2 interno.
- COMMIT MESSAGE: `feat(bt): add memory-off assistive behavior tree`

### Commit 5

- REPOSITORY: `/home/iratxefagoaga/workspace/tfm-robot-memory`
- FILES: `reports/behavior_tree_architecture_design.md`, `reports/bt_phase1_implementation.md`, `reports/bt_phase1_validation.md`, y opcionalmente este checkpoint después de su revisión.
- PURPOSE: mantener la trazabilidad del diseño y de la validación BT Phase 1.
- COMMIT MESSAGE: `docs(bt): document phase 1 design and validation`

Los cambios de world/map/Nav2/robot deberían formar commits independientes sólo después de una revisión de sus diffs y relación exacta con la Fase 1 previa; no se recomienda unirlos a Blocker 1 ni BT Phase 1.

## 5. Comandos exactos recomendados después de la revisión

Estos comandos son recomendaciones futuras; **no se han ejecutado**:

```bash
# Reinspección antes de seleccionar nada
cd /home/iratxefagoaga/workspace/tfm
git status --short
git diff -- ros2/src/wheelchair_assistive_bt
git diff --no-index /dev/null ros2/src/wheelchair_assistive_bt/src/assistive_bt_orchestrator.cpp

# Commit BT Phase 1 solamente, tras revisar cada diff
git add ros2/src/wheelchair_assistive_bt/CMakeLists.txt \
        ros2/src/wheelchair_assistive_bt/package.xml \
        ros2/src/wheelchair_assistive_bt/src/assistive_bt_orchestrator.cpp \
        ros2/src/wheelchair_assistive_bt/behavior_trees/n0_assistive_navigation.xml \
        ros2/src/wheelchair_assistive_bt/launch/bt_n0_smoke.launch.py
git diff --cached --check
git diff --cached
git commit -m "feat(bt): add memory-off assistive behavior tree"

# Commit documentación BT en el repositorio de memoria, tras revisar el contenido
cd /home/iratxefagoaga/workspace/tfm-robot-memory
git add reports/behavior_tree_architecture_design.md \
        reports/bt_phase1_implementation.md \
        reports/bt_phase1_validation.md \
        reports/pre_bt_phase2_git_checkpoint.md
git diff --cached --check
git diff --cached
git commit -m "docs(bt): document phase 1 design and validation"

# Sólo tras revisar y separar Blocker 1 de fases anteriores
cd /home/iratxefagoaga/workspace/tfm
git diff -- ros2/src/wheelchair_memory/wheelchair_memory/navigation_adapter.py \
             ros2/src/wheelchair_bringup/launch/memory_on_experiment.launch.py \
             ros2/src/wheelchair_bringup/scripts/baseline_runner.py
```

No ejecutar comandos de exclusión, limpieza o restauración (`git clean`, `git restore`, `git reset`, `git checkout`) hasta que el propietario del repositorio apruebe una lista explícita de artefactos temporales.

## 6. Conclusión del checkpoint

BT Phase 1 está delimitado de forma segura: el nuevo paquete `src/wheelchair_assistive_bt/` y sus dos informes. El resto del working tree no debe atribuirse automáticamente a BT Phase 1. El checkpoint no es todavía un estado Git reproducible limpio: ambos repositorios están dirty, no hay cambios staged y el repositorio principal agrupa cambios de ROS, simulación, app y metadatos Windows. La siguiente acción segura es una revisión humana de los grupos propuestos y, únicamente después, staging selectivo por rutas explícitas.