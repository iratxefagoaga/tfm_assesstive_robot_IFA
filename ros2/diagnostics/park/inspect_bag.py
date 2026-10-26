"""Extract diagnostic summaries from a closed rosbag, with no running ROS graph."""
import argparse,json,math
from pathlib import Path

def main():
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
    p=argparse.ArgumentParser();p.add_argument('bag',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(a.bag),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    types={t.name:get_message(t.type) for t in reader.get_all_topics_and_types()}
    summary={'kind':'OFFLINE_BAG_INSPECTION','counts':{},'odom':[],'amcl':[],'map_odom':[],'initial_scans':[]}
    while reader.has_next():
        topic,raw,stamp=reader.read_next();summary['counts'][topic]=summary['counts'].get(topic,0)+1
        if topic not in {'/odom','/amcl_pose','/tf','/scan_fixed'}:continue
        m=deserialize_message(raw,types[topic])
        if topic in {'/odom','/amcl_pose'}:
            pose=m.pose.pose;key='odom' if topic=='/odom' else 'amcl'
            summary[key].append([stamp/1e9,pose.position.x,pose.position.y])
        elif topic=='/tf':
            for t in m.transforms:
                if t.header.frame_id=='map' and t.child_frame_id=='odom':
                    z=t.transform.rotation.z;w=t.transform.rotation.w
                    summary['map_odom'].append([stamp/1e9,t.transform.translation.x,t.transform.translation.y,2*math.atan2(z,w)])
        elif len(summary['initial_scans'])<5:
            finite=[r for r in m.ranges if math.isfinite(r) and m.range_min<=r<=m.range_max]
            def ray(angle):
                i=round((angle-m.angle_min)/m.angle_increment)
                value=m.ranges[i] if 0<=i<len(m.ranges) else float('inf')
                return value if math.isfinite(value) else None
            summary['initial_scans'].append({'stamp':stamp/1e9,'total':len(m.ranges),'valid_finite':len(finite),'under_1m':sum(r<1 for r in finite),'south_ray_m':ray(-math.pi/2),'front_ray_m':ray(0),'back_ray_m':ray(math.pi-.02)})
    # Preserve series in a new diagnostic artifact; no original bag modification.
    for key in ['odom','amcl','map_odom']:
        points=summary[key]
        if points:summary[key+'_bounds']={'samples':len(points),'first':points[0],'last':points[-1],'max_abs_y_change':max(abs(v[2]-points[0][2]) for v in points)}
    a.output.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in {'odom','amcl','map_odom'}},indent=2))
if __name__=='__main__':main()
