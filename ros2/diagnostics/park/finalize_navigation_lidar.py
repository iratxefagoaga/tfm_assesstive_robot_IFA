"""Conserve completed engineering evidence and prepare a simulation-only profile."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
from diagnose import verify_sensor_overlay,digest,ros_environment
from analyze_localization import compare

def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--gate',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);a=p.parse_args();here=Path(__file__).parent
    status=json.loads((a.gate/'status.json').read_text());rows=json.loads((a.gate/'results.json').read_text());passed=status['status']=='PASSED_SIMULATION_ONLY_PHYSICAL_MOUNT_UNVALIDATED' and len(rows)==4 and all(r['accepted'] for r in rows)
    protocol=json.loads((a.gate/'protocol.json').read_text());source_verified=all(digest(here/n)==sha for n,sha in protocol['source_hashes'].items())
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(here),'-p','test_diagnose.py','-v'],capture_output=True,text=True)
    verify=subprocess.run([sys.executable,str(a.code_root/'scripts/experiments/verify_final_results.py')],capture_output=True,text=True)
    processes=subprocess.run(['ps','-eo','pid,ppid,comm'],capture_output=True,text=True,check=True).stdout.splitlines()
    names={'gz','ruby','planner_server','controller_server','map_server','amcl','bt_navigator','lifecycle_manag','parameter_bridg'}
    residue=[r for r in processes[1:] if r.split()[-1] in names]
    containers=subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,check=True).stdout.splitlines()
    fingerprints=[]
    inputs=[Path('/tmp')/name for name in ['park_localization_pair_20261025_01','park_localization_cyclone_20261025_01','park_additional_lidar_overlay_20261025_01','park_additional_lidar_overlay_20261025_02','park_additional_lidar_static_20261025_01','park_additional_lidar_static_20261025_02',a.gate.name]]
    for directory in inputs:
        for path in directory.glob('*/db_*.json'):fingerprints.append({'path':str(path),'value':json.loads(path.read_text())})
    values=[r['value'] for r in fingerprints];db_ok=len(values)==12 and all(v==values[0] and v['row_count']==50 for v in values)
    analysis={}
    for case in sorted(a.gate.glob('[0-9][0-9]_*')):
        mode=case.name.split('_',1)[1];directory=case/mode;truth=[json.loads(l) for l in (directory/'physical_pose.jsonl').read_text().splitlines() if l.strip()];observations=[json.loads(l) for l in (directory/'localization.jsonl').read_text().splitlines() if l.strip()]
        analysis[case.name]={kind:compare(truth,observations,kind) for kind in ['odom','amcl']}
    default_rmw=subprocess.run([sys.executable,'-c','from rclpy.utilities import get_rmw_implementation_identifier; print(get_rmw_implementation_identifier())'],env=ros_environment(a.code_root),capture_output=True,text=True)
    final={'gate_status':status,'tests_returncode':tests.returncode,'tests_output':tests.stdout+tests.stderr,'scientific_verify_returncode':verify.returncode,'scientific_verify_output':verify.stdout+verify.stderr,'source_hashes_match_executed_gate':source_verified,'fingerprints':fingerprints,'twelve_fingerprints_equal':db_ok,'ros_gazebo_residue':residue,'running_containers':containers,'global_default_rmw_observed':default_rmw.stdout.strip(),'physical_mount_measured':False}
    memory_sources_ok=all(r['result'][0].get('source_memory')=='M013' and r['result'][0].get('retrieved_strategy')=='west' for r in rows if r['mode']=='memory')
    checks_ok=passed and source_verified and db_ok and memory_sources_ok and not tests.returncode and not verify.returncode and not default_rmw.returncode and not residue and not containers
    a.archive.mkdir(parents=True,exist_ok=True)
    if (a.archive/'final_checks.json').exists():raise RuntimeError('Refusing to replace final verification')
    (a.archive/'final_checks.json').write_text(json.dumps(final,indent=2)+'\n');(a.archive/'localization_analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
    if not checks_ok:print('Final checks failed; profile not prepared');return 1
    verify_sensor_overlay(a.profile);runtime=a.archive/'runtime_profile';shutil.copytree(a.profile,runtime)
    (runtime/'simulation_acceptance.json').write_text(json.dumps({'status':status['status'],'gate_protocol_sha256':digest(a.gate/'protocol.json'),'gate_results_sha256':digest(a.gate/'results.json'),'physical_hardware_validated':False,'accepted_runs':4},indent=2)+'\n');verify_sensor_overlay(runtime)
    command=f'/usr/bin/python3 {here}/run_navigation_lidar_profile.py --code-root {a.code_root} --profile {runtime} --mode memory --output /tmp/park_additional_lidar_user_run_NEW'
    (a.archive/'RUN_SIMULATION.txt').write_text('SIMULATION ONLY; proposed additional sensor; physical mount unverified.\nChoose a new output path for each run.\n'+command+'\n')
    table='\n'.join(f'| {i+1} | {r["mode"]} | {r["physical_goal_distance_m"]:.4f} | {r["physical_yaw_error_rad"]:.4f} | limpio |' for i,r in enumerate(rows))
    report=f'''# PARK: perfil con LiDAR adicional — 25/10/2026

**Validado localmente en simulación: un N0 y tres N1 completos. Hardware físico no validado.**
No es una nueva tasa científica de éxito ni una demostración de seguridad general.
El modelo original y E1 permanecen intactos; la máscara anterior sigue rechazada.

## Diagnóstico que motivó el cambio

El LiDAR original ya existía: 720 rayos, 360 grados, 15 Hz, rango 0,12–12 m,
pose nominal (0,28;0;0,92) respecto al modelo. En el arranque original se
registraron 270 retornos propios cercanos y ningún retorno externo lejano.
La máscara anterior dejaba inicialmente solo diez retornos externos y no bastó.

En el par sincronizado con Cyclone DDS, la odometría presentó errores máximos
de 0,079 y 0,081 m frente a Gazebo, mientras AMCL alcanzó 0,976 y 0,895 m.
Se emparejaron poses por tiempo simulado, con diferencia máxima permitida 0,05 s
y diferencias reales <=0,009 s. El origen de odometría se trasladó por el spawn
conocido (0,-9), sin aplicar dos veces ese desplazamiento a AMCL.
Esto localiza una degradación importante de la estimación global en esos dos
recorridos; no demuestra una causa exclusiva para los seis abortos históricos.

El primer intento de esta fase con Fast DDS no publicó AMCL ni map→odom antes
de fallar readiness: sin goals, cierre limpio. Una sonda TF posterior a su cierre
no es evidencia válida de ausencia de TF durante el ensayo. En el intento Cyclone,
una sonda durante la ejecución sí confirmó base_link→lidar_link, odom→lidar_link
y map→base_link. Un par limpio no basta para atribuir causalidad al middleware.

## Perfil implementado

Se conserva el sensor original y se añade un LiDAR genérico propuesto:
pose respecto al modelo (0,33;0;0,08) m, y respecto a base_link (0,33;0;-0,12) m.
SDF y xacro comparten esa transformación. Se incluye una carcasa visual cilíndrica
de radio 0,025 m y altura 0,03 m, dentro de la huella planar existente.
Es un diseño simulado, no una medida de una silla existente ni un producto
comercial validado. Su punto más bajo queda a 0,065 m del suelo plano nominal;
no se ha validado para bordillos, irregularidades o montaje en una silla real.
Se conserva la geometría de colisión original; no se modela una colisión específica
de la nueva carcasa. La validación física debe incluir esa limitación.

El puente publica `/navigation_scan`. El filtro transforma únicamente la etiqueta
de frame al enlace correspondiente y elimina con NaN los impactos dentro de la
huella propia, calculados desde la pose conocida del sensor. No sustituye por
distancias largas ni permite ver detrás de las oclusiones. `/scan_fixed` alimenta
la cadena Nav2 existente. El orquestador N0/N1 original mantiene decisiones,
servicios reales, readiness y manejo del waypoint; la memoria no envía cmd_vel.
La salida inesperada del puente o filtro provoca cierre del lanzador del perfil.

El primer ensayo estático detectó 363 retornos externos por scan, con 100 % de
coincidencia a <=0,15 m de celdas ocupadas del mapa, pero falló el cierre del wrapper
`ros2 run`. Se conservó el fallo y se cambió el puente a un Node administrado
directamente por launch. La repetición pasó: 30 scans, los mismos 363 retornos y
100 % de coincidencia, deriva planar ~1,27e-17 m y cierre limpio sin residuos.

El perfil usa Cyclone DDS y limita llvmpipe a dos hilos. Se instalaron ocho
paquetes nuevos, sin actualizar ni eliminar paquetes. El middleware global
observado sigue siendo `{default_rmw.stdout.strip()}`. La selección de Cyclone
se limita a los procesos del perfil. El inventario previo bruto tuvo un error de
formato; se conserva la nota y una reconstrucción excluyendo los ocho paquetes
nuevos, junto con el inventario posterior. No se presenta como snapshot original.

Se fija una tolerancia interna más estricta de 0,15 m/0,15 rad para reservar
margen de localización dentro de la aceptación física de 0,25 m/0,25 rad.
Los demás parámetros de Nav2, mapas, mundos y plazos se conservan. El cambio
incluye sensor, filtrado, middleware, límite de hilos y tolerancia: estos ensayos
no permiten atribuir el resultado exclusivamente a uno de esos componentes.

## Aceptación fijada antes de ejecutar

Un N0 seguido de tres N1; sin reintentos. Todos los objetivos aplicables deben
SUCCEEDED, error físico final <=0,25 m y <=0,25 rad, ningún fallo de readiness,
confirmación de acción o cierre, y DB idéntica antes/después. Se detiene ante
la primera aceptación fallida. Medición independiente con poses Gazebo, además
de AMCL/odom/TF y resúmenes de scan; sin rosbag completo ni captura de /clock.

| Ensayo | Modalidad | Error físico final (m) | Error de orientación (rad) | Cierre |
|---|---|---:|---:|---|
{table}

Los tres N1 utilizan memoria real M013/west y alcanzan waypoint y destino.
No se han insertado/actualizado/borrado filas ni regenerado embeddings.
Los doce fingerprints de esta fase coinciden: 50 registros, hashes v2 idénticos.
Los contenedores regresan a su estado detenido y no quedan residuos ROS/Gazebo.
El verificador científico pasa para veinte artefactos e inputs congelados.
Los tests y los hashes del código ejecutado se guardan en final_checks.json.

## Uso y límites

Perfil autocontenido privado: `{runtime}`.
Ejecutor: `run_navigation_lidar_profile.py`. La receta completa está en
`{a.archive}/RUN_SIMULATION.txt`; exige directorio de salida nuevo y comprueba
hashes, aceptación previa y llegada física de cada ejecución. Siempre inicia
Gazebo: no es un bringup para hardware real. El modo memory restaura el estado
del contenedor original y exige el fingerprint congelado.

PARK/N1 original sigue siendo 4/10 éxitos de acción en E1. Estas cuatro pruebas
de ingeniería no lo reemplazan ni acreditan una tasa futura del 100 %.
La corrección queda disponible como perfil de simulación, sin sobrescribir el
modelo predeterminado. El despliegue en silla física sigue pendiente de validar
modelo comercial, montaje, oclusiones, colisiones y terreno. No se inventan
medidas físicas para declarar esa fase cerrada.
'''
    (here/'REPORT_ADDITIONAL_LIDAR_20261025.md').write_text(report)
    current={'date':'2026-10-25','status':'SIMULATION_PROFILE_VALIDATED_PHYSICAL_ADOPTION_BLOCKED','production_fix_adopted':False,'simulation_profile_usable':True,'sensor_mask_candidate':'REJECTED_FOR_ADOPTION','additional_lidar_profile':str(runtime),'accepted_simulation_runs':4,'physical_hardware_validated':False,'scientific_E1_park_N1':'UNCHANGED: 4/10 action successes','report':'REPORT_ADDITIONAL_LIDAR_20261025.md'}
    (here/'PRODUCTION_STATUS.json').write_text(json.dumps(current,indent=2)+'\n')
    for source in inputs:shutil.copytree(source,a.archive/source.name)
    code=a.archive/'diagnostic_code';code.mkdir()
    for source in here.iterdir():
        if source.suffix in {'.py','.md','.json'}:shutil.copy2(source,code/source.name)
    manifest={str(f.relative_to(a.archive)):hashlib.sha256(f.read_bytes()).hexdigest() for f in a.archive.rglob('*') if f.is_file()}
    (a.archive/'archive_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'status':current['status'],'files_archived':len(manifest),'runtime_profile':str(runtime),'report':str(here/'REPORT_ADDITIONAL_LIDAR_20261025.md')}));return 0
if __name__=='__main__':raise SystemExit(main())
