"""Cancel Nav2 before ending a simulator pipeline, keeping clock/TF alive."""
class ActiveGoals:
    def __init__(self):self.states={}
    def update(self,topic,goals):
        for identity,status in goals:self.states[(topic,identity)]=status
    def complete(self,expected):
        return not any(s in {1,2,3} for s in self.states.values()) and all(self.states.get(('/navigate_to_pose',g)) in {4,5,6} for g in expected)

class NavigationCancellation:
    def __init__(self,node):
        from action_msgs.srv import CancelGoal
        from action_msgs.msg import GoalStatusArray
        from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
        self.node=node;self.request_type=CancelGoal.Request;self.client=node.create_client(CancelGoal,'/navigate_to_pose/_action/cancel_goal');self.states=ActiveGoals();self.started=None;self.future=None
        qos=QoSProfile(depth=10,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
        topics=['/navigate_to_pose','/follow_path','/compute_path_to_pose','/spin','/backup','/drive_on_heading','/wait']
        self.subscriptions=[node.create_subscription(GoalStatusArray,t+'/_action/status',lambda m,t=t:self.states.update(t,[(bytes(g.goal_info.goal_id.uuid).hex(),g.status) for g in m.status_list]),qos) for t in topics]
    def start(self,now):self.started=now
    def step(self,now):
        if self.future is None and self.client.service_is_ready():self.future=self.client.call_async(self.request_type())
        if self.future is not None and self.future.done():
            try:
                response=self.future.result();expected=[bytes(g.goal_id.uuid).hex() for g in response.goals_canceling]
                if self.states.complete(expected):return 'CANCELLATION_COMPLETE'
            except Exception:return 'CANCELLATION_ERROR'
        if self.future is None and self.states.complete([]):return 'NO_ACTIVE_NAVIGATION'
        if now-self.started>2.:return 'CANCELLATION_TIMEOUT'
        return None
