"""Passive, simultaneous native-Gazebo and ROS laser timing observation."""
import argparse,json,signal,subprocess,threading,time
from pathlib import Path

def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    from rosgraph_msgs.msg import Clock
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rclpy.init();node=Node('park_raw_pipeline_observer');lock=threading.Lock();children=[];threads=[]
    with a.output.open('w',buffering=1) as output:
        def emit(kind,stamp,**data):
            with lock:output.write(json.dumps({'kind':kind,'stamp':stamp,'wall_monotonic':time.monotonic(),**data})+'\n')
        def native(topic):
            child=subprocess.Popen(['gz','topic','-e','--json-output','-t',topic],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True);children.append(child)
            decoder=json.JSONDecoder();buffer=''
            for line in child.stdout:
                buffer+=line
                while buffer.strip():
                    buffer=buffer.lstrip()
                    try:message,end=decoder.raw_decode(buffer)
                    except ValueError:break
                    buffer=buffer[end:];stamp=message.get('header',{}).get('stamp',{})
                    emit('gazebo:'+topic,float(stamp.get('sec',0))+float(stamp.get('nsec',0))/1e9,rays=len(message.get('ranges',[])))
                if len(buffer)>4_000_000:emit('OBSERVER_PARSE_FAILURE',None,topic=topic);break
        for topic in ['/navigation_scan','/scan']:
            thread=threading.Thread(target=native,args=(topic,),daemon=True);threads.append(thread);thread.start()
        def callback(topic,message):emit('ros:'+topic,message.header.stamp.sec+message.header.stamp.nanosec/1e9,rays=len(message.ranges))
        subscriptions=[node.create_subscription(LaserScan,topic,lambda m,t=topic:callback(t,m),qos_profile_sensor_data) for topic in ['/navigation_scan','/scan_fixed','/scan']]
        subscriptions.append(node.create_subscription(Clock,'/clock',lambda m:emit('ros:/clock',m.clock.sec+m.clock.nanosec/1e9),qos_profile_sensor_data))
        try:rclpy.spin(node)
        except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
        finally:
            for child in children:
                if child.poll() is None:child.send_signal(signal.SIGINT)
            for child in children:child.wait(timeout=15)
            for thread in threads:thread.join(timeout=2)
            node.destroy_node();rclpy.try_shutdown()
    return 0

if __name__=='__main__':raise SystemExit(main())
