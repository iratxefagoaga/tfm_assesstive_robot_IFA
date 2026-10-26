"""Isolated ament resource overlay for the already-tested candidate; original share unchanged."""
import argparse,json,os,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--sensor-validation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
validation=json.loads(a.sensor_validation.read_text())
if validation['status']!='PASSED_STATIC_SENSOR_ONLY':raise SystemExit('Candidate has not passed sensor validation')
protocol=json.loads((a.sensor_validation.parent/'protocol.json').read_text())
candidate_hash=hashlib.sha256(a.candidate.read_bytes()).hexdigest()
if protocol['models'].get(str(a.candidate))!=candidate_hash:raise SystemExit('Candidate differs from the sensor-tested bytes')
a.output.mkdir(parents=True,exist_ok=False)
index=a.output/'share/ament_index/resource_index/packages';index.mkdir(parents=True);(index/'wheelchair_gazebo').touch()
share=a.output/'share/wheelchair_gazebo';models=share/'models';models.mkdir(parents=True)
source=a.code_root/'ros2/src/wheelchair_gazebo'
(share/'worlds').symlink_to(source/'worlds',target_is_directory=True)
for model in (source/'models').iterdir():
    if model.name!='wheelchair':(models/model.name).symlink_to(model,target_is_directory=model.is_dir())
wheel=models/'wheelchair';wheel.mkdir()
for item in (source/'models/wheelchair').iterdir():
    target=a.candidate if item.name=='model.sdf' else item
    (wheel/item.name).symlink_to(target,target_is_directory=target.is_dir())
(a.output/'overlay_manifest.json').write_text(json.dumps({'status':'ISOLATED_DIAGNOSTIC_OVERLAY','candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_modified':False,'sensor_validation':str(a.sensor_validation)},indent=2)+'\n')
print(a.output)
