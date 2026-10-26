"""Production entry point for the locally qualified PARK Gazebo simulation."""
import argparse,json,subprocess,sys
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,default=Path(__file__).resolve().parents[3]);p.add_argument('--mode',choices=['direct','memory'],default='memory');p.add_argument('--output',type=Path);p.add_argument('--check-only',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parent;version=json.loads((root/'current.json').read_text())['release'];release=root/version
    if release.parent!=root:raise RuntimeError('Invalid release path')
    command=[sys.executable,str(release/'code/run_navigation_lidar_profile.py'),'--code-root',str(a.code_root),'--profile',str(release/'profile'),'--mode',a.mode]
    if a.check_only:command.append('--check-only')
    elif a.output is None:p.error('--output is required unless --check-only is supplied')
    else:command.extend(['--output',str(a.output)])
    return subprocess.run(command).returncode
if __name__=='__main__':raise SystemExit(main())
