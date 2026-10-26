"""Bounded read-only transform probe; does not change lifecycle or publish."""
import argparse,json,os,time
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--domain',default='91');p.add_argument('--rmw',choices=['rmw_fastrtps_cpp','rmw_cyclonedds_cpp']);a=p.parse_args();os.environ['ROS_DOMAIN_ID']=a.domain;os.environ['ROS_LOCALHOST_ONLY']='1'
    if a.rmw:os.environ['RMW_IMPLEMENTATION']=a.rmw
    import rclpy
    from rclpy.parameter import Parameter
    from tf2_ros import Buffer,TransformListener
    rclpy.init();node=rclpy.create_node('park_tf_readonly_probe',parameter_overrides=[Parameter('use_sim_time',value=True)])
    buffer=Buffer(node=node);listener=TransformListener(buffer,node)
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.1)
    result={}
    for target,source in [('base_link','lidar_link'),('odom','lidar_link'),('map','base_link')]:
        try:
            t=buffer.lookup_transform(target,source,rclpy.time.Time());p=t.transform.translation
            result[f'{target}<-{source}']={'available':True,'x':p.x,'y':p.y,'z':p.z}
        except Exception as exc:result[f'{target}<-{source}']={'available':False,'reason':str(exc)}
    result['frames']=buffer.all_frames_as_yaml();a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
