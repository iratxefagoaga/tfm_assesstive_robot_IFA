# PostgreSQL/pgvector: configuración e integridad actuales

Guía CURRENT del monorepo. Los comandos se ejecutan desde su raíz.
La Fase H sólo audita esta receta: no inicia PostgreSQL, carga datos ni calcula
embeddings. Ver [estado y límites](../../README.md#project-status).

## Configuración privada

El backend exige las cinco variables siguientes. El `.env.example` raíz
contiene las variables MEMORY_DB_* con placeholders seguros.
Crear localmente un `.env.memory` privado con esta plantilla y sustituir
el placeholder de password; no publicar ese archivo:

~~~dotenv
MEMORY_DB_HOST=localhost
MEMORY_DB_PORT=5433
MEMORY_DB_NAME=memory
MEMORY_DB_USER=tfm
MEMORY_DB_PASSWORD='<set_locally>'
~~~

Los nombres de usuario y base son identificadores, no contraseñas.
El healthcheck usa los identificadores configurados en el contenedor.
MEMORY_DB_PORT selecciona el puerto host (5433 por defecto); elegir uno libre
si ya existe una base local. Cada proyecto Compose usa su contenedor y volumen.
Cargar las variables explícitamente; no existe autoload dotenv:

~~~bash
set -a
source .env.memory
set +a
~~~

No imprimir el entorno completo, la contraseña ni el DSN.
El password debe permanecer local y el archivo con permisos privados.

## Inicialización: únicamente una base NUEVA

No ejecutar esta sección sobre la base experimental congelada.
Usar un proyecto Compose nuevo y un puerto libre. No reinicializar ni borrar
contenedores o volúmenes de una base existente.

~~~bash
docker compose --env-file .env.memory --project-name tfm-reproduction -f database/docker-compose.memory.yml ps -a
docker compose --env-file .env.memory --project-name tfm-reproduction -f database/docker-compose.memory.yml config --quiet
~~~

Continuar sólo si se ha confirmado una instalación nueva y libre de conflicto:

~~~bash
docker compose --env-file .env.memory --project-name tfm-reproduction -f database/docker-compose.memory.yml up -d
docker compose --env-file .env.memory --project-name tfm-reproduction -f database/docker-compose.memory.yml ps
~~~

Esperar a `healthy` antes de la carga. Compose publica MEMORY_DB_PORT (5433 por defecto)
y usa `pgvector/pgvector:pg16`.
No monta automáticamente el esquema; aplicar una vez sobre la base nueva:

~~~bash
docker compose --env-file .env.memory --project-name tfm-reproduction -f database/docker-compose.memory.yml exec -T postgres psql -U "$MEMORY_DB_USER" -d "$MEMORY_DB_NAME" -v ON_ERROR_STOP=1 < database/init.sql
~~~

El [esquema](../../database/init.sql) crea extensiones y `memory_episodes`,
incluyendo vectores de 1024 dimensiones. No es una receta para resetear
la base existente. No usar backups privados ni `down -v` para reproducirla.

## Seed: funciones existentes, ruta explícita

El [loader](../../scripts/memory/load_memories.py) conserva una limitación:
su `CSV_PATH` resuelve bajo `scripts/experiments/`, no la raíz del monorepo.
Por ello no se documenta su CLI directo como funcional.
La siguiente receta usa sus funciones reales sin cambiar datos ni algoritmo
de preparación, con el [seed correcto](../../experiments/data/memory_seed.csv).
**Inserta/actualiza; ejecutar exclusivamente en la base nueva.**

~~~bash
.venv-memory/bin/python - <<'PY'
from pathlib import Path
import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from scripts.memory.load_memories import prepare_dataset, insert_memories

url = URL.create(
    "postgresql+psycopg2",
    username=os.environ["MEMORY_DB_USER"],
    password=os.environ["MEMORY_DB_PASSWORD"],
    host=os.environ["MEMORY_DB_HOST"],
    port=int(os.environ["MEMORY_DB_PORT"]),
    database=os.environ["MEMORY_DB_NAME"],
)
engine = create_engine(url)
try:
    dataset = pd.read_csv(Path("experiments/data/memory_seed.csv"))
    insert_memories(engine, prepare_dataset(dataset))
finally:
    engine.dispose()
PY
~~~

`URL.create` evita interpolar el password en una URL literal.
La importación no ejecuta el main del loader.
La receta se ha revisado contra firmas y código actuales; no se ha ejecutado
contra una base durante H.

## Embeddings: exclusivamente para reconstrucción nueva

El modelo actual es `Qwen/Qwen3-Embedding-0.6B`, CPU, dimensión 1024,
con normalización de embeddings. Tras el seed de una base nueva:

~~~bash
.venv-memory/bin/python -m memory.embedding.generate_embeddings
.venv-memory/bin/python -m memory.embedding.generate_episodic_embeddings
~~~

Estos comandos **escriben** vectores. No ejecutarlos sobre la base congelada
durante validaciones. La primera ejecución puede descargar el modelo;
modo offline sólo es viable con el caché completo.
El generador semántico construye actualmente su URL desde variables:
los caracteres reservados en credenciales requieren revisar ese consumidor;
H no modifica su implementación. No imprimir esa URL.

La revisión exacta del modelo y digest de imagen no están fijados en estos
comandos. Registrar ambos y las versiones antes de una campaña. Regenerar
vectores puede producir diferencias numéricas: no prometer hashes idénticos
a otra instalación.

## Verificación READ-ONLY: fingerprint v2

Con runtime instalado y variables privadas cargadas:

~~~bash
.venv-memory/bin/python -m scripts.memory.fingerprint_memory
~~~

El [script real](../../scripts/memory/fingerprint_memory.py) abre una
transacción de sólo lectura con snapshot REPEATABLE READ, consulta
`memory_episodes` ordenado por memory_id y cierra con rollback.
Reporta `method`, `row_count`, `logical_sha256` y `embeddings_sha256`.

`canonical_memory_fingerprint_v2` usa SHA-256 sobre JSON canónico:
UTF-8, claves ordenadas y separadores compactos. Contenido lógico y vectores
se comparan por separado.
Verificar antes y después de cada validación READ-ONLY: mismo row count y
ambas huellas. La base validada tenía 50 memorias; medir, no asumir.

El fingerprint anterior tiene un método histórico no recuperado.
Conservar su evidencia sin comparar numéricamente hashes de metodologías
distintas. Un `--help` del script no es una comprobación inocua:
no tiene parser CLI y ejecutaría el acceso a DB.

Para servicios/consultas de validación, añadir en su terminal:

~~~bash
export PGOPTIONS='-c default_transaction_read_only=on'
~~~

No aplicar esa opción al aprovisionamiento nuevo que necesita escribir.
No insertar experiencias desde los smokes de validación.
