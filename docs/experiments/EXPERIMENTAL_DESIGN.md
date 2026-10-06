# Experimental Evaluation Design - FROZEN

## Estado y alcance

E1, E2 y E3 estan FROZEN. Aprobacion humana final registrada: reviewer HUMAN_APPROVED, review.date 2026-10-05, review.approved=true. Se reutiliza status/review sin campos redundantes. Baseline publicado: 596f54c83c343c0a8e40e092478ec21783fd948a, scenario-home. No hay resultados de eficacia, navegaciones E1 ni evaluaciones definitivas E2/E3. Se conservan los datasets B1â€“B4, seed, mapas, poses, physics, Nav2, ranking, recomendador y branching BT. Ãšnico cambio productivo autorizado: observaciÃ³n de latencia y su campo CSV.

La colecciÃ³n tiene 50 memorias sintÃ©ticas: 44 con etiqueta episodic y seis semantic. La revisiÃ³n de contenido usa el seed versionado completo; no supone que tener observation/action/outcome/preference convierta una memoria en episÃ³dica. Una colecciÃ³n pequeÃ±a y consultas cercanas al seed no constituyen validaciÃ³n externa ni una muestra representativa de usuarios.

## HipÃ³tesis

H1: Memory-enabled navigation increases compliance with independently defined contextual/personalized navigation strategies compared with memory-disabled navigation.

E1 pregunta whether memory leads to an observed navigation strategy that is consistent with the independently defined contextual/personal preference. No demuestra mayor clearance, evitaciÃ³n fÃ­sica de mesa, circunnavegaciÃ³n del jardÃ­n ni reducciÃ³n de distancia/tiempo.

H2: Context-aware retrieval improves retrieval of memories judged relevant to the current user's context compared with semantic-only retrieval. Primaria Recall@3.

H3: Availability of relevant personalized evidence improves the accuracy of the selected navigation strategy compared with an ablated condition in which that evidence is unavailable. Los grupos contienen evidencia episÃ³dica y semantic/preference; no se denomina ablaciÃ³n estricta de episodic embeddings ni efecto exclusivo de episodios.

## E1: diseÃ±o y ground truth

HOME_01: U01/salon/navegacion/dormitorio; peticiÃ³n `navegar evitando la mesa`; GT west, evidencia M001. M001 documenta preferencia por espacio lateral y una acciÃ³n oeste previa exitosa. West operacionaliza coherencia espacial con esa preferencia. Spawn (2,-6), final (4,-4); regiÃ³n oeste x [-0.6,0.6], y [-4.6,-3.4]; corredor directo x [1.3,4.7], y [-6.7,-3.3]. La ruta sur actual no mide distancia a la mesa. El contexto semÃ¡ntico es mÃ¡s cercano al original, pero el objetivo fÃ­sico sigue siendo la ruta experimental sur.

PARK_01: U01/park/navegacion/salida_norte; peticiÃ³n histÃ³rica `repetir ruta oeste habitual rodeando el jardin central`; GT west, evidencia M013/M015 de salon/cocina. Se evalÃºa Ãºnicamente transferencia limitada del hÃ¡bito direccional oeste a otro contexto. No existe episodio PARK previo. El wording de la peticiÃ³n no valida rodear el jardÃ­n. M013 es semantic/preference. Spawn (0,-9), final (1,-9); regiÃ³n oeste x [-1.5,-0.6], y [-9.6,-8.4]; corredor directo x [-0.3,1.6], y [-9.6,-8.4]. No cambia geometrÃ­a.

N0 MEMORY_OFF conserva Nav2; N1 MEMORY_ON aÃ±ade memoria y eventualmente waypoint, con el mismo final. Diez repeticiones por condiciÃ³n y escenario: 40 ejecuciones futuras. No se ejecutan aquÃ­. Se aleatoriza orden intercalado con seed 20261004, lanzamientos frescos y IDs Ãºnicos. No existen realizaciones aleatorias emparejadas verificadas: E1 usa grupos independientes; repetir diez veces no crea diez contextos o usuarios distintos.

Primaria context_compliance = comparaciÃ³n de estrategia observada por trayectoria y GT congelado. Nunca usar expected_strategy, strategy_applied, fuente del recomendador o waypoint comandado como evidencia de ejecuciÃ³n. N0 puede cumplir; no se asigna cero por no tener memoria. success es secundaria. Time/distance/replanning son descriptivas/secundarias; no se interpretan automÃ¡ticamente como ventajas de memoria. Replanning cuenta publicaciones /plan menos la primera, no operaciones internas. min_clearance_m e intervention_appropriate siguen N/A.

## Clasificador de trayectoria

La regla anterior de una muestra oeste se sustituye por al menos tres muestras consecutivas dentro de west_region Y una duraciÃ³n desde la primera hasta la Ãºltima de al menos 0.2 segundos. Ambos requisitos evitan un punto aislado o un burst de muestras casi simultÃ¡neas. Se aplican a muestras originales; no se interpola para fabricar permanencia. /clock proporciona el timestamp de cada consulta TF map->base_link; su frecuencia efectiva depende del runtime, todavÃ­a no validado. La regla no presupone una frecuencia fija y el mÃ­nimo de tres muestras permite tasas normales desde 10 Hz. Una captura demasiado dispersa no se acredita artificialmente: se reporta no evaluable. La validaciÃ³n runtime de TF/sampling sigue pendiente en una fase futura autorizada.

LÃ­mites de regiÃ³n inclusivos; igualdad en duraciÃ³n aceptada con tolerancia numÃ©rica de 1e-9 segundos. Salir de la regiÃ³n reinicia contador y duraciÃ³n. Todas las comprobaciones globales se realizan antes de clasificar: frame map, capture complete, coordenadas finitas, timestamps estrictamente crecientes, gap <=1 s, segmento <=0.75 m, ambos endpoints <=0.6 m de spawn/final. Solo todos los puntos dentro del corredor directo permiten direct; cualquier otra trayectoria sin secuencia oeste vÃ¡lida es N/A. No se definen central/alternative por geometrÃ­a inexistente. Se comparte exactamente el clasificador para N0/N1. AMCL/TF map no es ground truth fÃ­sico absoluto; saltos o captura incompleta no equivalen a incumplimiento.

`capture_trajectory.py` escribe JSONL exclusivo de transforms al timestamp de /clock y marca TF_UNAVAILABLE; no manda goals ni cmd_vel. `evaluate_navigation.py` conserva raw, verifica identidad/success de la fila, utiliza cobertura auditada externamente y guarda hashes raw/GT/trace. Fixtures sintÃ©ticos admiten FROZEN con --synthetic; datos reales exigen FROZEN y revisiÃ³n aprobada. No mezclar sintÃ©ticos y observaciones reales.

## E2: relevancia y mÃ©tricas

Una memoria es relevant solamente si pertenece al mismo usuario y aporta informaciÃ³n Ãºtil para resolver la consulta por contexto directo o preferencia personal razonablemente transferible. Coincidencia de palabras, ubicaciÃ³n o etiqueta de salida no basta. Otros usuarios son distractores naturales de R0, nunca GT relevante personalizado. Los 20 casos tienen 50 juicios individuales (1000 en total), rationale de inclusiones/exclusiones y listas completas revisadas, en contextual_retrieval.json. Transferencias de aproximaciÃ³n/margen lateral se distinguen de preferencias exclusivamente de giro, velocidad o detenciÃ³n.

Regla temporal: una declaraciÃ³n explÃ­cita de preferencia actual prevalece sobre una acciÃ³n explÃ­citamente histÃ³rica para juzgar relevancia de esa preferencia, sin inventar fechas ni acciones actuales. M047 es relevante para las consultas U02 de directo cuando estÃ¡ despejado (Q10/Q11), por su preferencia actual; su acciÃ³n oeste antigua no acredita preferencia oeste vigente. El parser continÃºa produciendo west para aquella acciÃ³n: se documenta la diferencia de constructos, sin cambiar producciÃ³n. M046/M048 se excluyen como evidencia positiva de evitar una mesa presente: sus contextos histÃ³ricos son sin mesa. Las otras consultas no piden recuperar esos contextos histÃ³ricos.

R0 llama al retrieval productivo con user/location/task/goal=None y k=50; con contexto cero el score final es 0.90*cosine, que conserva el orden semÃ¡ntico. R1 usa contexto completo, filtro de usuario y scoring productivo intacto. E2 estima ese paquete de filtrado+ranking, no efectos independientes de sus componentes.

Primary Recall@3 = hits_at_3 / nÃºmero de IDs relevantes. Secondary Precision@3 = hits_at_3/3; MRR = media de reciprocal_rank de la primera memoria relevante en ranking completo; Hit@3 = al menos un relevante en top3. Rankings vacÃ­os dan cero; GT vacÃ­o/ranking duplicado se rechazan. No confundir MRR con MRR@3. Futura tabla conserva query_id, condition, retrieved_ids, ranks, scores semÃ¡ntico/contextual/final, relevant_ids, hits_at_3, recall_at_3, precision_at_3, reciprocal_rank y latency_ms; raw conserva ranking completo. La latencia E2 es offline retrieval, diferente de BT.

## E3: grupos, ablaciÃ³n y taxonomÃ­a

Cinco familias de evidencia para diez casos; el JSON conserva motivos individuales para cada miembro y auditorÃ­a de TODOS los IDs del mismo usuario fuera del grupo:

- U01_LATERAL_SPACE_WEST_HABIT: M001/M002/M004/M006/M007/M010/M012/M013/M015/M046. Incluye aproximaciÃ³n/margen lateral y contraste sin mesa porque revelan la misma preferencia; no solamente acciones con etiqueta west.
- U01_DIRECT_WHEN_SPACIOUS: M008/M014. Preferencia explÃ­cita de directo cuando hay paso amplio.
- U02_DIRECT_WHEN_CLEAR: M016/M017/M021/M023/M025/M027/M030/M047. Preferencia directo/central despejado; M047 aporta preferencia actual, no acciÃ³n oeste actual.
- U02_SMALL_EAST_DETOUR: M022/M028. DesvÃ­o pequeÃ±o este ante bloqueo central parcial; M026 detenciÃ³n/recalculo genÃ©rico no reconstruye esa preferencia especÃ­fica.
- U03_TABLE_DISTANCE_PREFERENCE: M031/M032/M033/M036/M037/M038/M040/M041/M044/M045/M048. Incluye M044 directo si lejos de mesa y M048 contraste sin mesa: no toda evidencia equivalente tiene la misma salida. Aproximaciones a objetos M034/M039/M042, velocidad/giro M035 y bloqueo temporal M043 representan otras tareas/condiciones.

M046/M048 son contraste que revela la preferencia y se retiran en P0 para impedir esa pista residual; esto NO los convierte en positivos E2 ante mesa presente. La auditorÃ­a no ha identificado evidencia sustancialmente equivalente residual fuera de los grupos propuestos. Los lÃ­mites requieren revisiÃ³n final humana; ninguna ausencia de contaminaciÃ³n textual prueba un efecto causal. Si una revisiÃ³n detecta residual equivalente, marcar ABLATION_CONTAMINATED y bloquear su evaluaciÃ³n primaria; el evaluador rechaza esos casos explÃ­citamente.

P1 usa ranking contextual completo -> top3 -> recomendador productivo exacto. P0 usa la misma colecciÃ³n y algoritmo; filtra TODOS los IDs del grupo ANTES de top3, conservando score/orden de supervivientes, y llama al mismo recomendador. Registra exactamente excluded_ids. Sin DELETE/UPDATE/reseed ni cambios de embeddings. No es ablaciÃ³n del campo episodic_embedding, que no interviene en ranking actual.

TaxonomÃ­a declarativa exacta en strategy_taxonomy.json: prioridad de substring `ruta oeste` -> west; `ruta central` -> central; `alternativa`/`desvio`/`desvÃ­o` -> alternative; en ausencia -> direct. Central != direct; alternative != west. M002 `Ruta alternativa oeste` produce alternative; E3_C02 se corrige a alternative aunque su significado direccional sea oeste. M041 `Evita ruta central` produce central pese a negaciÃ³n; M047 acciÃ³n antigua produce west pese a preferencia actual directa. No se arregla el parser ni se adaptan memorias. NingÃºn agrupamiento secundario implÃ­cito.

Primaria strategy_accuracy exacta, con denominador evaluable/eligible explÃ­cito. DEFAULT_SENSITIVE C04/C05: la acciÃ³n ancla es directo pero direct tambiÃ©n es fallback. Se conservan sus resultados descriptivos y source_explicit_direct; quedan fuera de H3 primaria hasta revisiÃ³n. No atribuir acierto de fallback a evidencia personal. Fallo de recomendaciÃ³n es N/A, no incorrecto automÃ¡tico; reportar cobertura. Secondary relevant_memory_used usa fuente realmente seleccionada y pertenencia al grupo; memory_hit_rate usa algÃºn miembro del grupo en top3; latency_ms incluye retrieval+recomendaciÃ³n offline; evaluable_coverage informa selecciÃ³n vÃ¡lida. En P0, ausencia de IDs ablacionados fuerza hit=0: es tambiÃ©n comprobaciÃ³n de manipulaciÃ³n, no una demostraciÃ³n independiente de H3.

## Latencia BT y CSV

En memory_observation_orchestrator.cpp, un MemoryPipelineLatency compartido en Context usa steady_clock. QueryMemory::onStart resetea SOLO observaciÃ³n y blackboard a N/A. Se inicia inmediatamente antes de la primera llamada memory_query->async_send_request; readiness previa a ese envÃ­o no entra. GetNavigationRecommendation termina despuÃ©s de publicar toda recomendaciÃ³n vÃ¡lida en blackboard e inmediatamente antes de SUCCESS. Incluye respuesta query, ticks entre fases y servicio de recomendaciÃ³n (que puede consultar otra vez); no incluye navegaciÃ³n, reloj /clock, goal dispatch ni control. Timers de timeout, ranking, estrategia y branching no cambian.

N0 siempre N/A. N1 medido solo si completa recomendaciÃ³n vÃ¡lida; query/recommendation timeout, excepciÃ³n, respuesta vacÃ­a/invÃ¡lida, halt o ausencia de dispatch/completion quedan N/A. Fallos posteriores de readiness/waypoint/final conservan la medida completa. Inicio y fin se capturan una sola vez por intento; finalizar navegaciÃ³n no sobreescribe latencia.

El esquema histÃ³rico tiene 35 columnas SIN memory_latency_ms. Se conservan esas 35 en el mismo orden y se aÃ±ade una ÃšNICA columna final memory_latency_ms: nuevo esquema de 36 campos comÃºn N0/N1. No se sustituye una mÃ©trica ni se duplica campo. Raw histÃ³rico 35 permanece inmutable y el procesador lo lee con latencia N/A; la escritura rechaza append a CSV histÃ³rico de header distinto sin tocarlo. Usar archivo nuevo para nueva campaÃ±a. Contratos verifican N0 N/A, Ã©xito N1 medido, fallos tempranos N/A, posteriores conservados, reloj monotÃ³nico/intervalo Ãºnico y headers Ãºnicos.

## EstadÃ­stica y missingness

Continuas: n, mean, sample std n-1, median, IQR con interpolaciÃ³n lineal. Binarias: n evaluable, count, percentage. Reportar datos ausentes, infraestructura, denominadores y cobertura; no imputar N/A como cero. CI/effect de una colecciÃ³n sintÃ©tica limitada no justifican generalizaciÃ³n a poblaciÃ³n ni potencia estadÃ­stica.

E1 INDEPENDIENTE por escenario: context_compliance primaria con Fisher exact bilateral y diferencia de riesgo N1-N0; Holm entre dos primarios HOME/PARK. Success secundaria Fisher exact. Time/distance/replanning secundarias condicionadas a SUCCESS, Mann-Whitney U con permutaciÃ³n bilateral reproducible y Cliff delta; no inferir menor tiempo/distancia por hipÃ³tesis ni interpretar U automÃ¡ticamente como diferencia de medianas. Holm entre secundarios por escenario. Reportar efectos, tamaÃ±os pequeÃ±os y cobertura; no pooling ciego entre escenarios ni pairing por igual Ã­ndice de repeticiÃ³n. No comparar latencia N0 N/A contra N1.

E2 PAREADO por query_id: Recall@3 primaria, test bilateral de permutaciÃ³n de signos sobre diferencias R1-R0; mismas consultas en ambos mÃ©todos, hipÃ³tesis nula de intercambiabilidad de condiciÃ³n dentro de consulta. Precision@3 y reciprocal_rank/MRR mismo test pareado; Hit@3 McNemar exact (binomial bilateral sobre discordancias). E3 PAREADO por case_id: strategy_accuracy binaria McNemar exact P1/P0; secondary relevant_memory_used/memory_hit/evaluable_coverage McNemar exact, latency permutaciÃ³n pareada de signos. No usar Mann-Whitney para E2/E3. Usar todas las permutaciones si <=9999, si no muestreo reproducible; seed 20261005. Casos sin ambas observaciones evaluables/eligible se reportan como pairs_missing_or_ineligible, no desaparecen.

Efectos E2/E3: diferencia media o de riesgo segunda-primera y CI percentil de bootstrap PAREADO 95%, 9999 remuestras, seed 20261005. Es incertidumbre empÃ­rica descriptiva en 20/10 casos, especialmente frÃ¡gil con pocas discordancias; no se vende como CI de eficacia poblacional. P=1 cuando no hay diferencias/discordancias. Holm en cada familia secundaria por experimento; H1/H2/H3 son preguntas distintas y no se selecciona la favorable. No buscar significaciÃ³n ni ocultar ineligibilidad; no hay power analysis. Orden de mÃ©todos contrabalanceado determinÃ­sticamente por caso antes de ejecuciÃ³n futura; modelo offline/cacheado, declarar warm/cold y no atribuir latencia exclusivamente al mÃ©todo sin controlar carga/cachÃ©.

## Infraestructura, preservaciÃ³n y ejecuciÃ³n futura

Una ejecuciÃ³n principal y mÃ¡ximo una repeticiÃ³n limpia por fallo infra demostrado; no retry por fallo de navegaciÃ³n. Reincidencia -> INFRASTRUCTURE_BLOCKED. CLEANUP_FAILURE bloquea siguiente run. Mantener cada intento/clasificaciÃ³n y residuos; seÃ±al al propietario, esperar hijos, sin SIGKILL normal. No decidir exclusiones mirando efectos. El manifiesto E1 planifica, jamÃ¡s lanza procesos: --execute sigue bloqueado hasta futura validaciÃ³n autorizada de captura/mediciÃ³n integrada.

E2/E3 ejecuciÃ³n futura exige FROZEN, review.approved, reviewer/date y autorizaciÃ³n de campaÃ±a. PGOPTIONS default_transaction_read_only=on, count y canonical_memory_fingerprint_v2 antes/despuÃ©s; nunca store_memory. Outputs exclusivos en /tmp con raw/processed/manifest/fingerprints, hashes GT/config/baseline y auditorÃ­a. Fingerprints de referencia (Ãºltima validaciÃ³n anterior, NO nueva comprobaciÃ³n si DB inaccesible): 50 filas; logical 46ea5969b3047c1eb3bc526bb08fbb11b8ddac6f77f18a97e362fcdba9e97898; embeddings 8f9bf33815930952e3a7ee169d1edb4c7027d5cb5c77c173a3b1a16bb7af2599.

PreparaciÃ³n Ãºnicamente, desde raÃ­z con ROS/overlay y .venv Linux:

```bash
.venv/bin/python -m scripts.experiments.run_evaluation E1 --output /tmp/e1_plan_unique.json
.venv/bin/python -m scripts.experiments.run_evaluation E2 --output /tmp/e2_review_unique.json
.venv/bin/python -m scripts.experiments.run_evaluation E3 --output /tmp/e3_review_unique.json
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest scripts/experiments/tests
```

AnÃ¡lisis futuro usa processed JSON rows y `run_evaluation analyze`; detecta E1 independiente o E2/E3 pareado por identidad. --synthetic obligatorio para fixtures y nunca mezcla real/sintÃ©tico. AIRPORT permanece EXPLORATORY_DYNAMIC_SCENARIO fuera de E1 principal; no depuraciÃ³n ni tuning nuevos. No contacto remoto, stage, commit, push, reset ni cambio de rama en esta revisiÃ³n.

## Human freeze review - APPROVED

Estado FROZEN; reviewer HUMAN_APPROVED; review.date 2026-10-05. La aprobacion humana final conserva todas las decisiones actuales: HOME/PARK west y transferencia limitada, proxy oeste, clasificador de tres muestras consecutivas y 0.2 s, politica/listas E2, grupos P0/P1, taxonomia exacta y M002=alternative, CSV de 36 columnas, estadistica y manejo de muestra insuficiente. No hay nueva auditoria conceptual.

C04/C05 permanecen DEFAULT_SENSITIVE, fuera de H3 primaria, solo secundarios/exploratorios. Los restantes casos mantienen las reglas predefinidas de evaluabilidad. AIRPORT sigue EXPLORATORY_DYNAMIC_SCENARIO, excluido de la evaluacion principal. No se amplian los claims.

Los cinco artefactos congelados y sus SHA-256 constan en experiments/configs/freeze_manifest.json. El manifest registra timestamp, branch, HEAD base, aprobacion humana y baseline DB/checkpoint; se calcula despues de finalizar los artefactos y se verifican los hashes nuevamente al cierre.

## Validation checkpoint

Checkpoint previo al freeze: build PASS; BT 70/70, backend 17/17, ROS contract 17/17, experimental 54/54: 158 PASS / 0 FAIL. Sintaxis, JSON, whitespace y secret scan PASS. DB READ-ONLY verificada antes/despues: count 50 y ambos fingerprints de referencia coincidentes. Esta fase administrativa no vuelve a consultar DB ni repite suites de backend/ROS/BT.

La validacion posterior al freeze ejecuta solo tests experimentales y checks estaticos; resultados y reverificacion de hashes se registran en el manifest. Se acepta FROZEN con aprobacion completa y se rechazan aprobaciones incompletas, sin modificar los guards productivos. No se ejecutan campanas ni Gazebo.

NEXT STEP: EXECUTE E2 AND E3 en el siguiente bloque autorizado. No ejecutar E1/E2/E3 en este bloque.
