"""Diagnostic client: no velocity commands, readiness before every goal."""
import argparse,json,time
from pathlib import Path

def main():
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.node import Node
    from lifecycle_msgs.srv import GetState
    from nav2_msgs.action import NavigateToPose
    from ament_index_python.packages import get_package_share_directory
    args=argparse.ArgumentParser();args.add_argument('--output',type=Path,required=True);a,_=args.parse_known_args()
    rclpy.init();node=Node('park_explicit_sequence');client=ActionClient(node,NavigateToPose,'/navigate_to_pose')
    required=(Path(get_package_share_directory('wheelchair_navigation'))/'config/required_nav2_nodes.txt').read_text().split()
    assert len(required)==8 and len(set(required))==8
    states={n:node.create_client(GetState,'/'+n+'/get_state') for n in required}
    report={'kind':'DIAGNOSTIC_NOT_FROZEN_CAMPAIGN','mode':'explicit_waypoint','goals':[],'final_result':'NOT_SENT'}
    def wait(future,deadline):
        while rclpy.ok() and not future.done() and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.05)
        if not future.done():raise TimeoutError('Diagnostic future deadline')
        return future.result()
    def ready():
        deadline=time.monotonic()+120.
        for n,c in states.items():
            if not c.wait_for_service(timeout_sec=max(0,deadline-time.monotonic())):raise RuntimeError('Lifecycle service absent: '+n)
        futures={n:c.call_async(GetState.Request()) for n,c in states.items()}
        snapshot={n:wait(f,deadline).current_state.id for n,f in futures.items()}
        if any(s!=3 for s in snapshot.values()):raise RuntimeError('Lifecycle not ACTIVE')
        if not client.server_is_ready():raise RuntimeError('Navigation action unavailable')
        return snapshot
    try:
        for stage,x,y in [('waypoint',-1.,-9.),('final',1.,-9.)]:
            event={'stage':stage,'pose':[x,y,0.0],'readiness':ready(),'start_monotonic':time.monotonic()}
            report['goals'].append(event)
            goal=NavigateToPose.Goal();goal.pose.header.frame_id='map';goal.pose.pose.position.x=x;goal.pose.pose.position.y=y;goal.pose.pose.orientation.w=1.
            # Match frozen client: timestamp zero and yaw zero for both targets.
            handle=wait(client.send_goal_async(goal),time.monotonic()+120.)
            if not handle or not handle.accepted:event['result']='REJECTED';break
            try: result=wait(handle.get_result_async(),time.monotonic()+300.)
            except TimeoutError:
                wait(handle.cancel_goal_async(),time.monotonic()+10.);event['result']='TIMEOUT';break
            event.update(result={4:'SUCCEEDED',5:'CANCELED',6:'ABORTED'}.get(result.status,str(result.status)),
                         error_code=getattr(result.result,'error_code',None),error_msg=getattr(result.result,'error_msg',''),end_monotonic=time.monotonic())
            if stage=='final':report['final_result']=event['result']
            if event['result']!='SUCCEEDED':break
    except Exception as exc:
        report['exception_type']=type(exc).__name__;report['failure']=str(exc)
    finally:
        a.output.write_text(json.dumps(report,indent=2)+'\n');client.destroy();node.destroy_node();rclpy.try_shutdown()
    return 0 if report['final_result']=='SUCCEEDED' else 2

if __name__=='__main__':raise SystemExit(main())
