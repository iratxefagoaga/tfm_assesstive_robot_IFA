# Linux memory runtime — CURRENT

Guía del monorepo actual. El repositorio histórico no es un fallback runtime.
Los informes anteriores conservan sus rutas como evidencia.
Ver [README](../../README.md) y [PostgreSQL/pgvector](database.md).

## Entorno y dependencias

Runtime validado: Ubuntu 24.04.4 LTS/WSL2, Python 3.12.3 y CPU.
Backend único `tfm-memory` instalado editable desde `memory/`.
ROS 2 Jazzy y sus interfaces se gestionan con paquetes ROS, no pip memory.

Desde la raíz, en una terminal sin overlay ROS:

~~~bash
/usr/bin/python3 -m venv .venv-memory
.venv-memory/bin/python -m pip install setuptools==78.1.0
.venv-memory/bin/python -m pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
.venv-memory/bin/python -m pip install -r requirements-memory.txt -c requirements-memory-linux-cpu.constraints.txt
.venv-memory/bin/python -m pip install --no-deps --no-build-isolation -e ./memory
.venv-memory/bin/python -m pip install -r requirements-dev.txt
.venv-memory/bin/python -m pip check
~~~

Instalar CPU primero evita seleccionar CUDA transitivamente.
`--no-build-isolation` requiere setuptools ya instalado.
El entorno virtual permanece local e ignorado.
`pip check` aislado del overlay pasó en la revisión H. Con el overlay ROS
cargado se observó el requisito de `typeguard` de
`generate-parameter-library-py`; separar esa revisión de las dependencias
del backend, sin ocultar el aviso ni modificar paquetes en H.

## Configuración

Cargar las cinco variables `MEMORY_DB_*` según [database.md](database.md).
El backend no carga archivos dotenv automáticamente.
Qwen puede usar su caché existente; `HF_HUB_OFFLINE=1` y
`TRANSFORMERS_OFFLINE=1` sólo si ese caché está completo.
No cargar/modelar embeddings como parte de un check de imports o documentación.

## Servicios ROS sin simulacion

Requiere workspace construido e interfaces generadas.
En la raíz, abrir dos terminales; cada una carga ROS y configuración privada.
Primera terminal:

~~~bash
source /opt/ros/jazzy/setup.bash
source ros2/install/setup.bash
set -a
source .env.memory
set +a
export PGOPTIONS='-c default_transaction_read_only=on'
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false .venv-memory/bin/python ros2/install/wheelchair_assistive_bt/lib/wheelchair_assistive_bt/managed_memory_process.py memory
~~~

Segunda terminal:

~~~bash
source /opt/ros/jazzy/setup.bash
source ros2/install/setup.bash
set -a
source .env.memory
set +a
export PGOPTIONS='-c default_transaction_read_only=on'
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false .venv-memory/bin/python ros2/install/wheelchair_assistive_bt/lib/wheelchair_assistive_bt/managed_memory_process.py recommendation
~~~

El wrapper real ofrece esos roles y controla executor/node/context en el
cierre. Usar una señal al proceso propietario; esperar la salida y comprobar
que no quedan procesos antes de otro arranque. No exigir una duración
artificialmente corta a la finalización del runtime Python/modelo.

El intérprete explícito evita depender del shebang de `ros2 run`.
No insertar site-packages, rutas personales ni el repo histórico en PYTHONPATH.
ROS setup proporciona sus rutas estándar para tipos generados.
Las llamadas canónicas están en [README](../../README.md#memory-services).

El launch N1 ya crea ambos roles: no arrancar estos servicios por separado
si se utiliza ese launch. N0 no necesita esos servicios.

## Build y validación

Colcon debe utilizar `/usr/bin/python3`, con el venv desactivado.
Ver [build](../../README.md#ros-2-build) y [tests](../../README.md#testing).
La receta H no ejecuta build, tests, servicios, modelo ni smokes.
La validación integrada post-fix N0/N1 sigue pendiente por la limitación Nav2;
no confundir el runtime de memoria validado con navegación integrada validada.
