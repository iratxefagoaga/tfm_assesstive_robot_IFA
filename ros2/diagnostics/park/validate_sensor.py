"""Original/candidate static comparison; stop immediately on missing data or escalated close."""
import argparse,hashlib,json,math,os,subprocess,time,uuid
from pathlib import Path
from diagnose import ros_environment,owned_descendants,finish,summarize_log

def summarize(data):
    scans=data['scans'];near=[];far=[]
    for s in scans:
        valid=[r for r in s['ranges'] if r is not None and s['range_min']<=r<=s['range_max']]
        near.append(sum(r<1 for r in valid));far.append(sum(r>=2 for r in valid))
    odom=data['odometry'];drift=max((math.dist(p[:2],odom[0][:2]) for p in odom),default=0)
    return {'scan_count':len(scans),'near_hits_min':min(near,default=0),'near_hits_max':max(near,default=0),
            'far_hits_min':min(far,default=0),'far_hits_max':max(far,default=0),'max_odom_translation_m':drift}
def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    original=a.code_root/'ros2/src/wheelchair_gazebo/models/wheelchair/model.sdf'
    protocol={'kind':'STATIC_SENSOR_TEST_NOT_EFFICACY','order':['original','candidate'],'scan_count':30,
      'acquisition_start':'5 seconds of scan time after first scan, same for both models','no_navigation_goals':True,
      'pass_requirements':['both complete','clean shutdown and no residue','original near hits >=200','candidate near hits <5','candidate sees external ranges >=2m','odom translation <0.02m'],
      'models':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [original,a.candidate]}}
    (a.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    env=ros_environment(a.code_root);results={};status='STOPPED'
    try:
        processes=subprocess.run(['ps','-eo','comm='],capture_output=True,text=True,check=True).stdout.splitlines()
        if any(p.strip() in {'gz','ruby','amcl','planner_server','bt_navigator','controller_server'} for p in processes):raise RuntimeError('Existing simulator/Nav2 found')
        for i,(name,model) in enumerate([('original',original),('candidate',a.candidate)]):
            out=a.output/name;out.mkdir();e=env.copy();e.update(ROS_DOMAIN_ID=str(96+i),GZ_PARTITION=uuid.uuid4().hex,ROS_LOCALHOST_ONLY='1',
                PARK_SENSOR_MODEL=str(model),PARK_SENSOR_OUTPUT=str(out/'scans.json'),ROS_LOG_DIR=str(out/'ros_logs'))
            descendants=[]
            with (out/'runtime.log').open('w') as log:
                proc=subprocess.Popen(['ros2','launch',str(Path(__file__).with_name('sensor_probe.launch.py'))],env=e,cwd=a.code_root,stdout=log,stderr=subprocess.STDOUT)
                start=time.monotonic()
                try:
                    while proc.poll() is None and time.monotonic()-start<150:
                        descendants=list(set(descendants+owned_descendants(proc.pid)));time.sleep(.25)
                finally:closed=finish(proc)
            text=(out/'runtime.log').read_text(errors='replace');residue=[pid for pid in descendants if Path('/proc',str(pid)).exists()]
            summary={'returncode':proc.returncode,'cleanup_ok':closed and not residue and not summarize_log(text)['cleanup_escalation'],'residual_pids':residue}
            if (out/'scans.json').exists():
                data=json.loads((out/'scans.json').read_text());summary.update(summarize(data),completed=data['completed'])
            results[name]=summary;(a.output/'summary.json').write_text(json.dumps(results,indent=2)+'\n');print(name,json.dumps(summary),flush=True)
            if not summary['cleanup_ok'] or not summary.get('completed'):raise RuntimeError('Sensor test stopped: cleanup or acquisition failure')
        before,after=results['original'],results['candidate']
        passed=before['near_hits_min']>=200 and after['near_hits_max']<5 and after['far_hits_min']>0 and max(before['max_odom_translation_m'],after['max_odom_translation_m'])<.02
        status='PASSED_STATIC_SENSOR_ONLY' if passed else 'FAILED_SENSOR_REQUIREMENTS'
    except Exception as exc:results['reason']=str(exc)
    finally:
        results['status']=status;(a.output/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
    print(status,flush=True);return 0 if status=='PASSED_STATIC_SENSOR_ONLY' else 1
if __name__=='__main__':raise SystemExit(main())
