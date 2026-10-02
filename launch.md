# Ejecución del monorepo

Las recetas activas están centralizadas en el [README](README.md):

- [MemoryQuery y NavigationRecommendation sin simulación](docs/memory/linux-runtime.md#servicios-ros-sin-simulacion).
- [Smokes N0 y N1](README.md#smoke-commands-for-future-validation).

Utilizar `ros2/` como workspace y el runtime Linux `.venv-memory`
sólo donde corresponde. N1 coordina sus propios servicios; no duplicarlos.
N0 no consulta memoria.

Los launches documentados no certifican estabilidad Nav2.
Estado integrado post-fix N0/N1: NOT VALIDATED.
Para cierre, señalizar una vez al launch propietario y esperar a sus hijos;
no utilizar SIGKILL como mecanismo habitual ni iniciar otro stack con
procesos residuales.
