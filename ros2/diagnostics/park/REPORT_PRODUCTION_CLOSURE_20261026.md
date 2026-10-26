# Cierre de producción local: PARK simulado — 26/10/2026

**CLOSED — PARK_SIMULATION_RELEASE_READY**, versión `release-20261026-r1`.
Alcance: escenario y misión canónicos PARK_01 en Gazebo, N0/N1, entorno local
WSL/ROS 2 Jazzy. La usuaria confirmó que todo el trabajo es simulado: la validación
en silla física no forma parte de este cierre. No se declara validación de otros
escenarios, destinos arbitrarios, publicación pública ni eficacia científica.

## Versión utilizable

Entrada estable: `/home/iratxefagoaga/workspace/tfm/ros2/production/park_sim/run.py`.
La versión empaqueta 15 archivos de ejecución, incluidos el adaptador de puente
compilado y su procedencia, y fija por SHA256 44 recursos del perfil y 136 archivos
de las fuentes/dependencias locales instaladas del checkout validado. Las cachés
Python no forman parte del inventario. Cada arranque comprueba los hashes antes
de iniciar procesos o la DB. Un bloqueo de misión impide dos ejecuciones simultáneas.
El comprobador se ha ejecutado también después del recorrido empaquetado.

El LiDAR adicional, su pose (0,33;0;0,08) respecto al modelo y el filtro propio
son parámetros del diseño simulado. Se conserva el sensor original. El perfil
mantiene mapas y geometrías de colisión originales y usa tolerancias internas de
0,15 m/0,15 rad, aceptación independiente de 0,25 m/0,25 rad y Cyclone DDS limitado
a sus procesos. El middleware global observado sigue siendo `rmw_fastrtps_cpp`.

## Endurecimiento y fallos corregidos

1. El guardián del scan rechaza esquema incompatible, reloj regresivo y datos
   cuyo tiempo no avance durante más de 1 s de reloj de pared. El primer scan
   tiene el plazo existente de 120 s; no se aumentan plazos de navegación.
2. Ante pérdida del sensor se cancelan las acciones Nav2 por su servicio ROS y
   se comprueba que la acción externa y los controladores conocidos sean terminales
   antes de apagar la pila. Reloj y TF permanecen disponibles durante la cancelación.
   La memoria y el guardián no publican cmd_vel.
3. El adaptador local usa los conversores y transportes de ros_gz_bridge instalado
   (1.0.22), cerrando sus transportes mientras el contexto ROS sigue válido.
   El manejador de señal no invalida anticipadamente ese contexto. El canal de
   velocidad es ROS→Gazebo. No se ha modificado la biblioteca del sistema.
4. En N1, el proceso Qwen se libera al aceptarse el primer goal, después de las
   consultas/recomendación reales. El BT ya conserva la estrategia y no hace
   consultas entre waypoint y destino. Es un proceso por misión; una misión nueva
   inicia otro trabajador. No se cambian retrieval, pesos, embeddings ni ranking.
5. La llegada se contrasta con la pose Gazebo disponible al observar el éxito del
   **último** goal; no se confunde el éxito del waypoint con el del destino. La pose
   debe ser reciente (<=2 s), tener frame/entidad correctos y cuaternión válido.
   También se exige que la pose final tras el cierre conserve la tolerancia.
6. SIGABRT, SIGSEGV y otros cierres anómalos dejan de contar como cierre limpio.
   Los fallos, datos inválidos y ejecuciones incompletas producen rechazo.

## Pruebas de aceptación

| Ejecución | Error de posición en Gazebo (m) | Error angular (rad) | Resultado |
|---|---:|---:|---|
| N0_normal | 0.1549 | 0.0076 | aceptado |
| N1_normal | 0.0945 | 0.1388 | aceptado |
| N1 mediante el comando empaquetado | 0.1619 | 0.1669 | aceptado |

Los N1 normales recuperan M013/west mediante los servicios reales y completan
waypoint y destino. Todos esos cierres son limpios, con los dos mensajes
CLEAN_BRIDGE_SHUTDOWN, sin escalados de señal ni residuos.

Prueba de fallo: se pausó únicamente el puente del LiDAR adicional durante
1,6 s después de iniciar el primer goal de N1. El guardián detectó scan_stale
1.016 s después de pausar el puente.
La cancelación quedó completa 0.200 s
después de detectar el fallo. El puente se reanudó para permitir cierre normal.
No hubo éxito falso ni final enviado después del waypoint fallido; el caso cerró
limpiamente. La fila original y el log se conservan bajo N1_scan_loss; el destino
final permanece NOT_SENT y solo consta un goal de navegación iniciado.

El adaptador pasó seis ciclos adicionales de inicio/cierre sin simulación.
La suite diagnóstica completa pasó 29 tests. El CLI empaquetado pasó cinco
comprobaciones: integridad válida, rechazo de código alterado, rechazo de sensor
alterado, rechazo de fuentes equivocadas y rechazo de misión simultánea. Esas
comprobaciones no arrancaron simulación ni cambiaron el estado de la DB.

## Intentos rechazados conservados

- La primera aceptación operativa del 25/10 rechazó N0 por antigüedad calculada
  después del apagado. El recorrido había llegado a 0,1699 m y cerró sin escalado.
  Se corrigió la referencia temporal; no se aumentó el límite de 2 s ni se cambió
  retrospectivamente su decisión registrada.
- En el intento del 26/10 terminado en `_01`, N0 fue registrado como limpio por
  el clasificador antiguo aunque el log muestra un puente con salida -6. La
  reauditación considera ese cierre anómalo. N1 detectó pérdida no inyectada del
  scan bajo presión de recursos y su apagado inmediato acabó escalando el
  controlador a SIGKILL. El protocolo se detuvo; no se sustituyó por un éxito.
- Tras esos fallos se introdujeron la cancelación previa, el adaptador de puente,
  la liberación del trabajador de embeddings y el detector de salida anómala.
  Se conservan logs, protocolos y código de cada intento, con las limitaciones
  de versión indicadas en sus snapshots.

No se atribuye a una única causa el conjunto de los seis abortos históricos:
estos cambios resuelven y prueban el perfil operativo actual en el alcance fijado.

## Integridad y cierre

Ocho fingerprints de esta fase coinciden exactamente con la referencia v2 de
50 registros. No se modificó la DB ni se regeneraron embeddings. Se restauró el
estado del contenedor original. Verificador científico: PASS para veinte
artefactos e inputs congelados. Sin procesos ROS/Gazebo/puentes/trabajadores ni
contenedores activos al terminar. Sin stage, commit, push ni contacto a remotes.

E1 PARK/N1 original sigue siendo 4/10 éxitos de acción. Las ejecuciones de
ingeniería se conservan aparte y no se usan para publicar una tasa futura del
100 %. La memoria académica no se modifica para reemplazar la campaña original.

Archivo privado de cierre: `/home/iratxefagoaga/tfm-experimental-runs/20261026_park_simulation_release`.
El manifiesto conserva hashes de evidencias, código, fuente del adaptador y
versión desplegada. No contiene .env ni archivos de credenciales.

## Alcance de esta publicación

Se publican código, configuración, protocolo y resúmenes numéricos. Los logs,
poses y manifiestos de datos brutos completos se conservan en el archivo privado
de la ejecución. Las referencias a ellos en el informe describen esa evidencia
local; no afirman que dichos archivos formen parte de esta rama pública.
