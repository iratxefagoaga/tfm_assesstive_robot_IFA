# Optimización de la Asistencia Robótica mediante Sistemas de Memoria de Largo Plazo Basados en RAG Multimodal y Bases de Datos Vectoriales

TFM sobre memoria personalizada y contextual de largo plazo para navegación
robótica asistiva en simulación. Integra ROS 2, Nav2, Gazebo,
PostgreSQL/pgvector, retrieval semántico/contextual y Behavior Trees.

La implementación actual recupera experiencias textuales y contexto.
El título expresa el marco de investigación; no se ha desarrollado un nuevo
VLA ni un foundation model. No se utiliza hardware físico.

## Research Question

¿El uso de una memoria personalizada y contextual mejora la adaptación de la
navegación de un robot asistivo respecto a un sistema equivalente que no
utiliza memoria?

- **N0 / MEMORY_OFF:** navegación sin intervención de memoria.
- **N1 / MEMORY_ON:** navegación con recuperación y recomendación contextual.

La comparación científica final está pendiente. Las validaciones de ingeniería
y los resultados de retrieval disponibles no demuestran todavía esa mejora.

## Architecture

~~~text
User → Context → Memory Retrieval → Navigation Recommendation
     → Assistive BT → Nav2 → Robot Simulation
~~~

La memoria recomienda una estrategia o waypoint. Nav2 conserva la
responsabilidad de planificación, control, evitación de obstáculos y ejecución.
La memoria no envía órdenes de velocidad directamente al robot.

Hay una única implementación del backend en `memory/`. El paquete ROS
`wheelchair_memory` integra ese backend mediante servicios, sin duplicarlo.

## Repository Structure

~~~text
memory/                   Backend Python instalable, embedding y retrieval
database/                 Esquema SQL y compose separado de memoria
experiments/
  data/                   Seed y queries de retrieval
  configs/                Configuración experimental existente
  scenarios/              Escenarios existentes; no campaña final
  scripts/                Ejecución/análisis
  results/                B1–B4 y evidencia histórica
docs/memory/              Documentación de memoria
reports/                  Informes científicos y de ingeniería seleccionados
scripts/memory/           Carga, fingerprint y utilidades
ros2/src/                 Paquetes ROS
requirements-memory.txt   Runtime Python
requirements-dev.txt      Herramientas de tests
~~~

El prototipo auxiliar, los backups y los registros privados de migración
están excluidos. La ruta principal del proyecto es memoria/BT/Nav2.

## Validated Environment

Entorno utilizado: Windows 11 con WSL2, Ubuntu 24.04.4 LTS, ROS 2 Jazzy en
`/opt/ros/jazzy` y Python 3.12.3. Gazebo Sim reporta 8.11.0;
`ros_gz_sim`/`ros_gz_bridge` 1.0.22. La validación de memoria utilizó
PostgreSQL 16.15 y pgvector 0.8.6.

Estas versiones describen el entorno observado. No se declara soporte probado
para otros sistemas. La inestabilidad Nav2 conocida se describe en
[Project Status](#project-status).

## Installation and Dependencies

Ejecutar los comandos desde la raíz del monorepo, salvo que se indique `ros2/`.
Se requieren ROS 2 Jazzy instalado, colcon/rosdep, Docker Compose v2 y soporte
`venv` de Python 3.12.

Separación de dependencias:

| Ámbito | Fuente |
| --- | --- |
| ROS | `ros2/src/*/package.xml`, rosdep y paquetes del sistema |
| Backend de memoria | [requirements-memory.txt](requirements-memory.txt) y [constraints Linux CPU](requirements-memory-linux-cpu.constraints.txt) |
| Desarrollo | [requirements-dev.txt](requirements-dev.txt) |
| Backend instalable | [memory/pyproject.toml](memory/pyproject.toml) |

No instalar ROS mediante los requirements de memoria. El runtime validado usa
CPU; no requiere instalar CUDA.

### Python Memory Runtime

En una terminal sin overlay ROS cargado:

~~~bash
/usr/bin/python3 -m venv .venv-memory
.venv-memory/bin/python -m pip install setuptools==78.1.0
.venv-memory/bin/python -m pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
.venv-memory/bin/python -m pip install -r requirements-memory.txt -c requirements-memory-linux-cpu.constraints.txt
.venv-memory/bin/python -m pip install --no-deps --no-build-isolation -e ./memory
.venv-memory/bin/python -m pip install -r requirements-dev.txt
.venv-memory/bin/python -m pip check
~~~

El paquete instalado se llama `tfm-memory` y se importa como `memory`.
No necesita el repositorio histórico ni modificaciones manuales de `sys.path`.
Ver [runtime Linux](docs/memory/linux-runtime.md) para configuración y arranque ROS.

### PostgreSQL / pgvector

El compose real es [database/docker-compose.memory.yml](database/docker-compose.memory.yml).
El esquema es [database/init.sql](database/init.sql); el seed está en
[experiments/data/memory_seed.csv](experiments/data/memory_seed.csv).

La configuración requiere `MEMORY_DB_HOST`, `MEMORY_DB_PORT`,
`MEMORY_DB_NAME`, `MEMORY_DB_USER` y `MEMORY_DB_PASSWORD`.
No hay credenciales públicas ni contraseña de desarrollo por defecto.
El `.env.example` raíz incluye los placeholders de memoria. La
[guía de base de datos](docs/memory/database.md) describe la configuración
privada y el procedimiento de inicialización de una **base nueva**,
separado de la base experimental congelada.

El compose no monta automáticamente `init.sql`. Tampoco debe ejecutarse el
loader directo con su ruta de seed actual: la guía usa sus funciones existentes
con la ruta explícita correcta. No reinicializar ni regenerar embeddings de la
base congelada para validar el sistema.

### Database Integrity

El mecanismo actual es `canonical_memory_fingerprint_v2`.
Con el entorno privado cargado, este comando realiza únicamente lectura:

~~~bash
.venv-memory/bin/python -m scripts.memory.fingerprint_memory
~~~

Reporta número de filas y hashes separados de contenido lógico y embeddings.
Las verificaciones registradas observaron 50 memorias y huellas v2 estables.
Medir antes y después de una validación; no asumir ese número sin comprobarlo.

El fingerprint histórico anterior se conserva como evidencia, pero su método
exacto no pudo recuperarse. **No comparar numéricamente hashes de ambos métodos.**

### ROS 2 Build

Usar el Python del sistema para colcon/rosidl, separado del runtime de memoria:

~~~bash
deactivate 2>/dev/null || true
source /opt/ros/jazzy/setup.bash
test "$(command -v python3)" = /usr/bin/python3
rosdep install --from-paths ros2/src --ignore-src -r -y --rosdistro jazzy
cd ros2
colcon list
MAKEFLAGS='-j1 -l1' CMAKE_BUILD_PARALLEL_LEVEL=1 colcon build --symlink-install --executor sequential
source install/setup.bash
~~~

No borrar `src/` ni mezclar el intérprete de `.venv-memory` con el build.
MAKEFLAGS limita también el paralelismo que colcon pasa a Make; el executor
secuencial sólo limita el número de paquetes simultáneos.

## ROS Packages

| Paquete | Responsabilidad actual |
| --- | --- |
| `wheelchair_description` | URDF/Xacro y descripción del robot. |
| `wheelchair_gazebo` | Modelos y mundos de simulación. |
| `wheelchair_navigation` | Configuración, mapa y launch Nav2. |
| `wheelchair_bringup` | Coordinación de simulación, bridge, TF y scan. |
| `wheelchair_interfaces` | Interfaces MemoryQuery y NavigationRecommendation. |
| `wheelchair_memory` | Integración ROS del backend de memoria y recomendación. |
| `wheelchair_assistive_bt` | BT asistivo, contratos, logging y supervisión de readiness. |

El candidato contiene siete paquetes ROS completos. Los directorios
`wheelchair_vla` y `wheelchair_api` sólo conservan tests de plantilla,
sin metadata de paquete; colcon no los descubre como paquetes.

## Memory Services

- `/memory/query`, tipo `wheelchair_interfaces/srv/MemoryQuery`:
  recibe query, usuario, ubicación, tarea, destino y k; devuelve memorias,
  contenido y puntuaciones.
- `/memory/navigation_recommendation`, tipo
  `wheelchair_interfaces/srv/NavigationRecommendation`:
  devuelve strategy, source_memory, reason, avoid_obstacle y prefer_clearance.

Arranque mínimo sin Gazebo: [runtime Linux](docs/memory/linux-runtime.md#servicios-ros-sin-simulacion).

**Engineering validation example**, con la base validada y servicios activos:

~~~bash
source /opt/ros/jazzy/setup.bash
source ros2/install/setup.bash
ros2 service call /memory/query wheelchair_interfaces/srv/MemoryQuery "{query: 'navegar evitando la mesa', user_id: 'U01', location: 'salon', task: 'navegacion', goal: 'dormitorio', k: 3}"
ros2 service call /memory/navigation_recommendation wheelchair_interfaces/srv/NavigationRecommendation "{query: 'navegar evitando la mesa', user_id: 'U01', location: 'salon', task: 'navegacion', goal: 'dormitorio', k: 3}"
~~~

Retrieval validado: **M001, M046, M002**. Recomendación: **M001 / west**.
Es evidencia de ingeniería, no un resultado científico de eficacia N0/N1.

## Behavior Trees: N0 and N1

[N0 XML](ros2/src/wheelchair_assistive_bt/behavior_trees/n0_assistive_navigation.xml):
`MemoryOffNavigation` → `WaitForNav2Active` → `NavigateNav2(final_goal)`
→ `FinalizeExperiment`. No hace consultas a memoria.

[N1 XML](ros2/src/wheelchair_assistive_bt/behavior_trees/n1_memory_strategy_navigation.xml):
`QueryMemory` → `GetNavigationRecommendation` → `ResolveStrategyWaypoint`
→ readiness → waypoint opcional → readiness → final goal → finalize.

Si la estrategia es direct o no aplicable, se navega al final sin waypoint.
Un waypoint fallido deja el final en `NOT_SENT`. Una resolución inválida
falla antes de enviar objetivos.
En el caso west con offset (-0.25, 0.0) y final (2.5, -3.0),
el waypoint es (2.25, -3.0), conservando el yaw del final.

### Readiness

La barrera inicial y la revalidación fresca antes de cada objetivo utilizan
[la lista canónica](ros2/src/wheelchair_navigation/config/required_nav2_nodes.txt):
map_server, amcl, planner_server, controller_server, behavior_server,
bt_navigator, waypoint_follower y velocity_smoother.

El contrato es **fail closed**: una invalidación observada bloquea el envío,
con `NOT_SENT` y `failure_stage=readiness`.
En la validación registrada se bloquearon dos goals tras FAIL y se enviaron
cero después de FAIL.

La revalidación reduce ese riesgo, pero no elimina la carrera entre observar
ACTIVE y una caída inmediatamente posterior. No implica disponibilidad o
seguridad absoluta de Nav2.

### Smoke Commands for Future Validation

Estos comandos corresponden a los launches actuales. **N0/N1 integrados
post-fix siguen NOT VALIDATED**; no se ejecutaron en Fase H.
Usar un stack limpio y no arrancar servicios duplicados junto al launch N1.
Cada launch coordina sus componentes; enviar Ctrl+C una vez al proceso launch
propietario y comprobar el cierre antes de otro run.

N0, desde la raíz y sin venv de memoria:

~~~bash
deactivate 2>/dev/null || true
source /opt/ros/jazzy/setup.bash
source ros2/install/setup.bash
RUN_ID="n0_$(date -u +%Y%m%dT%H%M%S)_$$"
ros2 launch wheelchair_assistive_bt bt_n0_smoke.launch.py run_id:="$RUN_ID" result_csv:="/tmp/$RUN_ID.csv" initial_x:=2.0 initial_y:=-3.0 goal_x:=2.5 goal_y:=-3.0
~~~

N1, desde la raíz con configuración privada y runtime de memoria:

~~~bash
source /opt/ros/jazzy/setup.bash
source ros2/install/setup.bash
source .venv-memory/bin/activate
set -a
source .env.memory
set +a
export PGOPTIONS='-c default_transaction_read_only=on'
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false
RUN_ID="n1_$(date -u +%Y%m%dT%H%M%S)_$$"
ros2 launch wheelchair_assistive_bt bt_n1_phase3_smoke.launch.py run_id:="$RUN_ID" result_csv:="/tmp/$RUN_ID.csv" query:="navegar evitando la mesa" user_id:=U01 location:=salon task:=navegacion goal_label:=dormitorio k:=3 strategy_waypoint_offsets:=west:-0.25:0.0 initial_x:=2.0 initial_y:=-3.0 goal_x:=2.5 goal_y:=-3.0
~~~

La estrategia está habilitada por defecto en este launch. No existe un
argumento launch `strategy_waypoint_enabled`. No ajustar timeouts para obtener PASS.

## Common Experimental Logging

[N0/N1 usan el mismo helper](ros2/src/wheelchair_assistive_bt/include/wheelchair_assistive_bt/common_experiment_logging.hpp):
**36 columnas**, con `memory_latency_ms` al final, header común y una fila final por run iniciado que llega a
finalización, tanto exitoso como fallido. Los IDs deben ser únicos; los ejemplos
los generan explícitamente y escriben sólo en `/tmp`.
Un fallo antes de iniciar el orquestador no debe inventar una fila.

- `navigation_time_s`: desde el primer envío NavigateToPose hasta finalizar
  el run; N1 incluye waypoint, intervalo intermedio y final.
- `distance_m`: suma euclídea de posiciones consecutivas de `/odom` durante
  `navigation_active=true`.
- `replanning_count`: mensajes `/plan` durante navegación menos el primero,
  mínimo cero; no mide directamente cada operación interna del planner.
- Estados: éxito/fallo de navegación, `NOT_SENT` si no se envió el objetivo y
  `NOT_APPLIED` para waypoint no aplicable según el contrato.
- Campos de memoria/intervención de N0: `N/A`.
- `memory_latency_ms`: intervalo monotónico desde el envío de la consulta hasta
  completar la recomendación; N0 y recomendaciones incompletas conservan `N/A`.
- `min_clearance_m`, `context_compliance` e `intervention_appropriate` son `N/A`
  en el logger raw. El evaluador calcula cumplimiento contextual por trayectoria
  independiente y GT congelado; clearance e intervención siguen sin medirse.

Los errores de escritura se notifican; no se prometen resultados persistidos
si el destino no es escribible.
Ver [diseño del contrato](reports/n1_contract_and_logging_design.md).

## Testing

Las suites controladas no necesitan la base experimental ni descargar el modelo.
En este checkout de publicación el venv existente es `.venv`; sustituye
`.venv-memory` por `.venv` en los comandos de tests si usas ese entorno.
El launch N1 actual consume `.venv/bin` para el worker de memoria.
Desde la raíz, con ROS/overlay cargados. El backend y los tests del paquete
Python usan el venv público; los tests CMake usan Python del sistema.
requirements-dev.txt incluye el runner colcon para ese venv. En esa suite se
anula la carga automática de plugins pytest externos de ROS; sus tests usan
pytest y rclpy directamente, sin fixtures de launch_testing:

~~~bash
source /opt/ros/jazzy/setup.bash
source ros2/install/setup.bash
.venv-memory/bin/python -m pytest memory/tests scripts/memory/tests
.venv-memory/bin/python -m pytest ros2/src/wheelchair_memory/test/test_memory_contract.py
cd ros2
/usr/bin/python3 /usr/bin/colcon test --packages-skip wheelchair_memory --executor sequential --ctest-args -j1 --output-on-failure
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../.venv-memory/bin/colcon test --packages-select wheelchair_memory --executor sequential --python-testing pytest
colcon test-result --verbose
~~~

Los tests de evaluación requieren también ROS y el overlay cargados:

~~~bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest scripts/experiments/tests
~~~

El guard E1 verifica evidencia de ingeniería externa mediante hashes; un clon
sin esa evidencia no supera el guard. `E1 --execute` solo valida y emite el
plan; no supervisa ni lanza las 40 ejecuciones. E2/E3 requieren la DB congelada,
configuración privada, modelo cacheado y permisos READ-ONLY.

Cobertura real: backend de memoria, MemoryQuery/NavigationRecommendation con
backend controlado, fixtures de fingerprint, resolver/logging N0/N1,
readiness y lista canónica/lifecycle/shutdown.
`NO TESTS DISCOVERED` no equivale a cobertura PASS.
El estado y los límites de validación se resumen en [Project Status](#project-status).
El registro detallado de migración y seguridad se conserva como evidencia privada;
no forma parte del candidato público. Esta documentación no vuelve a ejecutar las suites.

## Project Status

### VALIDATED

Monorepo y packaging; runtime Linux; PostgreSQL/pgvector; retrieval y
recomendación reales; contratos BT; logging común de 36 columnas (35 en los CSV históricos);
readiness fail-closed, incluyendo los casos runtime observados.
Tests/build afectados están documentados en las fases G.

### PARTIALLY VALIDATED / KNOWN LIMITATION

Inestabilidad intermitente Nav2/lifecycle/discovery.
**Root cause UNKNOWN; production fix NONE.**
**N0 integrado post-fix: NOT VALIDATED. N1 integrado post-fix: NOT VALIDATED.**
El cierre vigente es **PHASE G ENGINEERING VALIDATION CLOSED WITH KNOWN LIMITATION**.
No se presenta como una solución definitiva de Nav2 ni como campaña lista.

Se conservan finales de línea históricos heterogéneos y whitespace residual;
su normalización queda pendiente para un commit de mantenimiento.

### Scenario engineering validation

HOME y PARK están **RUNTIME_VALIDATED** como validación de ingeniería;
el fix cinemático está **VALIDATED** (visual 45 mm, colisión 5 mm).
AIRPORT es exploratorio: percepción dinámica PASS (scan/marking/clearing),
navegación **NAVIGATION_BLOCKED** tras N0 NAVIGATION_FAILURE.
Véanse [HOME](docs/experiments/HOME_01.md), [PARK](docs/experiments/PARK_01.md)
y [AIRPORT](docs/experiments/AIRPORT_01.md).

El diseño E1/E2/E3 y su GT están congelados en
[freeze_manifest.json](experiments/configs/freeze_manifest.json); el evaluador y
sus tests están versionados. Las campañas finales y sus informes se conservan
fuera del repositorio en `tfm-experimental-runs/`; sus resúmenes finales aún no
se han incorporado a este checkout. AIRPORT sigue fuera de E1 principal.
El estado histórico de Fase G anterior corresponde a aquella validación,
no al cierre posterior de campañas HOME/PARK.

## Experiment Validity and Available Data

La matriz de diseño HOME/PARK/AIRPORT, con queries candidatas, geometría,
ground truth independiente y puertas de calibración, está en
[docs/experiments/SCENARIO_MATRIX.md](docs/experiments/SCENARIO_MATRIX.md).

[experiments/data](experiments/data) contiene seed y queries;
[experiments/configs](experiments/configs) contiene configuración;
[experiments/results](experiments/results) conserva resultados y trazabilidad.
B1–B4 y sensibilidades estudian retrieval, no la campaña final N0/N1.
Los runs de ingeniería y los logs históricos se mantienen como tales.

**Infrastructure-invalid attempts are not efficacy results.**
Un run invalidado por infraestructura, por ejemplo `failure_stage=readiness`,
se conserva y etiqueta; no cuenta como success/failure científico N0/N1.
La política congelada admite como máximo un retry limpio por fallo de
infraestructura demostrado y ningún retry por fallo de navegación. Véanse
[el diseño congelado](docs/experiments/EXPERIMENTAL_DESIGN.md) y
[la configuración](experiments/configs/evaluation_design.json). El documento
congelado registra el checkpoint previo a las campañas; sus frases sobre
ejecución futura y captura pendiente son históricas. La captura actual usa
`transform.header.stamp` y un timer ROS de 10 Hz, como documenta
[la validación técnica E1](docs/experiments/E1_RUNTIME_VALIDATION.md).

## Reproducibility

Artefactos: esquema SQL y compose, seed/queries, requirements/constraints,
packaging Python, fuentes ROS/package.xml, suites controladas,
configuraciones y resultados históricos.
`canonical_memory_fingerprint_v2` permite verificar integridad mediante lectura.

El candidato usa exclusivamente el código y la estructura de este directorio.
No requiere clonar repositorios históricos ni acceder al workspace privado.
Las rutas históricas de informes/logs se conservan como evidencia.
Los comandos actuales usan rutas relativas desde la raíz.

La imagen `pgvector/pgvector:pg16` y el modelo no están fijados aquí a un digest
y revisión inmutables. Registrar esos identificadores y el entorno antes de una
campaña; una reconstrucción de embeddings no garantiza hashes idénticos.
La ruta del loader directo y el healthcheck de Compose tienen las limitaciones
documentadas en [database.md](docs/memory/database.md).

## Security and Publication

Los entornos virtuales, `.env`/`.env.memory` y artefactos ROS generados
permanecen ignorados. No compartir credenciales ni publicar backups de DB.
`.gitignore` publica explícitamente las guías técnicas activas y el diseño
experimental; mantiene ignorados documentos de trabajo privados.

La publicación final y el historial sensible aún requieren auditoría.
Los PDFs académicos no se consideran redistribuibles automáticamente;
preferir bibliografía/DOI/enlaces cuando corresponda.

## License

El código propio del proyecto y los cinco assets confirmados como creados por
la autora se distribuyen bajo [Apache License 2.0](LICENSE). Los cinco assets
y su alcance se enumeran en [docs/ASSETS.md](docs/ASSETS.md).

Los materiales de terceros conservan sus términos aplicables y sus avisos.
La malla silla.stl fue proporcionada por el tutor; su licencia/procedencia
original no está documentada. Se conserva sin cambios para reproducibilidad
y queda explícitamente excluida de la concesión Apache-2.0 del proyecto.
Haber recibido la malla no acredita por sí mismo derechos de redistribución.

## Clean publication candidate status

Este directorio es un candidato seleccionado con licencia Apache-2.0 para el
código y assets propios. La validación de ingeniería del candidato limpio pasó:
17 tests del backend, build de siete paquetes ROS y 81 tests ROS sin fallos;
DB/retrieval y servicios reales con dos cierres normales y fingerprint v2 estable.
No contiene historial Git de desarrollo ni configuración privada.

Los seis recursos de simulación y mapa se restauraron sin modificar su contenido
en la Fase J3e. La autora confirmó cinco assets propios; silla.stl fue proporcionado
por el tutor y su licencia/procedencia original no está documentada.
Véase [Assets: autoría y procedencia](docs/ASSETS.md), incluido el alcance
de Apache-2.0 y la exclusión explícita de silla.stl de ese alcance.
El directorio models/ y las referencias a SDF, STL y PGM ya están presentes.
El build está validado. Los dos intentos de simulación bloquearon la navegación
al fallar readiness por la limitación intermitente Nav2/lifecycle/discovery.
La navegación integrada exitosa y la licencia/procedencia de silla.stl
siguen pendientes.
En J3g se eliminaron tres entradas de instalación sin recursos ni consumidores
runtime: los directorios correspondientes estaban vacíos en el origen y Git no
los conserva. Las fuentes de instalación restantes existen y el build pasó. Véase [docs/ASSETS.md](docs/ASSETS.md).

Los directorios auxiliares wheelchair_api y wheelchair_vla no contienen
package.xml en este candidato; sólo se conservaron sus tests de plantilla
Apache aprobados. Esta fase no reconstruye su metadata.
El candidato contiene siete paquetes completos, construidos correctamente.

El build y los tests del candidato están validados; la campaña científica sigue
pendiente. No se cambiaron algoritmos ni contratos para ocultar fallos.
La limitación Nav2 indicada en Project Status permanece sin cambios.
