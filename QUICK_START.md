# Quick start — monorepo actual

El punto de entrada es [README.md](README.md).

1. Revisar [estado y limitación Nav2](README.md#project-status).
2. Preparar [runtime Linux](docs/memory/linux-runtime.md).
3. Configurar PostgreSQL según [database.md](docs/memory/database.md).
   Inicializar únicamente una base nueva; conservar la experimental congelada.
4. Construir [ROS con Python del sistema](README.md#ros-2-build).
5. Ejecutar [tests controlados](README.md#testing).
6. Para una consulta sin Gazebo, usar [servicios de memoria](README.md#memory-services).

Los smokes N0/N1 documentados son recetas para una validación futura;
no constan como PASS integrado post-fix.
Casa/Mall/Aeropuerto y la campaña científica final permanecen PLANNED.
Las instrucciones anteriores de aplicación auxiliar no son el setup actual
de memoria/BT/Nav2.

## Prerrequisitos pendientes del candidato público

Los seis assets se han restaurado con hashes idénticos en la Fase J3e.
Revisar su [autoría y procedencia](docs/ASSETS.md), el alcance de Apache-2.0 y
[Clean publication candidate status](README.md#clean-publication-candidate-status)
antes de publicar. La licencia original de silla.stl sigue sin documentarse.
Estos comandos no constituyen una validación del candidato limpio. El build y los
tests completos siguen pendientes; no se ha ejecutado simulación en esta fase.
