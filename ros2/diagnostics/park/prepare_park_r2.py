"""A new navigation-only profile; original release and frozen sources stay intact."""
import argparse,hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
from prepare_sensor_candidate import collision_signature

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    import yaml
    p=argparse.ArgumentParser();p.add_argument('--previous-profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise RuntimeError('Refusing overwrite')
    shutil.copytree(a.previous_profile,a.output,ignore=shutil.ignore_patterns('__pycache__','simulation_acceptance.json'))
    model=a.output/'share/wheelchair_gazebo/models/wheelchair/model.sdf';tree=ET.parse(model);before=collision_signature(tree.getroot());removed=[]
    for link in tree.getroot().findall('model/link'):
        for sensor in list(link.findall('sensor')):
            if sensor.get('type') in {'camera','gpu_lidar'} and sensor.findtext('topic')!='/navigation_scan':
                removed.append({'link':link.get('name'),'name':sensor.get('name'),'type':sensor.get('type'),'topic':sensor.findtext('topic'),'rate_hz':sensor.findtext('update_rate')});link.remove(sensor)
    if len(removed)!=2:raise RuntimeError('Unexpected sensor inventory')
    if collision_signature(tree.getroot())!=before:raise RuntimeError('Collision geometry changed')
    tree.write(model,encoding='utf-8',xml_declaration=True)
    config=a.output/'share/wheelchair_navigation/config/nav2_params.yaml';data=yaml.safe_load(config.read_text());checker=data['controller_server']['ros__parameters']['general_goal_checker'];checker['xy_goal_tolerance']=.05;checker['yaw_goal_tolerance']=.10;config.write_text(yaml.safe_dump(data,sort_keys=False))
    manifest=json.loads((a.output/'overlay_manifest.json').read_text());manifest.update(status='PROPOSED_R2_NOT_VALIDATED',candidate_sha256=sha(model),original_sensor_retained=False,removed_inactive_navigation_sensors=removed,physical_mount_measured=False,scope='GAZEBO_SIMULATION_ONLY')
    manifest['goal_tolerances']={'xy_m':.05,'yaw_rad':.10,'reason':'Observed 0.132-0.161m localisation bias exceeded the previous 0.10m budget; reserve 0.20m of the unchanged 0.25m independent position acceptance, without a guarantee of a bound on future bias'}
    manifest['extra_sha256']={name:sha(a.output/name) for name in manifest['extra_sha256']}
    manifest.pop('sensor_validation',None)
    (a.output/'overlay_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (a.output/'r2_changes.json').write_text(json.dumps({'hypothesis':'remove unused camera at 30Hz and original high lidar at 15Hz to reduce common rendering workload; keep low lidar at 15Hz/720 rays','removed_sensors':removed,'collisions_and_maps_unchanged':True,'base_profile_manifest_sha256':sha(a.previous_profile/'simulation_acceptance.json'),'readiness_sensor_navigation_shutdown_timeouts':'unchanged','status':'CANDIDATE_NOT_ACCEPTED'},indent=2)+'\n')
    print(json.dumps({'profile':str(a.output),'removed_sensors':removed,'status':'STATIC_VALIDATION_REQUIRED'}))

if __name__=='__main__':main()
