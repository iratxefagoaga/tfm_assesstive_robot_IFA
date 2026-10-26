# Campaña prospectiva posterior de PARK — 26/10/2026

Protocolo fijado antes de ejecutar: 10 N0 y 10 N1, semilla 20261026, sin reemplazos ni exclusiones. Misma versión release-20261026-r1 para ambas condiciones.

Aceptación: objetivos aplicables exitosos, pose Gazebo reciente en el éxito final y pose tras cierre dentro de 0,25 m/0,25 rad; cierre limpio. El éxito de acción se cuenta aparte.

{
  "N0": {
    "attempts": 10,
    "accepted": 8,
    "action_successes": 9,
    "rate": 0.8,
    "wilson_95": [
      0.49016247153664183,
      0.9433178485456247
    ]
  },
  "N1": {
    "attempts": 10,
    "accepted": 6,
    "action_successes": 8,
    "rate": 0.6,
    "wilson_95": [
      0.31267376973365824,
      0.8318196702937638
    ]
  }
}

Las 20 decisiones fueron recomputadas desde pilot_results.json; IDs únicos; las 20 huellas DB de N1 coinciden con la referencia congelada. Se conserva cada fallo y trayectoria. La caída de internet comunicada por la autora está anotada sin atribuirle automáticamente los fallos internos ROS: el runtime fue local y offline.

Estos resultados sustituyen la tasa histórica como descripción de la versión final de PARK_01; no reescriben E1 original ni demuestran eficacia general o causa única de mejora. El criterio independiente es más estricto que el éxito de acción histórico. La cualificación previa no constituye un cierre de fiabilidad universal. Fuera de la misión canónica no se afirma validación.

Protocolo, resultados, logs, poses y manifiesto: experiments/results/park_corrected_20261026. El informe de cierre anterior conserva carácter histórico.

## Alcance de esta publicación

Se publican código, configuración, protocolo y resúmenes numéricos. Los logs,
poses y manifiestos de datos brutos completos se conservan en el archivo privado
de la ejecución. Las referencias a ellos en el informe describen esa evidencia
local; no afirman que dichos archivos formen parte de esta rama pública.
