"""Predeclared diagnostic pair, no promotion and no frozen input changes."""
import argparse,json
from pathlib import Path
from diagnose import pilot,existing_memory_database,digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--overlay',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--rmw',choices=['rmw_cyclonedds_cpp','rmw_fastrtps_cpp']);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    protocol={'kind':'LOCALIZATION_DIAGNOSIS_NOT_EFFICACY_NOT_DEPLOYMENT','order':['original','mask_candidate'],
      'repetitions':1,'retries':0,'LP_NUM_THREADS':2,'DDS':a.rmw or 'inherited','rosbag':False,
      'capture':['Gazebo pose/info all received','ROS amcl_pose,odom,tf,scan summaries'],
      'stop':'infrastructure failure; no automatic retry','physical_mount':'unknown, unchanged',
      'source_hashes':{n:digest(Path(__file__).with_name(n)) for n in ['diagnose.py','compare_localization.py','truth_observer.py','localization_observer.py']}}
    (a.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    status={'status':'STARTED'}
    try:
        with existing_memory_database(a.output) as db:
            for name in protocol['order']:
                out=a.output/name;out.mkdir()
                pilot(a.code_root,out,['memory'],database_env=db,recording_profile='none',sensor_overlay=a.overlay if name=='mask_candidate' else None,
                      observe_truth=True,render_threads=2,observe_localization=True,rmw=a.rmw)
        status['status']='COMPLETED_DIAGNOSTIC_PAIR'
    except Exception as exc:status.update(status='STOPPED',reason=str(exc),error_type=type(exc).__name__)
    finally:(a.output/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status));return 0 if status['status']=='COMPLETED_DIAGNOSTIC_PAIR' else 1
if __name__=='__main__':raise SystemExit(main())
