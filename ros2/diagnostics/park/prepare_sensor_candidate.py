"""Prepare (never deploy) an isolated SDF candidate excluding robot visuals from GPU lidar."""
import argparse,copy,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path

def collision_signature(tree):
    return [ET.tostring(c,encoding='unicode') for c in tree.findall('.//collision')]
def masked_candidate(original):
    tree=copy.deepcopy(original);before=collision_signature(tree)
    visuals=tree.findall('model/link/visual')
    for v in visuals:
        flag=v.find('visibility_flags')
        if flag is None:flag=ET.SubElement(v,'visibility_flags')
        flag.text='1'
    lidar=tree.find("model/link[@name='lidar_link']/sensor[@type='gpu_lidar']/ray")
    if lidar is None:raise ValueError('Expected original gpu_lidar/ray layout')
    mask=lidar.find('visibility_mask')
    if mask is None:mask=ET.SubElement(lidar,'visibility_mask')
    mask.text='4294967294'
    assert before==collision_signature(tree)
    return tree
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--code-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    source=a.code_root/'ros2/src/wheelchair_gazebo/models/wheelchair/model.sdf'
    tree=ET.parse(source).getroot();candidate=masked_candidate(tree)
    ET.ElementTree(candidate).write(a.output/'wheelchair-self-mask.sdf',encoding='utf-8',xml_declaration=True)
    report={'status':'PREPARED_NOT_RUNTIME_VALIDATED_NOT_DEPLOYED','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'collision_geometry_unchanged':True,'sensor_pose_and_range_unchanged':True,'environment_and_maps_unchanged':True,
      'source':'https://sdformat.org/spec/1.9/sensor/','visual_flags':1,'lidar_mask':4294967294,
      'test_required':'Verify external obstacles still detected, self returns suppressed, and no false navigation improvement by disabling collision checks. Then controlled comparison; original maps and collision checks retained.'}
    (a.output/'candidate_manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
