"""Read-only final verification; no simulation, DB connection or deployment."""
import argparse,json,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    root=Path('/home/iratxefagoaga/workspace/tfm-public');here=Path(__file__).parent
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(here),'-p','test_diagnose.py','-v'],capture_output=True,text=True)
    verify=subprocess.run([sys.executable,str(root/'scripts/experiments/verify_final_results.py')],capture_output=True,text=True)
    processes=subprocess.run(['ps','-eo','pid,ppid,comm'],capture_output=True,text=True,check=True).stdout
    names={'gz','ruby','planner_server','controller_server','map_server','amcl','bt_navigator','lifecycle_manag','parameter_bridg'}
    residues=[l for l in processes.splitlines()[1:] if l.split()[-1] in names]
    containers=subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,check=True).stdout.splitlines()
    public_status=subprocess.run(['git','status','--porcelain'],cwd=root,capture_output=True,text=True,check=True).stdout.splitlines()
    fingerprints=[]
    for directory in ['park_production_gate_20261025_01','park_production_udp_gate_20261025_01','park_production_render_gate_20261025_01']:
        for path in Path('/tmp',directory).glob('*/db_*.json'):fingerprints.append({'path':str(path),'value':json.loads(path.read_text())})
    values=[r['value'] for r in fingerprints]
    unchanged=len(values)==8 and all(v==values[0] and v['row_count']==50 for v in values)
    result={'tests_returncode':tests.returncode,'tests_output':tests.stdout+tests.stderr,'frozen_verifier_returncode':verify.returncode,
            'frozen_verifier_output':verify.stdout+verify.stderr,'ros_gazebo_residues':residues,'running_containers':containers,
            'public_git_status':public_status,'fingerprints':fingerprints,'all_eight_fingerprint_files_equal':unchanged,
            'production_status':'ADOPTION_BLOCKED'}
    (a.output/'final_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    passed=not tests.returncode and not verify.returncode and not residues and not containers and unchanged
    print(json.dumps({'final_checks_pass':passed,'production_status':'ADOPTION_BLOCKED','fingerprint_files':len(values)}));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
