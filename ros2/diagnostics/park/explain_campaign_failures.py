"""Synchronize existing evidence; do not infer a root cause from log labels alone."""
import argparse,json,math
from pathlib import Path

def read(path):return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
def yaw(q):
    x,y,z,w=q;return math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
def latest(rows,t):return next((r for r in reversed(rows) if r['wall_monotonic']<=t),None)
def main():
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise RuntimeError('Refusing overwrite')
    results=json.loads((a.campaign/'results.json').read_text());report=[]
    for r in results['runs']:
        if r['accepted']:continue
        directory=a.campaign/r['directory']/r['mode'];events=read(directory/'localization.jsonl');poses=read(directory/'physical_pose.jsonl');health=read(directory/'sensor_health.jsonl');resources=read(directory/'resources.jsonl')
        item={'index':r['index'],'condition':r['condition'],'categories':r['categories'],'acceptance':r['decision'],'physical_acceptance_recomputed_from_raw':None}
        if r['action_success']:
            pilot=json.loads((directory.parent/'pilot_results.json').read_text())[0]
            goalid=pilot.get('arrival_goal_id')
            success=next((e for e in events if e['kind']=='navigation_status' and any(g['id']==goalid and g['status']==4 for g in e['goals'])),None)
            if success:
                t=success['wall_monotonic'];transform=latest([e for e in events if e['kind']=='tf' and e['parent']=='map' and e['child']=='odom'],t);odom=latest([e for e in events if e['kind']=='odom'],t);truth=latest(poses,t)
                if transform and odom and truth:
                    angle=yaw(transform['q']);x=transform['x']+math.cos(angle)*odom['x']-math.sin(angle)*odom['y'];y=transform['y']+math.sin(angle)*odom['x']+math.cos(angle)*odom['y'];actual=truth['position'];tx=actual.get('x',0);ty=actual.get('y',0)
                    item['arrival_decomposition']={'estimated_map_xy':[x,y],'gazebo_xy':[tx,ty],'estimated_goal_error_m':math.hypot(x-1,y+9),'actual_goal_error_m':math.hypot(tx-1,ty+9),'localization_position_bias_m':math.hypot(x-tx,y-ty),'estimated_minus_actual_xy':[x-tx,y-ty],'transform_age_wall_s':t-transform['wall_monotonic'],'odom_age_wall_s':t-odom['wall_monotonic'],'truth_age_wall_s':t-truth['wall_monotonic'],'odom_sim_stamp':odom['stamp'],'transform_sim_stamp':transform['stamp']}
        failure=next((h for h in health if h['status']=='FAILED'),None)
        if failure:
            t=failure['wall_monotonic'];window=[e for e in events if t-2<=e['wall_monotonic']<=t+.6];physical=[e for e in poses if t-2<=e['wall_monotonic']<=t+.6]
            item['sensor_failure']={'event':failure,'nearby_resources':latest(resources,t),'streams':{k:[{'wall':e['wall_monotonic'],'sim':e['stamp']} for e in window if e['kind']==k] for k in ['scan','odom','amcl']},'gazebo_pose_stream':[{'wall':e['wall_monotonic'],'sim':float(e['stamp'].get('sec',0))+float(e['stamp'].get('nsec',0))/1e9} for e in physical],'health_events':health}
        report.append(item)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    for item in report:
        concise={k:v for k,v in item.items() if k!='sensor_failure'}
        if 'sensor_failure' in item:
            s=item['sensor_failure'];concise['sensor_summary']={'failure':s['event'],'resources':s['nearby_resources'],'stream_counts':{k:len(v) for k,v in s['streams'].items()},'gazebo_samples':len(s['gazebo_pose_stream'])}
        print(json.dumps(concise))

if __name__=='__main__':main()
