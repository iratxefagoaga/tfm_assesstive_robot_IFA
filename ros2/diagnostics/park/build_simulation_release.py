"""Create a pinned local PARK simulation release only after operational acceptance."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from diagnose import digest,verify_sensor_overlay
from qualify_simulation_release import RUNTIME_FILES

ENTRY='''"""Production entry point for the locally qualified PARK Gazebo simulation."""
import argparse,json,subprocess,sys
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--mode',choices=['direct','memory'],default='memory');p.add_argument('--output',type=Path);p.add_argument('--check-only',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parent;version=json.loads((root/'current.json').read_text())['release'];release=root/version
    if release.parent!=root:raise RuntimeError('Invalid release path')
    command=[sys.executable,str(release/'code/run_navigation_lidar_profile.py'),'--code-root',str(a.code_root),'--profile',str(release/'profile'),'--mode',a.mode]
    if a.check_only:command.append('--check-only')
    elif a.output is None:p.error('--output is required unless --check-only is supplied')
    else:command.extend(['--output',str(a.output)])
    return subprocess.run(command).returncode
if __name__=='__main__':raise SystemExit(main())
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--qualification',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--code-root',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args();here=Path(__file__).parent
    status=json.loads((a.qualification/'status.json').read_text())
    if status['status']!='OPERATIONAL_ACCEPTANCE_PASSED':raise RuntimeError('Operational acceptance has not passed')
    protocol=json.loads((a.qualification/'protocol.json').read_text())
    for name in RUNTIME_FILES:
        if digest(here/name)!=protocol['code_sha256'][name]:raise RuntimeError('Runtime changed after qualification: '+name)
    verify_sensor_overlay(a.profile)
    if a.destination.exists():raise RuntimeError('Refusing to overwrite a release')
    parent=a.destination.parent
    if (parent/'current.json').exists() or (parent/'run.py').exists():raise RuntimeError('An existing entry point requires an explicit update')
    a.destination.mkdir(parents=True);code=a.destination/'code';code.mkdir()
    for name in RUNTIME_FILES:shutil.copy2(here/name,code/name)
    profile=a.destination/'profile';shutil.copytree(a.profile,profile,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # Package resources must be self-contained: copytree resolves the preparation
    # overlay links. Imports of original N0/N1 remain pinned in the source checkout.
    inventory={}
    for directory in [a.code_root/'ros2/src',a.code_root/'memory',a.code_root/'scripts/memory']:
        for file in directory.rglob('*'):
            if file.is_file() and file.suffix in {'.py','.cpp','.hpp','.h','.xml','.xacro','.yaml','.txt','.srv','.msg','.action','.sdf','.world','.pgm'} and '__pycache__' not in file.parts:inventory[str(file.relative_to(a.code_root))]=digest(file)
    executable_dir=a.code_root/'ros2/install/wheelchair_assistive_bt/lib/wheelchair_assistive_bt'
    for file in executable_dir.iterdir():
        if file.is_file():inventory[str(file.relative_to(a.code_root))]=digest(file)
    for file in (a.code_root/'ros2/install/wheelchair_interfaces').rglob('*'):
        if file.is_file() and file.suffix in {'.so','.py'} and '__pycache__' not in file.parts:inventory[str(file.relative_to(a.code_root))]=digest(file)
    interpreter=a.code_root/'.venv/bin/python';inventory[str(interpreter.relative_to(a.code_root))]=digest(interpreter)
    record={'status':'PARK_SIMULATION_RELEASE_READY','scope':'PARK_GAZEBO_SIMULATION','hardware_validation':'NOT_APPLICABLE_USER_CONFIRMED_SIMULATION_ONLY','release':a.destination.name,
      'code_root_head':subprocess.run(['git','rev-parse','HEAD'],cwd=a.code_root,capture_output=True,text=True,check=True).stdout.strip(),
      'code_sha256':{name:digest(code/name) for name in RUNTIME_FILES},'source_sha256':inventory,
      'profile_sha256':{str(file.relative_to(profile)):digest(file) for file in profile.rglob('*') if file.is_file() and file!=profile/'simulation_acceptance.json' and '__pycache__' not in file.parts},
      'qualification_protocol_sha256':digest(a.qualification/'protocol.json'),'qualification_results_sha256':digest(a.qualification/'results.json'),
      'sensor_freshness_s':1.0,'truth_freshness_s_at_success':2.0,'position_tolerance_m':.25,'yaw_tolerance_rad':.25,'scientific_E1':'unchanged'}
    (profile/'simulation_acceptance.json').write_text(json.dumps(record,indent=2)+'\n')
    (parent/'run.py').write_text(ENTRY);(parent/'current.json').write_text(json.dumps({'scope':record['scope'],'release':a.destination.name},indent=2)+'\n')
    shutil.copy2(a.qualification/'results.json',a.destination/'operational_acceptance.json')
    result=subprocess.run([sys.executable,str(parent/'run.py'),'--code-root',str(a.code_root),'--check-only'],capture_output=True,text=True)
    (a.destination/'build_check.json').write_text(json.dumps({'returncode':result.returncode,'output':result.stdout+result.stderr},indent=2)+'\n')
    if result.returncode:raise RuntimeError('Packaged integrity check failed')
    print(json.dumps({'release':str(a.destination),'source_files_pinned':len(inventory),'profile_files_pinned':len(record['profile_sha256']),'code_files_pinned':len(record['code_sha256'])}));return 0
if __name__=='__main__':raise SystemExit(main())
