# Análisis estadístico del protocolo experimental

Fecha: 2026-09-28

## Datos analizados

Se inventariaron todos los CSV bajo experiments/results. El análisis de navegación usa exclusivamente el lote protocol_20260928 del escenario S001_shared_safe_goal, para no mezclarlo con resultados de aceptación previos ni con resultados B1-B4 de retrieval.

Se analizaron cinco registros MEMORY_OFF y cuatro registros MEMORY_ON con CSV crudo. El manifiesto contiene cinco parejas; Memory ON protocol_20260928_004 figura como NO_RESULT y launcher_timed_out=true. Se conserva como dato faltante documentado. No se imputó como éxito, fallo ni valor numérico.

No se retiraron observaciones como outliers.

## Estadística descriptiva

| Condición | Métrica | n | Media | Mediana | DE muestral | IC 95% de la media |
|---|---|---:|---:|---:|---:|---|
| MEMORY_OFF | tiempo (s) | 5 | 1.893 | 1.276 | 1.330 | [0.242, 3.545] |
| MEMORY_OFF | distancia (m) | 5 | 0.104 | 0.073 | 0.100 | [-0.020, 0.228] |
| MEMORY_OFF | replanning | 5 | 1.000 | 1.000 | 1.000 | [-0.241, 2.241] |
| MEMORY_ON | tiempo (s) | 4 | 3.404 | 3.458 | 0.311 | [2.909, 3.900] |
| MEMORY_ON | distancia (m) | 4 | 0.262 | 0.261 | 0.002 | [0.259, 0.264] |
| MEMORY_ON | replanning | 4 | 2.500 | 2.500 | 0.577 | [1.581, 3.419] |

Los intervalos de las medias cuantitativas usan t de Student bilateral al 95% con desviación estándar muestral. Sus límites negativos para distancia o replanning son una consecuencia matemática del intervalo t en esta muestra pequeña, no valores físicos observados.

## Éxito y sus intervalos

Las tasas e intervalos Wilson 95% se calculan solo sobre los registros con resultado CSV.

| Condición | Éxitos / registros | Tasa | IC Wilson 95% |
|---|---:|---:|---:|
| MEMORY_OFF | 1 / 5 | 0.200 | [0.036, 0.624] |
| MEMORY_ON | 4 / 4 | 1.000 | [0.510, 1.000] |

## Diferencias observadas

Diferencia de medias no emparejada, definida como MEMORY_ON menos MEMORY_OFF:

| Métrica | Diferencia observada |
|---|---:|
| tiempo (s) | 1.511 |
| distancia (m) | 0.158 |
| replanning | 1.500 |

Estas diferencias son descriptivas. No se sometieron a prueba inferencial por el tamaño muestral, la falta de un resultado Memory ON y la asimetría de éxitos entre condiciones.

En las cuatro parejas completas, los resultados binarios fueron: tres pares con MEMORY_OFF fallido y MEMORY_ON exitoso, uno con éxito en ambas condiciones, cero con MEMORY_OFF exitoso y MEMORY_ON fallido.

Se aplicó McNemar exacto bilateral sobre los tres pares discordantes:

- pares completos: 4
- discordantes OFF éxito / ON fallo: 0
- discordantes OFF fallo / ON éxito: 3
- p exacta bilateral: 0.250

Con p=0.250 no se rechaza la hipótesis nula de probabilidades marginales de éxito iguales al nivel 0.05. No se afirma significancia.

Solo la pareja 002 fue exitosa en ambas condiciones. Para esa única pareja, las diferencias ON menos OFF fueron: tiempo 0.490 s, distancia 0.003 m y replanning 1. Con n=1 no se calcula desviación estándar, intervalo ni prueba estadística para las métricas cuantitativas emparejadas.

## Reproducibilidad

El script experiments/scripts/generate_statistical_tables.py regenera sin cambiar datos originales:

- experiments/results/statistical_analysis/descriptive_statistics.csv
- experiments/results/statistical_analysis/paired_success.csv
- experiments/results/statistical_analysis/analysis_metadata.json

El script fija explícitamente el prefijo protocol_20260928, conserva la ejecución NO_RESULT como ausencia de CSV y declara que no se eliminan outliers.

## Límites

- Hay un único escenario y cinco repeticiones solicitadas.
- Un registro Memory ON no tiene resultado crudo.
- El tamaño de las parejas completas es cuatro, insuficiente para inferencia cuantitativa robusta.
- Los intervalos y la prueba reportados describen este lote, no validan una conclusión general.
- No se analizan aquí B1-B4 porque son experimentos de retrieval, no observaciones pareadas de navegación.

No se formulan conclusiones científicas sobre superioridad, mejora o empeoramiento.
