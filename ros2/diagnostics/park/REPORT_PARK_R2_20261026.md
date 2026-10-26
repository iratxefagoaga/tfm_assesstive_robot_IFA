# PARK R2: corrección y validación operativa — 26/10/2026

La PR #1 se integró en main antes de esta revisión. R1 se conserva: aceptación
8/10 N0 y 6/10 N1. R2 es otra versión y otra campaña completa, sin reemplazos.

## Cambios

Se elimina del perfil de navegación el renderizado de la cámara a 30 Hz y del
LiDAR alto a 15 Hz, sin consumidores de navegación. Se conservan enlaces,
geometría visual y colisiones, mapas y LiDAR bajo de 720 rayos a 15 Hz.
Las tolerancias internas pasan a 0,05 m y 0,10 rad: el sesgo observado de
0,132–0,161 m excedía el margen anterior. La aceptación independiente conserva
0,25 m/0,25 rad y frescura de 2 s; el guardián conserva 1 s. No se aumentan plazos,
no se cambia retrieval ni se suprimen abortos para hacer pasar los ensayos.

## Evidencia

Prueba estática: 30 scans, 363 retornos externos por scan, coincidencia con mapa
100 %, deriva despreciable y cierre limpio. Cualificación: N0 y N1 aceptados,
errores 0,0751 y 0,0383 m. Pérdida de scan inyectada: cancelación completa y
cierre limpio. Campaña prospectiva posterior: 10/10 N0 y 10/10 N1 aceptados,
denominador completo, sin reintentos, objetivos y poses Gazebo verificados,
sin scan_stale no inyectado, escalados de señal ni fallo de readiness.
Las 20 decisiones se recomputan desde los registros; IDs únicos; veinte
fingerprints N1 coinciden con la referencia congelada. Cinco checks offline
del CLI pasan. Las 29 pruebas unitarias y los veinte artefactos congelados
se comprueban aparte en la entrega.

## Interpretación

Se adopta R2 para la misión canónica local. No se declara eficacia científica,
seguridad física ni garantía de una tasa futura del 100 %. Cambiar ambos
componentes no aísla causalmente cuál explica cada mejora. No se asegura
soporte de otros escenarios ni instalación en otro ordenador. La raíz precisa
del fallo lifecycle o del apagado anterior no queda demostrada por su ausencia
en estas repeticiones. Los logs completos permanecen privados; se publican
código, perfil, protocolo y resúmenes numéricos. E1 original permanece intacto.
