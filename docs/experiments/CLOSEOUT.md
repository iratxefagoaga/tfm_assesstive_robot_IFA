# Cierre técnico y experimental — 2026-10-12

Implementación textual/contextual y E1/E2/E3 terminados.
[Resultados y límites](../../experiments/results/final/README.md).
No se modifica navegación, diseño congelado, GT ni algoritmos.

## Reproducción

Preparar ROS y memoria con README, QUICK_START y docs/memory/linux-runtime.md.
ROS: Python de sistema. Backend: intérprete del venv Linux del checkout.
Verificación offline: python scripts/experiments/verify_final_results.py
E2/E3: DB congelada, modelo cacheado, READ-ONLY y fingerprint v2 antes/después.
python -m scripts.experiments.run_evaluation E2 --execute --output <directorio-nuevo>
E3 análogo. Reconstruir embeddings puede cambiar hashes: no equivale al original.

E1: conservar certificado original. Trasladar íntegros los directorios
certificados a <evidencia>/N0/ y /N1/, con los mismos bytes. En una sola línea:
python -m scripts.experiments.run_evaluation E1 --execute
--runtime-evidence-root <evidencia> --output <plan-nuevo.json>
La opción cambia solo la ruta; certificado, captura y todos los hashes siguen
verificados. Sin evidencia o con mutación se bloquea. El comando emite plan,
no lanza campaña. Réplica: supervisar cada run, capture_trajectory.py,
evaluate_navigation.py, cobertura, incidentes y cierre según protocolo.
run_evaluation analyze analiza selección nueva sin mezclar ingeniería/sintéticos.
Digests/revisiones de dependencias incompletos: no se inventan retrospectivamente.
Una verificación offline no sustituye una réplica.

## Tablas y figuras descriptivas

Dependencia opcional separada del runtime: requirements-evaluation-figures.txt.
Usar un entorno con matplotlib instalado:
python -m scripts.experiments.generate_final_figures --output <directorio-nuevo>
No sobrescribe resultados preservados ni recalcula pruebas estadísticas.
La regeneración se comprobó con Python Windows y matplotlib ya disponible;
el venv Linux actual no tiene matplotlib. No se instaló ni modificó el venv.

## Verificación de este cierre

70 tests experimentales PASS (incluidos guard trasladado y rechazo de mutaciones
en resultados/GT); git diff --check PASS; 20 artefactos finales y cinco inputs
congelados verificados offline. Regeneración de tabla/figuras PASS.
No se ejecutaron nuevas campañas ni se consultó DB; los controles DB pertenecen
a los informes originales. Interpretación, incidencias y límites siguen a cargo
de la autora; esto no acredita una mejora universal.

## Pendientes externos

Título/alcance: tutor y coordinación. Interpretación/redacción: autora,
incluidos fallos PARK, cobertura, evidencia mixta E3 e incidencias/reanudaciones.
Redistribución: silla.stl y revisión de assets de escenarios.
Merge/push requieren autorización específica; no se ejecutan aquí.
No se necesita otra campaña para describir el diseño ya cerrado; modificar
algoritmos/objetivos exigiría otra evaluación separada.
