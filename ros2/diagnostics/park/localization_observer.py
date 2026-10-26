"""Passive ROS observer for comparison with independently recorded Gazebo poses."""
import argparse,json,math,time
from pathlib import Path

def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy,ReliabilityPolicy
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from tf2_msgs.msg import TFMessage
    from sensor_msgs.msg import LaserScan
    from action_msgs.msg import GoalStatusArray
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a,_=p.parse_known_args()
    rclpy.init();node=Node('park_passive_localization_observer')
    with a.output.open('w',buffering=1) as out:
        def emit(kind,stamp,**values):
            out.write(json.dumps({'kind':kind,'stamp':stamp.sec+stamp.nanosec/1e9 if stamp is not None else None,'wall_monotonic':time.monotonic(),**values})+'\n')
        def pose(kind,m):
            v=m.pose.pose;p=v.position;q=v.orientation
            emit(kind,m.header.stamp,frame=m.header.frame_id,x=p.x,y=p.y,z=p.z,q=[q.x,q.y,q.z,q.w])
        def tf(m,static=False):
            for t in m.transforms:
                if not static and (t.header.frame_id,t.child_frame_id) not in {('map','odom'),('odom','base_link')}:continue
                p=t.transform.translation;q=t.transform.rotation
                emit('tf_static' if static else 'tf',t.header.stamp,parent=t.header.frame_id,child=t.child_frame_id,x=p.x,y=p.y,z=p.z,q=[q.x,q.y,q.z,q.w])
        def scan(m):
            valid=[r for r in m.ranges if math.isfinite(r) and m.range_min<=r<=m.range_max]
            emit('scan',m.header.stamp,frame=m.header.frame_id,finite=len(valid),near_under_1m=sum(r<1 for r in valid),far_over_2m=sum(r>=2 for r in valid))
        def status(m):
            emit('navigation_status',None,goals=[{'id':bytes(s.goal_info.goal_id.uuid).hex(),'created':s.goal_info.stamp.sec+s.goal_info.stamp.nanosec/1e9,'status':s.status} for s in m.status_list])
        subscriptions=[node.create_subscription(Odometry,'/odom',lambda m:pose('odom',m),qos_profile_sensor_data),
          node.create_subscription(PoseWithCovarianceStamped,'/amcl_pose',lambda m:pose('amcl',m),qos_profile_sensor_data),
          node.create_subscription(TFMessage,'/tf',tf,qos_profile_sensor_data),
          node.create_subscription(TFMessage,'/tf_static',lambda m:tf(m,True),QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)),
          node.create_subscription(LaserScan,'/scan_fixed',scan,qos_profile_sensor_data)]
        subscriptions.append(node.create_subscription(GoalStatusArray,'/navigate_to_pose/_action/status',status,QoSProfile(depth=10,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)))
        try:rclpy.spin(node)
        except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
        finally:node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
