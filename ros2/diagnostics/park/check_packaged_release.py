"""Exercise the shipped CLI without starting simulation or writing to the DB."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from release_integrity import mission_lock

def main():
    p=argparse.ArgumentParser();p.add_argument('--entry',type=Path,required=True);p.add_argument('--code-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    version=json.loads((a.entry.parent/'current.json').read_text())['release'];release=a.entry.parent/version
    def db_state():return subprocess.run(['docker','inspect','--format','{{.State.Running}}','tfm_memory_postgres'],capture_output=True,text=True,check=True).stdout.strip()
    initial=db_state();results=[]
    def command(name,script,profile,root,expected,needle=None,execute=False):
        output=a.output/(name+'_run');args=[sys.executable,str(script),'--code-root',str(root),'--profile',str(profile)]
        args+=['--output',str(output)] if execute else ['--check-only']
        proc=subprocess.run(args,capture_output=True,text=True,timeout=30);text=proc.stdout+proc.stderr
        passed=(proc.returncode==0 if expected else proc.returncode!=0) and (needle is None or needle in text) and not output.exists()
        results.append({'case':name,'passed':passed,'returncode':proc.returncode,'output':text,'no_run_directory_created':not output.exists()})
        if not passed:raise RuntimeError('Packaged CLI check failed: '+name)
    script=release/'code/run_navigation_lidar_profile.py';profile=release/'profile'
    command('valid_integrity',script,profile,a.code_root,True,needle='no processes or DB started')
    badcode=a.output/'changed_code';shutil.copytree(release,badcode);file=badcode/'code/navigation_scan_filter.py';file.write_text(file.read_text()+'\n# Offline mutation test\n')
    command('reject_changed_code',badcode/'code/run_navigation_lidar_profile.py',badcode/'profile',a.code_root,False,needle='changed: navigation_scan_filter.py')
    badprofile=a.output/'changed_profile';shutil.copytree(release,badprofile);file=badprofile/'profile/share/wheelchair_gazebo/models/wheelchair/model.sdf';file.write_text(file.read_text()+'\n<!-- Offline mutation test -->\n')
    command('reject_changed_sensor',badprofile/'code/run_navigation_lidar_profile.py',badprofile/'profile',a.code_root,False,needle='model.sdf')
    missing=a.output/'missing_source';missing.mkdir();command('reject_unmatched_source',script,profile,missing,False,needle='Release artifact missing or changed:')
    with mission_lock():command('reject_concurrent_mission',script,profile,a.code_root,False,needle='Another PARK simulation mission is already running',execute=True)
    final=db_state();report={'status':'PASSED' if all(r['passed'] for r in results) and initial==final else 'FAILED','database_initially_running':initial,'database_finally_running':final,'checks':results}
    (a.output/'checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'checks':len(results),'database_state_unchanged':initial==final}));return 0 if report['status']=='PASSED' else 1
if __name__=='__main__':raise SystemExit(main())
