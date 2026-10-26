"""Compare simultaneous poses in explicitly defined frames, rejecting stale pairs."""
import argparse,bisect,json,math,statistics
from pathlib import Path

def yaw(q):
    x,y,z,w=q;return math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))

def compare(truth,observations,kind,max_dt=.05):
    ordered=sorted(truth,key=lambda r:float(r['stamp'].get('sec',0))+float(r['stamp'].get('nsec',0))/1e9)
    times=[float(r['stamp'].get('sec',0))+float(r['stamp'].get('nsec',0))/1e9 for r in ordered]
    pairs=[];rejected=0
    for row in observations:
        if row['kind']!=kind:continue
        i=bisect.bisect_left(times,row['stamp']);candidates=[j for j in [i-1,i] if 0<=j<len(times)]
        if not candidates:rejected+=1;continue
        j=min(candidates,key=lambda j:abs(times[j]-row['stamp']));dt=abs(times[j]-row['stamp'])
        if dt>max_dt:rejected+=1;continue
        p=ordered[j]['position'];q=ordered[j]['orientation'];truth_yaw=yaw([q.get(k,1 if k=='w' else 0) for k in ['x','y','z','w']])
        # Odom starts at (0,0), Gazebo at (0,-9), both with yaw=0 in this protocol.
        x=row['x'];y=row['y']-9 if kind=='odom' else row['y']
        error=math.hypot(x-p.get('x',0),y-p.get('y',0));dyaw=yaw(row['q'])-truth_yaw
        pairs.append({'stamp':row['stamp'],'pair_dt_s':dt,'position_error_m':error,'yaw_error_rad':math.atan2(math.sin(dyaw),math.cos(dyaw))})
    errors=[r['position_error_m'] for r in pairs]
    return {'frame_assumption':'odom translated by spawn (0,-9), yaw=0' if kind=='odom' else 'AMCL map coordinates vs Gazebo world coordinates; original map origin unchanged',
            'matched_samples':len(pairs),'rejected_stale_samples':rejected,'max_pair_dt_s':max((r['pair_dt_s'] for r in pairs),default=None),
            'median_position_error_m':statistics.median(errors) if errors else None,'max_position_error_m':max(errors,default=None),
            'last_pair':pairs[-1] if pairs else None,'pairs':pairs}

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    truth=[json.loads(l) for l in (a.input/'physical_pose.jsonl').read_text().splitlines() if l.strip()]
    observations=[json.loads(l) for l in (a.input/'localization.jsonl').read_text().splitlines() if l.strip()]
    result={kind:compare(truth,observations,kind) for kind in ['odom','amcl']}
    transforms=[r for r in observations if r['kind']=='tf' and r['parent']=='map' and r['child']=='odom']
    result['map_odom']={'samples':len(transforms),'first':transforms[0] if transforms else None,'last':transforms[-1] if transforms else None}
    scans=[r for r in observations if r['kind']=='scan']
    result['scan']={'samples':len(scans),'first':scans[0] if scans else None,'last':scans[-1] if scans else None}
    if a.output.exists():raise RuntimeError('Refusing to replace analysis')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:{j:v for j,v in r.items() if j!='pairs'} for k,r in result.items()},indent=2))
if __name__=='__main__':main()
