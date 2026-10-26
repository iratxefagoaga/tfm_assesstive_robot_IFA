La explicación sincronizada está en [el informe de fallos](../../diagnostics/park/REPORT_FAILURE_EXPLANATION_20261026.md).

## Medición posterior: fiabilidad limitada

La campaña fija posterior de 20 intentos está en
[los resultados](../../../experiments/results/park_corrected_20261026/summary.json).
La aceptación operativa anterior no demuestra robustez general. Los fallos de
esta campaña se conservan en el denominador y la tasa es descriptiva de PARK_01.
La entrada permite omitir --code-root cuando se usa desde este repositorio.

# Producción local de PARK en simulación

Versión activa: **release-20261026-r1**. Cierre operativo documentado en
[el informe](../../diagnostics/park/REPORT_PRODUCTION_CLOSURE_20261026.md).
Solo la misión canónica PARK_01, en Gazebo/ROS 2 Jazzy. Los resultados científicos
congelados permanecen aparte. No requiere hardware físico.

Desde WSL, con el checkout validado disponible:

```bash
/usr/bin/python3 ros2/production/park_sim/run.py \
  --code-root "$PWD" --check-only

/usr/bin/python3 ros2/production/park_sim/run.py \
  --code-root "$PWD" --mode memory \
  --output /tmp/park_production_N1_NUEVO
```

Usar `--mode direct` para N0 y un directorio nuevo para cada ejecución.
No es necesario activar el venv: el ejecutor establece el entorno ROS y el
trabajador de memoria usa su intérprete explícito. Requiere los paquetes ROS
existentes, Cyclone DDS y el contenedor original tfm_memory_postgres disponible.
N1 usa exclusivamente consultas read-only y verifica fingerprints antes/después.

Un retorno 0 confirma aceptación de esa ejecución. La decisión y los motivos se
guardan en physical_acceptance.json; también se conservan CSV, logs, poses Gazebo,
AMCL/odom/TF, salud del scan y recursos. Un error de entrada/infraestructura puede
detenerse antes de producir una fila o decisión final: nunca equivale a éxito.

Si faltan archivos o cambian respecto a la versión validada, el comando rechaza
el arranque. No editar la versión activa para ajustar un ensayo: preparar una
nueva versión y revalidarla. El bloqueo de misión evita solapar dos ejecuciones.
Ante pérdida de scan, cancela Nav2 y cierra; para repetir, usar otra salida.
No hay reintentos automáticos ni sustitución de Nav2 por comandos de memoria.

## Distribución y límites

Ejecutar desde la raíz de este repositorio. Este directorio incorpora la versión
local aceptada sin modificar los lanzadores de la campaña E1 congelada.
Las fuentes, el perfil y el adaptador compilado están incluidos. El ejecutable
es Linux x86-64 para el entorno Jazzy observado; no es un binario universal.
La compilación local ROS, el intérprete .venv y sus binarios se verifican contra
la instalación aceptada: un clon recién compilado puede ser rechazado aunque
las fuentes coincidan. No sustituir hashes para aparentar validación.
Para otro entorno, reconstruir el adaptador con CMake en diagnostics/park/native,
preparar el perfil y repetir qualify_simulation_release.py antes de generar
una nueva versión mediante build_simulation_release.py. No se certifica una
instalación desde cero en otro equipo.

La base original y el modelo cacheado no se publican. Se requiere el contenedor
existente tfm_memory_postgres; el lanzador no lo crea ni lo reinicializa.
Las exclusiones y dudas de procedencia de assets en docs/ASSETS.md también
se aplican a sus copias del perfil; no se otorgan permisos nuevos.
El informe de cierre conserva rutas históricas como procedencia local.

## Alcance de esta publicación

Se publican código, configuración, protocolo y resúmenes numéricos. Los logs,
poses y manifiestos de datos brutos completos se conservan en el archivo privado
de la ejecución. Las referencias a ellos en el informe describen esa evidencia
local; no afirman que dichos archivos formen parte de esta rama pública.
