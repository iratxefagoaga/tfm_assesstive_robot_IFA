"""Fail-closed arrival acceptance for PARK simulation, independent of Nav2 status."""
import math

def assess(row,mode):
    reasons=[];result=row.get('result',[])
    if not isinstance(result,list) or len(result)!=1:reasons.append('missing_or_multiple_final_rows')
    else:
        final=result[0]
        if final.get('final_goal_nav2_result')!='SUCCEEDED' or final.get('success')!='true':reasons.append('action_not_successful')
        if mode=='memory' and final.get('waypoint_nav2_result')!='SUCCEEDED':reasons.append('waypoint_not_successful')
    if not row.get('cleanup_ok'):reasons.append('unclean_shutdown')
    if any(row.get('categories',{}).get(k,0) for k in ['readiness','action_ack_timeout','cleanup_escalation','abnormal_exit','sensor_fault']):reasons.append('infrastructure_failure')
    if row.get('physical_pose_samples',0)<2:reasons.append('insufficient_truth_samples')
    if row.get('physical_pose_frame')!='world/default' or row.get('physical_pose_entity')!='wheelchair':reasons.append('unexpected_truth_frame_or_entity')
    if row.get('physical_pose_reference')!='nav2_success_observed':reasons.append('missing_success_time_reference')
    age=row.get('physical_pose_age_s')
    if not isinstance(age,(float,int)) or not math.isfinite(age) or not 0<=age<=2.:reasons.append('stale_or_missing_truth')
    distance=angle=None
    try:
        def measure(position,orientation):
            xyz=[float(position.get(k,0)) for k in ['x','y','z']];q=[float(orientation.get(k,0)) for k in ['x','y','z','w']]
            if not all(math.isfinite(v) for v in xyz+q) or abs(sum(v*v for v in q)-1)>1e-3:raise ValueError('Invalid pose')
            x,y,z,w=q;return math.hypot(xyz[0]-1,xyz[1]+9),abs(math.atan2(2*(w*z+x*y),1-2*(y*y+z*z)))
        distance,angle=measure(row['physical_arrival_position'],row['physical_arrival_orientation'])
        settled_distance,settled_angle=measure(row['physical_final_position'],row['physical_final_orientation'])
        if distance>.25:reasons.append('position_outside_tolerance')
        if angle>.25:reasons.append('yaw_outside_tolerance')
        if settled_distance>.25 or settled_angle>.25:reasons.append('settled_pose_outside_tolerance')
    except (KeyError,TypeError,ValueError,AttributeError):reasons.append('invalid_truth_pose')
    return {'accepted':not reasons,'reasons':reasons,'position_error_m':distance,'yaw_error_rad':angle,'physical_hardware_validated':False}
