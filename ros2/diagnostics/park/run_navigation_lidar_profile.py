"""Run the locally accepted SIMULATION profile; never a hardware bringup."""
import argparse,json,math
from pathlib import Path
from diagnose import pilot,existing_memory_database,verify_sensor_overlay
from physical_acceptance import assess
from release_integrity import verify_release,mission_lock

def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--mode',choices=['direct','memory'],default='memory');p.add_argument('--output',type=Path);p.add_argument('--check-only',action='store_true');a=p.parse_args()
    verify_release(a.profile,a.code_root,Path(__file__).parent);verify_sensor_overlay(a.profile)
    if a.check_only:print('PASS: PARK simulation release integrity; no processes or DB started');return 0
    if a.output is None:p.error('--output is required for execution')
    print('PARK production profile: Gazebo simulation only.',flush=True)
    def run(db=None):
        row=pilot(a.code_root,a.output,[a.mode],database_env=db,recording_profile='none',sensor_overlay=a.profile,observe_truth=True,render_threads=2,observe_localization=True,rmw='rmw_cyclonedds_cpp',launch_file=Path(__file__).with_name('navigation_lidar.launch.py'))[0]
        decision=assess(row,a.mode)
        (a.output/'physical_acceptance.json').write_text(json.dumps(decision,indent=2)+'\n')
        return 0 if decision['accepted'] else 1
    with mission_lock():
        a.output.mkdir(parents=True,exist_ok=False)
        if a.mode=='memory':
            with existing_memory_database(a.output) as db:return run(db)
        return run()
if __name__=='__main__':raise SystemExit(main())
