"""Bounded acceptance of a proposed mount in simulation, never physical deployment."""
import argparse,json,math
from pathlib import Path
from diagnose import pilot,existing_memory_database,digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--overlay',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    protocol={'kind':'PROPOSED_MOUNT_SIMULATION_ACCEPTANCE_NOT_EFFICACY','order':['direct','memory','memory','memory'],'retries':0,
      'physical_mount_measured':False,'RMW':'rmw_cyclonedds_cpp','LP_NUM_THREADS':2,'rosbag':False,
      'acceptance':['all actions succeed','each physical final position error <=0.25m','each physical final yaw error <=0.25rad','no readiness/ack/cleanup failure','DB unchanged'],
      'controller_goal_budget':'profile xy/yaw tolerances 0.15; physical acceptance remains 0.25',
      'source_hashes':{n:digest(Path(__file__).with_name(n)) for n in ['diagnose.py','navigation_lidar.launch.py','navigation_scan_filter.py','localization_observer.py','truth_observer.py','gate_navigation_lidar.py']}}
    (a.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n');results=[];status={'status':'STARTED'}
    try:
        with existing_memory_database(a.output) as db:
            for i,mode in enumerate(protocol['order']):
                out=a.output/f'{i+1:02d}_{mode}';out.mkdir();row=pilot(a.code_root,out,[mode],database_env=db,recording_profile='none',sensor_overlay=a.overlay,observe_truth=True,render_threads=2,observe_localization=True,rmw='rmw_cyclonedds_cpp',launch_file=Path(__file__).with_name('navigation_lidar.launch.py'))[0]
                q=row.get('physical_final_orientation',{});x=q.get('x',0);y=q.get('y',0);z=q.get('z',0);w=q.get('w',1);angle=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z));row['physical_yaw_error_rad']=abs(angle)
                rows=row.get('result',[]);success=isinstance(rows,list) and len(rows)==1 and rows[0].get('final_goal_nav2_result')=='SUCCEEDED'
                if mode=='memory':success=success and rows[0].get('waypoint_nav2_result')=='SUCCEEDED'
                row['accepted']=success and row.get('physical_goal_distance_m',float('inf'))<=.25 and abs(angle)<=.25 and row['cleanup_ok'];results.append(row)
                (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
                if not row['accepted']:raise RuntimeError('Proposed profile failed action/physical acceptance; no further trials')
        status['status']='PASSED_SIMULATION_ONLY_PHYSICAL_MOUNT_UNVALIDATED'
    except Exception as exc:status.update(status='STOPPED',reason=str(exc),error_type=type(exc).__name__)
    finally:(a.output/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status));return 0 if status['status']=='PASSED_SIMULATION_ONLY_PHYSICAL_MOUNT_UNVALIDATED' else 1
if __name__=='__main__':raise SystemExit(main())
