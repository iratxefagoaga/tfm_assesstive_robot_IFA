# PARK: explicación de los fallos, 26/10/2026

La campaña final de veinte intentos obtuvo aceptación de 8/10 N0 y 6/10 N1.
El éxito de acción, menos estricto, fue 9/10 y 8/10. No se declara PARK cerrado
globalmente en producción. Se cumple la alternativa de explicar los mecanismos
de rechazo con evidencia sincronizada, conservando los límites de atribución.

## Los cuatro rechazos de N1

* Intento 02: Nav2 estima (0,8547; -9,0151), error 0,1461 m, dentro de su
  tolerancia 0,15 m. Gazebo mide (0,7243; -8,9928), error 0,2758 m.
  El sesgo de posición es 0,1323 m. La tolerancia y el error de localización
  consumen más que el presupuesto independiente de 0,25 m.
* Intento 17: error estimado 0,1473 m, sesgo 0,1607 m, error real 0,3024 m.
  Mismo mecanismo: éxito interno compatible con llegada real fuera de tolerancia.
  TF/odom/Gazebo se observaron con edades de 0,052/0,023/0,008 s en ese evento.
* Intentos 07 y 09: el scan deja de avanzar, el guardián marca scan_stale y
  cancela Nav2. La cancelación termina; no hay éxito ni destino final enviado
  después del waypoint fallido. Son paradas deliberadas por datos caducados,
  no errores demostrados de retrieval.

## Localización reproducida de la interrupción del scan

Se repitió una misión sin cambiar la versión, añadiendo observadores pasivos
del topic nativo Gazebo y de ROS antes y después del filtro. El primer intento
reprodujo scan_stale. Entre stamps 8,515 y 8,581 s, el LiDAR adicional presenta
una pausa de entrega nativa de 1,132 s; el original, 1,166 s. ROS recibe la
misma pausa (1,166 s en navigation_scan). El máximo hueco del reloj ROS en
esa ventana es 0,454 s y el de poses físicas 0,464 s: el resto del simulador
sigue avanzando. El guardián falla a t=14534,568 monotónico; el siguiente scan
nativo llega a 14534,604, después del umbral de frescura. La cancelación queda
completa a 14534,885. Los observadores y la pila cierran limpiamente.

Esto sitúa la interrupción en la ruta común nativa de sensores de Gazebo,
antes del puente ROS y del filtro. No se distingue aún entre renderizado,
planificación del sistema y transporte nativo. La presión de recursos observada
es compatible con retrasos, pero no prueba una causa exclusiva. El observador
añade carga: se usa para localizar el mecanismo, no para estimar la tasa final.
La caída de internet comunicada no demuestra la causa de este flujo local.

## Los dos rechazos de N0

Intento 10: falla la activación lifecycle de waypoint_follower por
async_send_request failed; readiness no se alcanza y no se navega. La causa
subyacente de ese fallo de servicio no queda determinada.
Intento 18: llega a 0,1708 m del destino, pero Gazebo no termina con SIGINT
ni SIGTERM; launch escala automáticamente a SIGKILL. Es un fallo de cierre,
no de llegada. Se conserva como rechazo porque el protocolo exige cierre limpio.

## Alcance de la explicación y acciones concretas

Los cuatro fallos N1 de la versión final tienen mecanismo documentado:
dos llegadas falsas por margen insuficiente frente al sesgo de localización,
y dos cancelaciones por scan caducado, reproducido y localizado antes de ROS.
No equivale a demostrar una causa común de los seis abortos de E1 original.
La recuperación no se modifica. Para un cierre de robustez adicional habría que
reducir y volver a validar el error de localización/presupuesto de llegada,
aislar renderizado frente a transporte/scheduling y resolver lifecycle/cierre.
No se amplía el umbral de frescura ni se relabelan fallos como éxitos.

Datos y SHA256: experiments/diagnostics/park_failure_explanation_20261026.
Campaña final intacta: experiments/results/park_corrected_20261026.

## Alcance de esta publicación

Se publican código, configuración, protocolo y resúmenes numéricos. Los logs,
poses y manifiestos de datos brutos completos se conservan en el archivo privado
de la ejecución. Las referencias a ellos en el informe describen esa evidencia
local; no afirman que dichos archivos formen parte de esta rama pública.
