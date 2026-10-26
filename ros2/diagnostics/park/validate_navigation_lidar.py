"""Static validation of the proposed extra lidar against unchanged planning map."""
import argparse,json,math,subprocess,time,uuid
from pathlib import Path
from diagnose import ros_environment,owned_descendants,finish,summarize_log,digest
from navigation_scan_filter import filtered_ranges

def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--overlay',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    manifest_path=a.overlay/'overlay_manifest.json';manifest=json.loads(manifest_path.read_text());model=a.overlay/'share/wheelchair_gazebo/models/wheelchair/model.sdf'
    protocol={'kind':'PROPOSED_ADDITIONAL_LIDAR_STATIC_TEST','scan_count':30,'max_odom_drift_m':.02,'external_returns_min':100,'map_match_min':.9,'map_match_radius_m':.15,'candidate_sha256':digest(model),'no_navigation':True,'LP_NUM_THREADS':2,'RMW':'rmw_cyclonedds_cpp','physical_mount_measured':False}
    (a.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    processes=subprocess.run(['ps','-eo','comm='],capture_output=True,text=True,check=True).stdout.splitlines()
    if any(n.strip() in {'gz','ruby','amcl','controller_server','bt_navigator'} for n in processes):raise RuntimeError('Existing simulator or Nav2')
    env=ros_environment(a.code_root);env.update(ROS_DOMAIN_ID='98',ROS_LOCALHOST_ONLY='1',GZ_PARTITION=uuid.uuid4().hex,LP_NUM_THREADS='2',RMW_IMPLEMENTATION='rmw_cyclonedds_cpp',PARK_SENSOR_MODEL=str(model),PARK_SENSOR_TOPIC='/navigation_scan',PARK_SENSOR_OUTPUT=str(a.output/'scans.json'),ROS_LOG_DIR=str(a.output/'ros_logs'))
    descendants=[]
    with (a.output/'runtime.log').open('w') as log:
        proc=subprocess.Popen(['ros2','launch',str(Path(__file__).with_name('sensor_probe.launch.py'))],env=env,cwd=a.code_root,stdout=log,stderr=subprocess.STDOUT);start=time.monotonic()
        try:
            while proc.poll() is None and time.monotonic()-start<150:
                descendants=list(set(descendants+owned_descendants(proc.pid)));time.sleep(.5)
        finally:closed=finish(proc)
    data=json.loads((a.output/'scans.json').read_text());categories=summarize_log((a.output/'runtime.log').read_text(errors='replace'));residue=[p for p in descendants if Path('/proc',str(p)).exists()]
    import yaml
    from PIL import Image
    metadata=yaml.safe_load((a.code_root/'ros2/src/wheelchair_navigation/maps/park.yaml').read_text());resolution=metadata['resolution'];origin=metadata['origin'];assert origin[2]==0
    image=Image.open(a.code_root/'ros2/src/wheelchair_navigation/maps/park.pgm');offsets=[(x,y) for x in range(-3,4) for y in range(-3,4) if math.hypot(x,y)*resolution<=.15+1e-9]
    measurements=[]
    for scan in data['scans']:
        raw=[float('inf') if r is None else r for r in scan['ranges']];ranges=filtered_ranges(raw,scan['angle_min'],scan['angle_increment'],scan['range_min'],scan['range_max']);finite=matched=0
        for i,r in enumerate(ranges):
            if not math.isfinite(r) or not scan['range_min']<=r<=scan['range_max']:continue
            finite+=1;angle=scan['angle_min']+i*scan['angle_increment'];x=.33+r*math.cos(angle);y=-9+r*math.sin(angle);px=int((x-origin[0])/resolution);py=image.height-1-int((y-origin[1])/resolution)
            matched+=any(0<=px+dx<image.width and 0<=py+dy<image.height and image.getpixel((px+dx,py+dy))<100 for dx,dy in offsets)
        measurements.append({'external_returns':finite,'matched_returns':matched,'map_match_fraction':matched/finite if finite else 0})
    odom=data['odometry'];drift=max((math.dist(p[:2],odom[0][:2]) for p in odom),default=float('inf'))
    passed=data['completed'] and len(measurements)==30 and min(r['external_returns'] for r in measurements)>=100 and min(r['map_match_fraction'] for r in measurements)>=.9 and drift<.02 and closed and not residue and not categories['cleanup_escalation']
    result={'status':'PASSED_PROPOSED_SENSOR_STATIC_ONLY' if passed else 'FAILED','measurements':measurements,'odom_planar_drift_m':drift,'cleanup_ok':closed and not residue and not categories['cleanup_escalation'],'residual_pids':residue,'categories':categories,'physical_mount_measured':False}
    (a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    if passed:
        manifest.update(status='ISOLATED_DIAGNOSTIC_OVERLAY',sensor_validation=str(a.output/'summary.json'));manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(result));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
