"""Predeclared engineering gate; never retries or promotes a failing candidate."""
import argparse,json,random,subprocess,math
from pathlib import Path
from diagnose import pilot,existing_memory_database,digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--instrument-check',action='store_true');p.add_argument('--transport',choices=['DEFAULT','UDPv4']);p.add_argument('--render-threads',type=int,choices=[1,2]);a=p.parse_args()
    root=Path('/home/iratxefagoaga/workspace/tfm-public');overlay=Path('/tmp/park_sensor_overlay_20261025_01')
    a.output.mkdir(parents=True,exist_ok=False)
    order=[]
    for block in range(3):
        variants=['original','candidate'];random.Random(20261025+block).shuffle(variants)
        order.extend({'block':block+1,'variant':v,'mode':'memory'} for v in variants)
    if a.instrument_check:order=[{'block':0,'variant':'original','mode':'direct'}]
    protocol={'kind':'ENGINEERING_GATE_NOT_SCIENTIFIC_EFFICACY','order':order,'retries':0,
      'recording':'no rosbag; all received read-only Gazebo world pose messages','DDS_transport':a.transport or 'inherited','LP_NUM_THREADS':a.render_threads,
      'acceptance':['every candidate run Nav2 SUCCEEDED','every candidate physical final distance <=0.25m',
                    'no acknowledgement/readiness/cleanup failure','frozen DB unchanged'],
      'limits':['three paired N1 repetitions do not establish a general success rate',
                'mask remains idealised; low obstacle visibility is unresolved',
                'no production promotion if physical arrival disagrees with action success'],
      'code_sha256':{n:digest(Path(__file__).with_name(n)) for n in ['diagnose.py','truth_observer.py','production_gate.py']}}
    (a.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    results=[];status='STOPPED'
    def execute(db=None):
        nonlocal status
        for i,item in enumerate(order):
            out=a.output/f'{i+1:02d}_{item["variant"]}';out.mkdir()
            rows=pilot(root,out,[item['mode']],database_env=db,recording_profile='none',
                       sensor_overlay=overlay if item['variant']=='candidate' else None,observe_truth=True,transport=a.transport,render_threads=a.render_threads)
            row=rows[0];row.update(item);results.append(row)
            (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
            if not row.get('physical_pose_samples'):raise RuntimeError('Independent pose acquisition failed')
            recorded=row.get('result',[])
            success=isinstance(recorded,list) and len(recorded)==1 and recorded[0].get('final_goal_nav2_result')=='SUCCEEDED'
            row['physical_arrival_pass']=row['physical_goal_distance_m']<=.25
            row['action_success']=success
            (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
            if item['variant']=='candidate' and success and not row['physical_arrival_pass']:raise RuntimeError('Candidate action success disagrees with physical arrival; adoption blocked')
        status='INSTRUMENT_CHECK_COMPLETED' if a.instrument_check else ('GATE_PASSED_LIMITED_SCOPE' if all(r['action_success'] and r['physical_arrival_pass'] for r in results if r['variant']=='candidate') else 'GATE_FAILED')
    try:
        if a.instrument_check:execute()
        else:
            with existing_memory_database(a.output) as db:execute(db)
    except Exception as exc:
        (a.output/'error.json').write_text(json.dumps({'type':type(exc).__name__,'reason':str(exc)},indent=2)+'\n')
        print(str(exc),flush=True)
    finally:
        (a.output/'status.json').write_text(json.dumps({'status':status},indent=2)+'\n')
    print(status,flush=True);return 0 if status in {'INSTRUMENT_CHECK_COMPLETED','GATE_PASSED_LIMITED_SCOPE'} else 1
if __name__=='__main__':raise SystemExit(main())
