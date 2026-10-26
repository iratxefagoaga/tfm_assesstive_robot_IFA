# PARK: versión operativa R2 en simulación

Versión activa: **release-20261026-r2**. [Informe de validación](../../diagnostics/park/REPORT_PARK_R2_20261026.md).
10/10 N0 y 10/10 N1 aceptados en una campaña nueva; no es garantía de eficacia
ni de éxito futuro. Solo misión canónica PARK_01 local. R1 y sus fallos se conservan.

Desde la raíz del repositorio preparado:
```bash
/usr/bin/python3 ros2/production/park_sim/run.py --check-only
/usr/bin/python3 ros2/production/park_sim/run.py --mode memory --output /tmp/park_r2_N1_nuevo
```
Usar `--mode direct` para N0, salida nueva y una misión a la vez. Se requieren ROS
Jazzy, Cyclone DDS, workspace compilado, .venv, modelo cacheado y contenedor
original tfm_memory_postgres. Las fuentes/binarios deben coincidir con el
manifiesto aceptado; un clon recompilado puede requerir recualificación. No se
garantiza ejecución inmediata en otro equipo. No se crea ni reinicializa la DB.
El runtime la consulta en solo lectura y verifica huellas. No hay hardware físico.

R2 conserva el LiDAR bajo y desactiva cámara/LiDAR alto sin uso en navegación.
La memoria no envía velocidades; la guarda cancela Nav2 ante scan caducado.
El retorno 0 requiere éxito de acciones, pose Gazebo válida en tolerancia y
cierre limpio. Los fallos quedan rechazados. No se amplían los timeouts.

Código y resúmenes están publicados; logs/poses completos permanecen privados.
Las exclusiones y dudas de procedencia de assets de docs/ASSETS.md se conservan.
El adaptador binario corresponde al entorno Linux/Jazzy observado y mantiene
su fuente y procedencia. No se asignan nuevas licencias a assets de terceros.
