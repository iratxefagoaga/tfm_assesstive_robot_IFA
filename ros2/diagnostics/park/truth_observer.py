"""Read Gazebo world pose independently of ROS localisation; never publish."""
import argparse,json,signal,subprocess,time
from pathlib import Path

def wheelchair_pose(message):
    for pose in message.get('pose',[]):
        if pose.get('name')=='wheelchair':
            return {'frame':'world/default','entity':'wheelchair','stamp':message.get('header',{}).get('stamp',{}),
                    'position':pose.get('position',{}),'orientation':pose.get('orientation',{})}
    return None

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    proc=subprocess.Popen(['gz','topic','-e','--json-output','-t','/world/default/pose/info'],stdout=subprocess.PIPE,text=True)
    def stop(*_):
        if proc.poll() is None:proc.send_signal(signal.SIGINT)
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    decoder=json.JSONDecoder();buffer=''
    try:
        with a.output.open('w',buffering=1) as out:
            for line in proc.stdout:
                buffer+=line
                while buffer.strip():
                    buffer=buffer.lstrip()
                    try:message,end=decoder.raw_decode(buffer)
                    except ValueError:break
                    buffer=buffer[end:];pose=wheelchair_pose(message);now=time.monotonic()
                    if pose:
                        pose['wall_monotonic']=now;out.write(json.dumps(pose)+'\n')
                if len(buffer)>4_000_000:raise RuntimeError('Invalid Gazebo pose stream')
    finally:
        stop();proc.wait(timeout=15)
if __name__=='__main__':main()
