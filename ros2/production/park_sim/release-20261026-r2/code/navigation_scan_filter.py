"""Physical self-return exclusion, never revealing geometry behind an occlusion."""
import math,time,json,os
from pathlib import Path
from scan_health import ScanHealth
from navigation_cancellation import NavigationCancellation

def filtered_ranges(ranges,angle_min,angle_increment,range_min,range_max,sensor_x=.33):
    result=[]
    for i,r in enumerate(ranges):
        if math.isfinite(r) and range_min<=r<=range_max:
            angle=angle_min+i*angle_increment;x=sensor_x+r*math.cos(angle);y=r*math.sin(angle)
            if -.36<=x<=.36 and -.34<=y<=.34:r=float('nan')
        result.append(r)
    return result

def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    rclpy.init();node=Node('proposed_navigation_lidar_filter');publisher=node.create_publisher(LaserScan,'/scan_fixed',10)
    health=ScanHealth(time.monotonic());failure=None;ready=False;cancellation=NavigationCancellation(node)
    def record(status,reason=None):
        path=os.environ.get('PARK_SENSOR_HEALTH_OUTPUT')
        if path:
            with Path(path).open('a') as output:output.write(json.dumps({'status':status,'reason':reason,'wall_monotonic':time.monotonic(),'last_scan_stamp':health.last_stamp})+'\n')
    def fail(reason):
        nonlocal failure
        if failure is not None:return
        failure=reason;record('FAILED',reason);node.get_logger().error('Sensor guard failed: '+reason);cancellation.start(time.monotonic())
    def callback(m):
        nonlocal ready
        if failure:return
        reason=health.observe(m,time.monotonic())
        if reason:fail(reason);return
        if not ready:ready=True;record('READY');node.get_logger().info('Sensor guard READY')
        m.header.frame_id='navigation_lidar_link'
        m.ranges=filtered_ranges(m.ranges,m.angle_min,m.angle_increment,m.range_min,m.range_max)
        publisher.publish(m)
    subscription=node.create_subscription(LaserScan,'/navigation_scan',callback,qos_profile_sensor_data)
    def check():
        if failure:
            result=cancellation.step(time.monotonic())
            if result:record(result);node.get_logger().info(result);rclpy.try_shutdown()
            return
        reason=health.fault(time.monotonic())
        if reason:fail(reason)
    timer=node.create_timer(.1,check)
    try:rclpy.spin(node)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:record('CLOSED',failure);node.destroy_node();rclpy.try_shutdown()
    return 2 if failure else 0
if __name__=='__main__':raise SystemExit(main())
