"""Read-only audit and isolated diagnostic pilot; never edits frozen inputs."""
import argparse,csv,hashlib,json,math,os,random,re,shlex,signal,subprocess,time,uuid
from contextlib import contextmanager
from arrival_reference import reference
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
TOPICS=['/clock','/tf','/tf_static','/odom','/scan_fixed','/amcl_pose','/cmd_vel','/plan',
        '/local_costmap/costmap','/global_costmap/costmap','/navigate_to_pose/_action/status',
        '/follow_path/_action/status','/compute_path_to_pose/_action/status']
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def summarize_log(text):
    # Keep only diagnostic categories, never arbitrary environment/DB messages.
    patterns={'control_patience':r'Controller patience exceeded','progress':r'Failed to make progress',
              'planning':r'Failed to create plan|failed to plan from',
              'goal_abort':r'Goal failed','readiness':r'readiness (?:response )?failed|Nav2 readiness failed','sensor_fault':r'Sensor guard failed:',
              'action_ack_timeout':r'Timed out while waiting for action server to acknowledge goal request',
              'cleanup_escalation':r'SIGKILL|failed to terminate','abnormal_exit':r'process has died.*exit code -(?:6|7|8|9|11)\b|BRIDGE_FAILURE:',
              'tf_extrapolation':r'extrapolation|extrapolat'}
    return {k:len(re.findall(p,text,re.I)) for k,p in patterns.items()}
def stage(row):
    if row.get('waypoint_nav2_result')=='ABORTED':
        if row.get('final_goal_nav2_result')!='NOT_SENT':raise ValueError('Failed waypoint with final goal sent')
        return 'waypoint'
    if row.get('waypoint_nav2_result')=='SUCCEEDED' and row.get('final_goal_nav2_result')=='ABORTED':return 'final'
    return 'other'
def vertical_interval(link,geom):
    pose=list(map(float,link.findtext('pose','0 0 0 0 0 0').split())); z=pose[2]
    if geom.find('box') is not None:h=float(geom.findtext('box/size').split()[2])
    elif geom.find('cylinder') is not None:h=float(geom.findtext('cylinder/length'))
    else:return None
    return z-h/2,z+h/2
def audit(root,runs,out):
    selected=root/'experiments/results/final/E1/final_selected_observations.json'
    rows=json.loads(selected.read_text());result={'kind':'OFFLINE_DIAGNOSTIC','inputs':{str(selected):digest(selected)},'park_n1':[]}
    for r in rows:
        if r['scenario']!='park' or r['memory_condition']!='N1':continue
        m=re.search(r'job(\d+)_attempt(\d+)',r['run_id']);base=runs/f'job_{m[1]}'/f'attempt_{m[2]}'
        log=(base/'runtime.log').read_text(errors='replace'); result['inputs'][str(base/'runtime.log')]=digest(base/'runtime.log')
        pts=[json.loads(l) for l in (base/'trajectory.jsonl').read_text().splitlines() if l.strip()]
        jumps=[math.hypot(b['x']-a['x'],b['y']-a['y']) for a,b in zip(pts,pts[1:])]
        nav_start=log.find('sent to /navigate_to_pose')
        # Categories after the first goal are separate from startup diagnostics.
        after=log[nav_start:] if nav_start>=0 else ''
        result['park_n1'].append({'run_id':r['run_id'],'success':r['success'],'stage':stage(r),
          'waypoint':r['waypoint_nav2_result'],'final':r['final_goal_nav2_result'],'source_memory':r['source_memory'],
          'diagnostics_after_first_goal':summarize_log(after),'first_goal_log_found':nav_start>=0,
          'max_map_step_m':max(jumps,default=0),'map_steps_over_075m':sum(j>.75 for j in jumps),
          'odom_distance_m':r['distance_m']})
    robot=root/'ros2/src/wheelchair_gazebo/models/wheelchair/model.sdf'; world=root/'ros2/src/wheelchair_gazebo/models/park/model.sdf'
    for p in [robot,world,root/'ros2/src/wheelchair_navigation/maps/park.yaml',root/'ros2/src/wheelchair_navigation/maps/park.pgm']:
        result['inputs'][str(p)]=digest(p)
    model=ET.parse(robot).getroot().find('model');lidar=model.find("link[@name='lidar_link']")
    z=float(lidar.findtext('pose').split()[2]);sensor=lidar.find('sensor');max_range=float(sensor.findtext('ray/range/max'))
    objects=[]
    from PIL import Image
    map_image=Image.open(root/'ros2/src/wheelchair_navigation/maps/park.pgm')
    for link in ET.parse(world).getroot().findall('model/link'):
        if link.get('name')=='floor':continue
        col=link.find('collision/geometry');vis=link.find('visual/geometry');v=vertical_interval(link,vis);c=vertical_interval(link,col)
        pose=list(map(float,link.findtext('pose','0 0 0 0 0 0').split())); x,y=pose[:2]
        px=int((x+15)/.05);py=map_image.height-1-int((y+12)/.05)
        val=map_image.getpixel((px,py)) if 0<=px<map_image.width and 0<=py<map_image.height else None
        objects.append({'name':link.get('name'),'visual_z_interval':v,'collision_z_interval':c,
         'horizontal_lidar_intersects_visual_at_nominal_z':v[0]<=z<=v[1],
         'map_value_at_object_center':val,'center_distance_from_spawn_m':math.hypot(x,y+9)})
    result.update(lidar_nominal_model_z_m=z,lidar_max_range_m=max_range,objects=objects,
      geometry_conclusion='Static planar-height mismatch; not a runtime causal proof. Robot roll/pitch and world pose may alter the real scan plane.')
    (out/'offline_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
def ros_environment(root):
    # Source only trusted installed setup files; capture environment without displaying it.
    cmd='source /opt/ros/jazzy/setup.bash && source '+shlex.quote(str(root/'ros2/install/setup.bash'))+' && env -0'
    r=subprocess.run(['bash','-c',cmd],capture_output=True,check=True)
    return dict(x.split('=',1) for x in r.stdout.decode().split('\0') if '=' in x)
def fingerprint(root,env):
    r=subprocess.run([str(root/'.venv/bin/python'),'-m','scripts.memory.fingerprint_memory'],cwd=root,env=env,capture_output=True,text=True,timeout=40)
    try:data=json.loads(r.stdout)
    except ValueError:raise RuntimeError('Fingerprint produced no safe JSON')
    if r.returncode:raise RuntimeError('Fingerprint failed: '+str(data.get('error_type','unknown')))
    return data
def load_database_env(path,env,postgres_aliases=False):
    allowed={'MEMORY_DB_HOST','MEMORY_DB_PORT','MEMORY_DB_NAME','MEMORY_DB_USER','MEMORY_DB_PASSWORD'}
    aliases={f'POSTGRES_{a}':f'MEMORY_DB_{b}' for a,b in [('HOST','HOST'),('PORT','PORT'),('DB','NAME'),('USER','USER'),('PASSWORD','PASSWORD')]} if postgres_aliases else {}
    if path.exists():
        for line in path.read_text().splitlines():
            line=line.strip()
            if line.startswith('export '):line=line[7:].lstrip()
            key,sep,value=line.partition('=');key=aliases.get(key.strip(),key.strip())
            if not sep or key not in allowed:continue
            try:parts=shlex.split(value,comments=True,posix=True)
            except ValueError:raise RuntimeError('Invalid quoting for private variable '+key) from None
            if len(parts)!=1:raise RuntimeError('Unsupported private value format for '+key)
            if '${' in parts[0]:raise RuntimeError('Variable interpolation is not supported for '+key)
            env[key]=parts[0]
    return env
def load_private(root,env):return load_database_env(root/'.env',env)
def verify_sensor_overlay(path):
    manifest=json.loads((path/'overlay_manifest.json').read_text())
    if manifest.get('status')!='ISOLATED_DIAGNOSTIC_OVERLAY':raise RuntimeError('Unverified sensor overlay')
    candidate=path/'share/wheelchair_gazebo/models/wheelchair/model.sdf'
    if digest(candidate)!=manifest.get('candidate_sha256'):raise RuntimeError('Sensor candidate changed after validation')
    for relative,sha in manifest.get('extra_sha256',{}).items():
        if digest(path/relative)!=sha:raise RuntimeError('Sensor profile resource changed after validation')
@contextmanager
def existing_memory_database(out):
    """Use only the known existing container; never initialize or recreate a DB."""
    name='tfm_memory_postgres'
    info=json.loads(subprocess.run(['docker','inspect',name],capture_output=True,text=True,check=True).stdout)[0]
    was_running=info['State']['Running'];values=dict(v.split('=',1) for v in info['Config']['Env'] if '=' in v)
    bindings=info['HostConfig']['PortBindings'].get('5432/tcp',[])
    if len(bindings)!=1:raise RuntimeError('Ambiguous original memory container port')
    db={'MEMORY_DB_HOST':'localhost','MEMORY_DB_PORT':bindings[0]['HostPort']}
    for k,v in [('USER','USER'),('PASSWORD','PASSWORD'),('DB','NAME')]:db['MEMORY_DB_'+v]=values['POSTGRES_'+k]
    state={'container':name,'initially_running':was_running,'new_container_created':False}
    try:
        if not was_running:subprocess.run(['docker','start',name],capture_output=True,check=True,timeout=30)
        for _ in range(30):
            p=subprocess.run(['docker','exec',name,'pg_isready','-U',values['POSTGRES_USER'],'-d',values['POSTGRES_DB']],capture_output=True,timeout=5)
            if p.returncode==0:break
            time.sleep(1)
        else:raise RuntimeError('Original memory database unavailable')
        yield db
    finally:
        if not was_running:
            subprocess.run(['docker','kill','--signal=SIGINT',name],capture_output=True,check=True,timeout=10)
            try:
                subprocess.run(['docker','wait',name],capture_output=True,check=True,timeout=30);state['restored_stopped_state']=True
            except subprocess.TimeoutExpired:state['restored_stopped_state']=False
        (out/'database_lifecycle.json').write_text(json.dumps(state,indent=2)+'\n')
def owned_descendants(pid):
    result=[]
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            text=path.read_text();ppid=int(text[text.rfind(')')+2:].split()[1])
            if ppid==pid:result.append(int(path.parent.name))
        except (OSError,ValueError,IndexError):pass
    return result+sum((owned_descendants(p) for p in result),[])
def finish(proc):
    if proc.poll() is None:
        if not getattr(proc,'park_shutdown_requested',False):
            proc.send_signal(signal.SIGINT);proc.park_shutdown_requested=True
        try:proc.wait(timeout=30)
        except subprocess.TimeoutExpired:return False
    return True
def resource_sample(pids):
    sample={'wall_monotonic':time.monotonic(),'pressure':{},'processes':[]}
    for kind in ['cpu','memory','io']:
        sample['pressure'][kind]=Path('/proc/pressure',kind).read_text().strip()
    sample['memory']={line.split(':')[0]:line.split(':')[1].strip() for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','SwapFree:'))}
    for pid in pids:
        try:
            values=dict(line.split(':',1) for line in Path('/proc',str(pid),'status').read_text().splitlines() if ':' in line)
            sample['processes'].append({'pid':pid,**{k:values[k].strip() for k in ['Name','VmRSS','Threads'] if k in values}})
        except OSError:pass
    return sample

def pilot(root,out,modes,private_env=None,database_env=None,recording_profile='full',sensor_overlay=None,observe_truth=False,transport=None,render_threads=None,observe_localization=False,rmw=None,launch_file=None):
    env=load_private(root,ros_environment(root));env.update(PGOPTIONS='-c default_transaction_read_only=on',HF_HUB_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    if rmw:
        if rmw not in {'rmw_fastrtps_cpp','rmw_cyclonedds_cpp'}:raise ValueError('Unsupported diagnostic middleware')
        env['RMW_IMPLEMENTATION']=rmw
    if transport:
        if transport not in {'DEFAULT','UDPv4'}:raise ValueError('Unsupported diagnostic DDS transport')
        env['FASTDDS_BUILTIN_TRANSPORTS']=transport
    if render_threads is not None:
        if render_threads not in {1,2}:raise ValueError('Unsupported diagnostic renderer thread limit')
        env['LP_NUM_THREADS']=str(render_threads)
    if private_env:
        load_database_env(private_env,env)
    if database_env:env.update(database_env)
    probe=subprocess.run(['/usr/bin/python3','-c','import rclpy,rosbag2_py; from ament_index_python.packages import get_package_share_directory; print(get_package_share_directory("wheelchair_gazebo"))'],env=env,capture_output=True,text=True)
    if probe.returncode:raise RuntimeError('ROS/rosbag2 dependency preflight failed')
    if str(root/'ros2/install') not in probe.stdout:raise RuntimeError('Installed ROS overlay does not belong to frozen checkout')
    # Refuse to start over an unrelated existing simulator/navigation stack.
    ps=subprocess.run(['ps','-eo','comm='],capture_output=True,text=True,check=True).stdout.splitlines()
    if any(p.strip() in {'gz','ruby','planner_server','controller_server','bt_navigator','amcl','map_server','gzserver','gzclient'} for p in ps):
        raise RuntimeError('Existing simulator/Nav2 process found; refusing to interfere')
    before=None
    if 'memory' in modes:
        before=fingerprint(root,env);(out/'db_before.json').write_text(json.dumps(before,indent=2)+'\n')
        frozen=json.loads((root/'experiments/configs/evaluation_design.json').read_text())['memory_fingerprint']
        if before!=frozen:raise RuntimeError('DB is not the frozen reference; no goals sent')
    order=list(modes);random.Random(20261025).shuffle(order)
    topics=TOPICS if recording_profile=='full' else [t for t in TOPICS if t not in {'/clock','/local_costmap/costmap','/global_costmap/costmap'}]
    if sensor_overlay:
        verify_sensor_overlay(sensor_overlay)
    protocol={'kind':'DIAGNOSTIC_PILOT_NOT_EFFICACY','repetitions_per_mode':1,'order':order,'seed':20261025,
      'geometry':'original collisions/maps; masked robot visuals' if sensor_overlay else 'original','retries':0,'stop_on_cleanup_or_readiness_failure':True,'topics':topics if recording_profile!='none' else [],'recording_profile':recording_profile,'sensor_overlay':str(sensor_overlay) if sensor_overlay else None,
      'limitation':'Explicit sequence uses diagnostic client; original N0/N1 use frozen C++ orchestration. Not a timing-identical ablation.'}
    (out/'pilot_protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    results=[]
    try:
        for index,mode in enumerate(order):
            if sensor_overlay:verify_sensor_overlay(sensor_overlay)
            run=out/mode;run.mkdir();ident='park_diag_'+uuid.uuid4().hex
            e=env.copy();e.update(ROS_DOMAIN_ID=str(91+index),GZ_PARTITION=ident,ROS_LOCALHOST_ONLY='1',PARK_DIAGNOSTIC_OUTPUT=str(run/'sequence_result.json'),ROS_LOG_DIR=str(run/'ros_logs'))
            if sensor_overlay:e['AMENT_PREFIX_PATH']=str(sensor_overlay)+os.pathsep+e.get('AMENT_PREFIX_PATH','')
            if launch_file:
                if mode not in {'direct','memory'}:raise ValueError('Proposed launch profile supports original N0/N1')
                e['PARK_LIDAR_CONDITION']=mode
                e['PARK_SENSOR_HEALTH_OUTPUT']=str(run/'sensor_health.jsonl')
                cmd=['ros2','launch',str(launch_file),'gui:=false','run_id:='+ident,'result_csv:='+str(run/'result.csv')]
            elif mode=='explicit_waypoint':cmd=['ros2','launch',str(HERE/'stack.launch.py')]
            else:cmd=['ros2','launch','wheelchair_assistive_bt',f'park_{"n0" if mode=="direct" else "n1"}.launch.py','gui:=false','run_id:='+ident,'result_csv:='+str(run/'result.csv')]
            bag=None;proc=None;truth=None;localization=None;desc=[]
            with (run/'runtime.log').open('w') as log,(run/'bag.log').open('w') as baglog,(run/'resources.jsonl').open('w',buffering=1) as resource_log:
                try:
                    if observe_truth:truth=subprocess.Popen(['/usr/bin/python3',str(HERE/'truth_observer.py'),'--output',str(run/'physical_pose.jsonl')],env=e,stdout=baglog,stderr=subprocess.STDOUT)
                    if observe_localization:localization=subprocess.Popen(['/usr/bin/python3',str(HERE/'localization_observer.py'),'--output',str(run/'localization.jsonl')],env=e,stdout=baglog,stderr=subprocess.STDOUT)
                    if recording_profile!='none':bag=subprocess.Popen(['ros2','bag','record','--include-hidden-topics','-o',str(run/'bag'),*topics],cwd=root,env=e,stdout=baglog,stderr=subprocess.STDOUT)
                    proc=subprocess.Popen(cmd,cwd=root,env=e,stdout=log,stderr=subprocess.STDOUT)
                    (run/'owner.json').write_text(json.dumps({'pid':proc.pid,'run_id':ident})+'\n')
                    start=time.monotonic()
                    while proc.poll() is None and time.monotonic()-start<420:
                        desc=list(set(desc+owned_descendants(proc.pid)))
                        resource_log.write(json.dumps(resource_sample([proc.pid,*desc]))+'\n');time.sleep(.5)
                    if proc.poll() is None:
                        if not finish(proc):raise RuntimeError('Launch failed to close after one SIGINT')
                    returncode=proc.returncode
                finally:
                    clean_launch=finish(proc) if proc else True
                    clean_bag=finish(bag) if bag else True
                    clean_truth=finish(truth) if truth else True
                    clean_localization=finish(localization) if localization else True
            text=(run/'runtime.log').read_text(errors='replace');categories=summarize_log(text)
            residue=[pid for pid in desc if Path('/proc',str(pid)).exists()]
            row={'mode':mode,'run_id':ident,'returncode':returncode,'categories':categories,'residual_pids':residue,
                 'processes_terminated':clean_launch and clean_bag and clean_truth and clean_localization and not residue,
                 'cleanup_ok':clean_launch and clean_bag and clean_truth and clean_localization and not residue and not categories['cleanup_escalation'] and not categories['abnormal_exit']}
            if observe_truth:
                poses=[json.loads(line) for line in (run/'physical_pose.jsonl').read_text().splitlines() if line.strip()]
                row['physical_pose_samples']=len(poses)
                if poses:
                    position=poses[-1]['position'];row['physical_final_position']=position
                    row['physical_final_orientation']=poses[-1]['orientation']
                    row['physical_pose_frame']=poses[-1].get('frame');row['physical_pose_entity']=poses[-1].get('entity')
                    row['post_cleanup_pose_age_s']=time.monotonic()-poses[-1]['wall_monotonic']
                    if observe_localization:
                        observations=[json.loads(line) for line in (run/'localization.jsonl').read_text().splitlines() if line.strip()]
                        arrival=reference(poses,observations)
                        if arrival:
                            row.update(physical_arrival_position=arrival['pose']['position'],physical_arrival_orientation=arrival['pose']['orientation'],physical_pose_age_s=arrival['age_s'],physical_pose_reference='nav2_success_observed',arrival_goal_id=arrival['goal_id'])
                    row['physical_goal_distance_m']=math.hypot(position.get('x',0)-1,position.get('y',0)+9)
                else:row['infrastructure_failure']='No independent physical pose samples'
            if (run/'result.csv').exists():row['result']=list(csv.DictReader((run/'result.csv').open()))
            if (run/'sequence_result.json').exists():row['result']=json.loads((run/'sequence_result.json').read_text())
            if 'result' not in row:row['infrastructure_failure']='No finalized diagnostic result'
            results.append(row);(out/'pilot_results.json').write_text(json.dumps(results,indent=2)+'\n')
            print(mode,'completed', 'cleanup_ok='+str(row['cleanup_ok']),flush=True)
            if categories['cleanup_escalation'] or not row['cleanup_ok'] or categories['readiness'] or categories['action_ack_timeout'] or categories['sensor_fault'] or row.get('infrastructure_failure'):raise RuntimeError('Pilot stopped on infrastructure/cleanup; preserved all evidence')
    finally:
        if before is not None:
            after=fingerprint(root,env);(out/'db_after.json').write_text(json.dumps(after,indent=2)+'\n')
            if before!=after:raise RuntimeError('Frozen DB fingerprint changed')
    return results
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--code-root',type=Path,required=True);parser.add_argument('--runs-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--execute-pilot',action='store_true');parser.add_argument('--modes',nargs='+',choices=['direct','explicit_waypoint','memory'],default=['direct','explicit_waypoint','memory']);parser.add_argument('--private-env',type=Path);parser.add_argument('--existing-memory-container',action='store_true');parser.add_argument('--recording-profile',choices=['full','light','none'],default='full');parser.add_argument('--sensor-overlay',type=Path);a=parser.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    report={'status':'STARTED','source_head':subprocess.run(['git','rev-parse','HEAD'],cwd=a.code_root,capture_output=True,text=True,check=True).stdout.strip()}
    try:
        audit(a.code_root,a.runs_root,a.output)
        if a.execute_pilot:
            if a.existing_memory_container:
                with existing_memory_database(a.output) as db:pilot(a.code_root,a.output,a.modes,a.private_env,db,a.recording_profile,a.sensor_overlay)
            else:pilot(a.code_root,a.output,a.modes,a.private_env,recording_profile=a.recording_profile,sensor_overlay=a.sensor_overlay)
        report['status']='COMPLETED'
    except Exception as exc:
        report.update(status='STOPPED',error_type=type(exc).__name__,reason=str(exc));print(report['reason'],flush=True)
    finally:
        (a.output/'diagnostic_status.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Evidence:',a.output,flush=True)
    return 0 if report['status']=='COMPLETED' else 1
if __name__=='__main__':raise SystemExit(main())
