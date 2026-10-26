"""Collect a fixed, predeclared static scan window. No goals or motion commands."""
import argparse,json,math,time
from pathlib import Path

def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--topic',default='/scan');a,_=p.parse_known_args()
    rclpy.init();node=Node('park_static_sensor_observer')
    scans=[];odometry=[];first=None
    def scan(m):
        nonlocal first
        stamp=m.header.stamp.sec+m.header.stamp.nanosec/1e9
        if first is None:first=stamp
        # Acquisition window, identical for original and candidate. Not a navigation delay.
        if stamp-first<5.0 or len(scans)>=30:return
        ranges=[float(x) if math.isfinite(x) else None for x in m.ranges]
        scans.append({'stamp':stamp,'angle_min':m.angle_min,'angle_increment':m.angle_increment,
                      'range_min':m.range_min,'range_max':m.range_max,'ranges':ranges})
    def odom(m):
        p=m.pose.pose.position;odometry.append([p.x,p.y,p.z])
    s=node.create_subscription(LaserScan,a.topic,scan,qos_profile_sensor_data)
    o=node.create_subscription(Odometry,'/odom',odom,qos_profile_sensor_data)
    deadline=time.monotonic()+120.
    try:
        while rclpy.ok() and time.monotonic()<deadline and len(scans)<30:rclpy.spin_once(node,timeout_sec=.1)
    finally:
        report={'kind':'STATIC_SENSOR_NOT_NAVIGATION','expected_scans':30,'window_starts_5s_after_first_scan':True,
                'scans':scans,'odometry':odometry,'completed':len(scans)==30}
        a.output.write_text(json.dumps(report,indent=2)+'\n');node.destroy_node();rclpy.try_shutdown()
    return 0 if report['completed'] else 2
if __name__=='__main__':raise SystemExit(main())
