"""Proposed additional low lidar; source model and original sensor remain intact."""
import argparse,ast,copy,hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
from prepare_sensor_candidate import collision_signature

def main():
    p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--goal-margin',action='store_true');p.add_argument('--sensor-validation',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    source=a.code_root/'ros2/src';gazebo=source/'wheelchair_gazebo';tree=ET.parse(gazebo/'models/wheelchair/model.sdf');model=tree.getroot().find('model');before=collision_signature(tree.getroot())
    link=copy.deepcopy(model.find("link[@name='lidar_link']"));link.set('name','navigation_lidar_link');link.find('pose').text='.33 0 .08 0 0 0'
    sensor=link.find('sensor');sensor.set('name','proposed_navigation_lidar');sensor.find('topic').text='/navigation_scan'
    # A generic simulated enclosure fits entirely inside the existing planar footprint.
    visual=ET.SubElement(link,'visual',name='proposed_lidar_enclosure');geometry=ET.SubElement(visual,'geometry');cylinder=ET.SubElement(geometry,'cylinder');ET.SubElement(cylinder,'radius').text='.025';ET.SubElement(cylinder,'length').text='.03'
    material=ET.SubElement(visual,'material');ET.SubElement(material,'diffuse').text='.9 .15 .05 1'
    model.append(link);joint=ET.SubElement(model,'joint',name='navigation_lidar_joint',type='fixed');ET.SubElement(joint,'parent').text='base_link';ET.SubElement(joint,'child').text='navigation_lidar_link'
    assert collision_signature(tree.getroot())==before
    share=a.output/'share';index=share/'ament_index/resource_index/packages';index.mkdir(parents=True)
    for package in ['wheelchair_gazebo','wheelchair_description']:(index/package).touch()
    target=share/'wheelchair_gazebo';(target/'models/wheelchair').mkdir(parents=True);(target/'worlds').symlink_to(gazebo/'worlds',target_is_directory=True)
    for item in (gazebo/'models').iterdir():
        if item.name!='wheelchair':(target/'models'/item.name).symlink_to(item,target_is_directory=item.is_dir())
    for item in (gazebo/'models/wheelchair').iterdir():
        if item.name!='model.sdf':(target/'models/wheelchair'/item.name).symlink_to(item,target_is_directory=item.is_dir())
    sdf=target/'models/wheelchair/model.sdf';tree.write(sdf,encoding='utf-8',xml_declaration=True)
    description=share/'wheelchair_description';shutil.copytree(source/'wheelchair_description/urdf',description/'urdf');(description/'launch').symlink_to(source/'wheelchair_description/launch',target_is_directory=True)
    joints=description/'urdf/joints.xacro';text=joints.read_text();text=text.replace('</robot>','''  <link name="navigation_lidar_link"/>
  <joint name="navigation_lidar_joint" type="fixed">
    <parent link="base_link"/><child link="navigation_lidar_link"/>
    <origin xyz="0.33 0 -0.12" rpy="0 0 0"/>
  </joint>
</robot>''');joints.write_text(text)
    hashed={str(f.relative_to(a.output)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [sdf,*sorted((description/'urdf').glob('*.xacro'))]}
    manifest={'status':'PROPOSED_MOUNT_NOT_VALIDATED','physical_mount_measured':False,'additional_sensor_not_existing_hardware_claim':True,
      'candidate_sha256':hashlib.sha256(sdf.read_bytes()).hexdigest(),'extra_sha256':hashed,
      'pose_model_m':[.33,0,.08],'pose_base_link_m':[.33,0,-.12],'original_sensor_retained':True,'collision_geometry_unchanged':True,
      'assumptions':['generic sensor, not a validated commercial product','flat simulated floor; 6.5cm enclosure ground clearance','physical mounting and terrain suitability require verification'],
      'static_test_required':'filtered external returns >=100 and >=90% endpoints within 0.15m of original occupied map cells'}
    (a.output/'overlay_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(a.output)
    if a.goal_margin:
        import yaml
        (index/'wheelchair_navigation').touch();navigation=share/'wheelchair_navigation';shutil.copytree(source/'wheelchair_navigation/config',navigation/'config')
        for name in ['maps','launch']:(navigation/name).symlink_to(source/'wheelchair_navigation'/name,target_is_directory=True)
        parameters=navigation/'config/nav2_params.yaml';original=yaml.safe_load(parameters.read_text());changed=copy.deepcopy(original)
        checker=changed['controller_server']['ros__parameters']['general_goal_checker'];checker['xy_goal_tolerance']=.15;checker['yaw_goal_tolerance']=.15
        parameters.write_text(yaml.safe_dump(changed,sort_keys=False))
        manifest['goal_tolerances']={'xy_m':.15,'yaw_rad':.15,'reason':'Reserve 0.10m of the physical 0.25m arrival budget for localisation/odometry error; no timeout increase'}
        for f in (navigation/'config').rglob('*'):
            if f.is_file():manifest['extra_sha256'][str(f.relative_to(a.output))]=hashlib.sha256(f.read_bytes()).hexdigest()
    if a.sensor_validation:
        validation=json.loads(a.sensor_validation.read_text());protocol=json.loads((a.sensor_validation.parent/'protocol.json').read_text())
        if validation['status']!='PASSED_PROPOSED_SENSOR_STATIC_ONLY' or protocol['candidate_sha256']!=manifest['candidate_sha256']:raise RuntimeError('Static test does not validate these SDF bytes')
        manifest.update(status='ISOLATED_DIAGNOSTIC_OVERLAY',sensor_validation=str(a.sensor_validation))
    (a.output/'overlay_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
