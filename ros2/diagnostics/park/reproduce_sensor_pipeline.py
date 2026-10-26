"""Bounded failure diagnosis with unchanged accepted release; not a success-rate campaign."""
import argparse,json,os,subprocess,threading,time
from pathlib import Path
from diagnose import ros_environment,finish

def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--entrypoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--runs',type=int,default=3);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'protocol.json').write_text(json.dumps({'kind':'TARGETED_PIPELINE_DIAGNOSIS_NOT_RATE_ESTIMATE','max_runs':a.runs,'stop_on':'first scan_stale or uncleanness','changes':'passive raw GZ and ROS subscribers only; original release unchanged','no_internet_required':True},indent=2)+'\n')
    environment=ros_environment(a.code_root);environment.update(RMW_IMPLEMENTATION='rmw_cyclonedds_cpp',ROS_DOMAIN_ID='91',ROS_LOCALHOST_ONLY='1')
    for i in range(1,a.runs+1):
        out=a.output/f'{i:02d}';stop=threading.Event();observed=[]
        def observe():
            owner=out/'memory/owner.json'
            while not stop.is_set() and not owner.exists():stop.wait(.05)
            if stop.is_set():return
            env=environment.copy();env['GZ_PARTITION']=json.loads(owner.read_text())['run_id']
            with (a.output/f'{i:02d}_observer.log').open('w') as log:
                proc=subprocess.Popen(['/usr/bin/python3',str(Path(__file__).with_name('sensor_pipeline_observer.py')),'--output',str(a.output/f'{i:02d}_pipeline.jsonl')],env=env,stdout=log,stderr=subprocess.STDOUT)
                stop.wait();observed.append({'returncode_before_stop':proc.poll(),'clean':finish(proc),'returncode':proc.returncode})
        watcher=threading.Thread(target=observe);watcher.start()
        try:
            with (a.output/f'{i:02d}_entry.log').open('w') as log:
                result=subprocess.run(['/usr/bin/python3',str(a.entrypoint),'--code-root',str(a.code_root),'--mode','memory','--output',str(out)],stdout=log,stderr=subprocess.STDOUT)
        finally:stop.set();watcher.join(timeout=25)
        (a.output/f'{i:02d}_observer_status.json').write_text(json.dumps(observed,indent=2)+'\n')
        rows=json.loads((out/'pilot_results.json').read_text());row=rows[0]
        print(json.dumps({'run':i,'returncode':result.returncode,'categories':row['categories'],'observer':observed}),flush=True)
        if row['categories'].get('sensor_fault') or not row['cleanup_ok']:break
    return 0

if __name__=='__main__':raise SystemExit(main())
