"""Operational acceptance: N0, N1 and controlled scan-loss during N1."""
import argparse,json,os,signal,threading,time,subprocess
from pathlib import Path
from diagnose import pilot,existing_memory_database,owned_descendants,digest
from physical_acceptance import assess

RUNTIME_FILES=['diagnose.py','navigation_lidar.launch.py','navigation_scan_filter.py','scan_health.py','navigation_cancellation.py','mission_memory_process.py','managed_bridge.launch.py','park_bridge','park_bridge.build.json','physical_acceptance.py','arrival_reference.py','localization_observer.py','truth_observer.py','run_navigation_lidar_profile.py','release_integrity.py']

def freeze_code(out):
    import shutil
    snapshot=out/'tested_code';snapshot.mkdir()
    for name in RUNTIME_FILES:shutil.copy2(Path(__file__).with_name(name),snapshot/name)
    return {name:digest(snapshot/name) for name in RUNTIME_FILES}

def interrupt_scan(run,stop,events):
    target=None;identity=None
    def starttime(pid):
        text=Path('/proc',str(pid),'stat').read_text();return text[text.rfind(')')+2:].split()[19]
    try:
        deadline=time.monotonic()+420
        while not stop.is_set() and time.monotonic()<deadline:
            log=run/'runtime.log';owner=run/'owner.json'
            if log.exists() and owner.exists() and 'Begin navigating from current location' in log.read_text(errors='replace'):
                pid=json.loads(owner.read_text())['pid']
                for child in owned_descendants(pid):
                    path=Path('/proc',str(child),'cmdline')
                    try:command=path.read_bytes()
                    except OSError:continue
                    if (b'parameter_bridge' in command and b'/navigation_scan@' in command) or (b'park_bridge' in command and b'--bridge-kind=navigation_scan' in command):
                        target=child;identity=starttime(target);os.kill(target,signal.SIGSTOP);events.append({'event':'SCAN_BRIDGE_PAUSED','pid':target,'wall_monotonic':time.monotonic()});break
                if target:break
            time.sleep(.05)
        if target:
            # Fault interval, not a readiness/navigation timeout increase. Restore
            # scheduling before launch's normal 5-second shutdown escalation.
            deadline=time.monotonic()+1.6
            while time.monotonic()<deadline and not stop.is_set():time.sleep(.05)
    except Exception as exc:events.append({'event':'INJECTOR_ERROR','type':type(exc).__name__})
    finally:
        if target:
            try:
                if starttime(target)==identity:os.kill(target,signal.SIGCONT);events.append({'event':'SCAN_BRIDGE_RESUMED','wall_monotonic':time.monotonic()})
            except (OSError,ValueError):pass

def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    code=freeze_code(a.output);protocol={'scope':'PARK_GAZEBO_SIMULATION','order':['N0_normal','N1_normal','N1_scan_loss'],'retries':0,'code_sha256':code,'acceptance':'normal: successful applicable goals, actual simulation position/yaw <=0.25m/rad, truth age <=2s, clean shutdown; injected: sensor_stale detected, no success, clean shutdown, DB unchanged','fault':'pause only the owned extra-lidar bridge for 1.6 seconds after first navigation goal; resume for clean shutdown','sensor_freshness_s':1.0,'no_scientific_result_changes':True}
    (a.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n');results=[];status={'status':'STARTED'}
    try:
        with existing_memory_database(a.output) as db:
            for name,mode in [('N0_normal','direct'),('N1_normal','memory'),('N1_scan_loss','memory')]:
                case=a.output/name;case.mkdir();events=[];stop=threading.Event();watcher=None;error=None;rows=[]
                if name=='N1_scan_loss':watcher=threading.Thread(target=interrupt_scan,args=(case/mode,stop,events));watcher.start()
                try:rows=pilot(a.code_root,case,[mode],database_env=db,recording_profile='none',sensor_overlay=a.profile,observe_truth=True,render_threads=2,observe_localization=True,rmw='rmw_cyclonedds_cpp',launch_file=Path(__file__).with_name('navigation_lidar.launch.py'))
                except RuntimeError as exc:error=str(exc)
                finally:
                    stop.set()
                    if watcher:watcher.join(timeout=5)
                if name!='N1_scan_loss':
                    if error:raise RuntimeError(error)
                    decision=assess(rows[0],mode);results.append({'case':name,'decision':decision})
                    if not decision['accepted']:raise RuntimeError('Normal operational acceptance failed: '+str(decision['reasons']))
                    if mode=='memory' and 'MISSION_MEMORY_RELEASE:' not in (case/mode/'runtime.log').read_text():raise RuntimeError('Embedding worker was not released after the first goal')
                else:
                    (case/'fault_events.json').write_text(json.dumps(events,indent=2)+'\n')
                    data=json.loads((case/'pilot_results.json').read_text());row=data[0]
                    health=[json.loads(l) for l in (case/mode/'sensor_health.jsonl').read_text().splitlines()]
                    final=row.get('result',[]);no_success=not final or all(r.get('success')!='true' and r.get('final_goal_nav2_result')!='SUCCEEDED' for r in final)
                    cancellation_complete=any(e['status']=='CANCELLATION_COMPLETE' for e in health)
                    accepted=bool(error) and row['cleanup_ok'] and no_success and cancellation_complete and any(e['event']=='SCAN_BRIDGE_PAUSED' for e in events) and any(e['status']=='FAILED' and e['reason']=='scan_stale' for e in health) and not watcher.is_alive()
                    results.append({'case':name,'expected_failure_verified':accepted,'cancellation_complete':cancellation_complete,'cleanup_ok':row['cleanup_ok'],'no_success':no_success,'events':events})
                    if not accepted:raise RuntimeError('Injected scan loss did not meet operational acceptance')
                (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        for name in ['N1_normal','N1_scan_loss']:
            if json.loads((a.output/name/'db_before.json').read_text())!=json.loads((a.output/name/'db_after.json').read_text()):raise RuntimeError('DB fingerprint changed')
        status['status']='OPERATIONAL_ACCEPTANCE_PASSED'
    except Exception as exc:status.update(status='STOPPED',reason=str(exc),error_type=type(exc).__name__)
    finally:
        (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n');(a.output/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status));return 0 if status['status']=='OPERATIONAL_ACCEPTANCE_PASSED' else 1
if __name__=='__main__':raise SystemExit(main())
