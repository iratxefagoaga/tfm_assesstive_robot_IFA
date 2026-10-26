"""Release the one-shot mission's embedding worker after its first Nav2 goal."""
import importlib.util
from pathlib import Path
from ament_index_python.packages import get_package_prefix

def main():
    import rclpy
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
    from action_msgs.msg import GoalStatusArray
    from wheelchair_memory.memory_node import MemoryNode
    path=Path(get_package_prefix('wheelchair_assistive_bt'))/'lib/wheelchair_assistive_bt/managed_memory_process.py'
    spec=importlib.util.spec_from_file_location('original_managed_memory_lifecycle',path);lifecycle=importlib.util.module_from_spec(spec);spec.loader.exec_module(lifecycle)
    def factory():
        node=MemoryNode()
        def goal_started(message):
            if any(g.status in {1,2} for g in message.status_list):
                node.get_logger().info('MISSION_MEMORY_RELEASE: retrieval complete; first Nav2 goal accepted');rclpy.try_shutdown()
        node.mission_subscription=node.create_subscription(GoalStatusArray,'/navigate_to_pose/_action/status',goal_started,QoSProfile(depth=10,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE))
        return node
    lifecycle.run_node(factory,SingleThreadedExecutor)
if __name__=='__main__':main()
