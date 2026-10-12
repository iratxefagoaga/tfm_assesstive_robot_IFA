# Resultados definitivos E1/E2/E3

Selección de 2026-10-12 idéntica a los informes originales externos.
No se repitieron experimentos, no se recalcularon pruebas ni se cambió el GT.
E1: 40 observaciones, 46 intentos; 34 SUCCEEDED, seis ABORTED válidos PARK/N1.
Tres mediciones inválidas y tres intentos de infraestructura quedan fuera
de la selección pero se conservan en el archivo completo.
E2: 20 consultas R0/R1, Recall@3 0.47444 -> 0.57514, efecto 0.10069,
IC95% [0.03125,0.175], p=0.014.
E3: diez casos P0/P1, ocho pares primarios, 0/8 -> 8/8, McNemar p=0.0078125.
C04/C05 DEFAULT_SENSITIVE secundarios, excluidos del contraste primario.

## Lectura

E1/final_e1_report.json es el cierre definitivo; los informes intermedios
STOPPED_CAPTURE_CONTRACT no lo sustituyen. Los análisis originales están en
E1/frozen_final_analysis.json y E2/E3/paired_analysis.json.
navigation_summary.csv y figuras derivan de los resultados finales:
descriptivos de tiempo/distancia incluyen fallidos; inferencia continua solo éxitos.

E1 es proxy de estrategia oeste, no clearance, confort, seguridad ni rodeo
de jardín. PARK/N1: éxito 4/10, cumplimiento 4/4 evaluables, cobertura 4/10;
seis N/A no son ceros. Mostrar cobertura y éxito junto al cumplimiento.
PARK/N0 llega 10/10; HOME/N1 tiene mayor tiempo/distancia. No mejora universal.
R1 combina filtro/contexto; E3 retira evidencia personalizada episódica y
semántica, no aísla vector episódico ni prueba aprendizaje longitudinal.

## Integridad y conservación

python scripts/experiments/verify_final_results.py verifica hashes offline
sin ROS, modelo ni DB: no es réplica ni nueva validación científica.
Conservar archivos privados completos con sus hashes:
tfm-experimental-runs/20261005T153539_e1_frozen_campaign/
tfm-experimental-runs/20261005T143507_e2e3_frozen/
Incluyen descartados, logs, capturas, auditorías e incidencias/reanudaciones.
Hubo escalados automáticos de launch, algunos con SIGKILL: describir y
contrastar con el protocolo. No se publican automáticamente los archivos
completos. Fingerprints acreditan las fechas de campaña, no la DB actual.
