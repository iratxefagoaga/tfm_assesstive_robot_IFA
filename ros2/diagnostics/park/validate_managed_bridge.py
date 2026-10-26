"""Compile provenance and six bounded startup/shutdown cycles without simulation."""
import argparse,json,os,shutil,subprocess,time,uuid
from pathlib import Path
from diagnose import ros_environment,digest,finish,owned_descendants

def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);here=Path(__file__).parent
    executable=here/'park_bridge'
    if executable.exists():raise RuntimeError('Refusing to replace an existing adapter binary')
    shutil.copy2(a.build/'park_bridge',executable);metadata={'source_sha256':{n:digest(here/'native'/n) for n in ['managed_bridge.cpp','CMakeLists.txt']},'binary_sha256':digest(executable),'ros_gz_bridge_version':'1.0.22','system_ros_python':'/usr/bin/python3','build_directory':str(a.build),'link_dependencies':subprocess.run(['ldd',str(executable)],capture_output=True,text=True,check=True).stdout}
    (here/'park_bridge.build.json').write_text(json.dumps(metadata,indent=2)+'\n');results=[]
    env=ros_environment(a.code_root);env.update(RMW_IMPLEMENTATION='rmw_cyclonedds_cpp',ROS_DOMAIN_ID='89',ROS_LOCALHOST_ONLY='1')
    for i in range(3):
        for kind in ['core','navigation_scan']:
            e=env.copy();e['GZ_PARTITION']=uuid.uuid4().hex;path=a.output/f'{i}_{kind}.log';desc=[]
            with path.open('w') as log:
                proc=subprocess.Popen([str(executable),'--bridge-kind='+kind],env=e,stdout=log,stderr=subprocess.STDOUT);deadline=time.monotonic()+10
                while proc.poll() is None and time.monotonic()<deadline:
                    desc=list(set(desc+owned_descendants(proc.pid)))
                    if 'Creating GZ->ROS Bridge' in path.read_text():break
                    time.sleep(.05)
                start=time.monotonic();closed=finish(proc);elapsed=time.monotonic()-start
            residue=[pid for pid in desc if Path('/proc',str(pid)).exists()];text=path.read_text();passed=closed and proc.returncode==0 and elapsed<5 and not residue and 'CLEAN_BRIDGE_SHUTDOWN '+kind in text
            results.append({'cycle':i,'kind':kind,'returncode':proc.returncode,'shutdown_s':elapsed,'residue':residue,'passed':passed})
            (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
            if not passed:raise RuntimeError('Managed bridge did not close cleanly')
    print(json.dumps({'passed_cycles':len(results),'no_simulation_started':True}));return 0
if __name__=='__main__':raise SystemExit(main())
