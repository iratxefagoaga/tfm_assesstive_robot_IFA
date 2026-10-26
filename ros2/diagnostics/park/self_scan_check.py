"""Static ray/triangle intersection against the exact existing chair visual mesh."""
import argparse,json,math,struct,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from diagnose import digest
p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
model=ET.parse(a.code_root/'ros2/src/wheelchair_gazebo/models/wheelchair/model.sdf').getroot().find('model')
base=model.find("link[@name='base_link']");lidar=model.find("link[@name='lidar_link']")
visual=base.find("visual[@name='chair']");mesh_config=visual.find('geometry/mesh')
uri=mesh_config.findtext('uri');assert uri.startswith('model://wheelchair/')
mesh=a.code_root/'ros2/src/wheelchair_gazebo/models/wheelchair'/uri.removeprefix('model://wheelchair/')
data=mesh.read_bytes();n=struct.unpack('<I',data[80:84])[0]
assert len(data)==84+50*n
dtype=np.dtype([('n','<f4',(3,)),('v','<f4',(3,3)),('a','<u2')]);tri=np.frombuffer(data,offset=84,count=n,dtype=dtype)['v'].astype(float)*np.array(list(map(float,mesh_config.findtext('scale','1 1 1').split())))
def pose(element):return np.array(list(map(float,element.findtext('pose','0 0 0 0 0 0').split())))
assert np.allclose(pose(base)[3:],0) and np.allclose(pose(lidar)[3:],0) and np.allclose(pose(visual)[3:],0),'Rotated source model requires a full frame transform'
origin=pose(lidar)[:3]-pose(base)[:3]-pose(visual)[:3]
ray_config=lidar.find('sensor/ray');scan=ray_config.find('scan/horizontal')
angles=np.linspace(float(scan.findtext('min_angle')),float(scan.findtext('max_angle')),int(scan.findtext('samples')))
e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];s=origin-tri[:,0];q=np.cross(s,e1)
hits=[]
for angle in angles:
    d=np.array([np.cos(angle),np.sin(angle),0.]);h=np.cross(np.broadcast_to(d,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h)
    valid=np.abs(det)>1e-10;inv=np.zeros_like(det);inv[valid]=1/det[valid]
    u=inv*np.einsum('ij,ij->i',s,h);v=inv*np.einsum('ij,j->i',q,d);t=inv*np.einsum('ij,ij->i',e2,q)
    valid&=(u>=0)&(v>=0)&(u+v<=1)&(t>=float(ray_config.findtext('range/min')))&(t<=float(ray_config.findtext('range/max')))
    hits.append(float(t[valid].min()) if valid.any() else None)
def ray(angle):return hits[round((angle-angles[0])/(angles[1]-angles[0]))]
result={'kind':'STATIC_VISUAL_SELF_INTERSECTION_NOT_NEW_SIMULATION','mesh_sha256':digest(mesh),'laser_origin_in_visual_coordinates':origin.tolist(),
        'rays':len(angles),'predicted_hits_under_1m':sum(h is not None and h<1 for h in hits),'south_ray_m':ray(-math.pi/2),'back_ray_m':ray(math.pi-.02),'front_ray_m':ray(0),
        'limitation':'Static nominal poses; no occlusion by other robot links or environment; comparison with actual scan required.'}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
