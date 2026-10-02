#!/usr/bin/env python3
import sys
import time
import rclpy
from rclpy.executors import ExternalShutdownException
from lifecycle_msgs.srv import GetState
from wheelchair_interfaces.srv import MemoryQuery, NavigationRecommendation
from nav2_msgs.action import NavigateToPose, ComputePathToPose
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from rosgraph_msgs.msg import Clock
from rclpy.action import ActionClient

from pathlib import Path
from ament_index_python.packages import get_package_share_directory


def required_nav2_nodes():
    path = Path(get_package_share_directory('wheelchair_navigation')) / 'config/required_nav2_nodes.txt'
    nodes = tuple(line.strip() for line in path.read_text().splitlines() if line.strip())
    if not nodes or len(nodes) != len(set(nodes)):
        raise RuntimeError('Invalid canonical Nav2 lifecycle node list')
    return nodes


NAV_NODES = required_nav2_nodes()

def all_active(states):
    return set(states) == set(NAV_NODES) and all(v == 3 for v in states.values())

def main():
    rclpy.init()
    node = rclpy.create_node('smoke_readiness')
    mode = node.declare_parameter('mode', 'nav2').value
    limit = node.declare_parameter('readiness_timeout_s', 120.0).value
    deadline = time.monotonic() + limit
    def wait_service(client):
        while rclpy.ok() and time.monotonic() < deadline:
            if client.wait_for_service(timeout_sec=0.5):
                return
        raise RuntimeError('readiness failed: ' + client.srv_name)
    def call(client, request):
        wait_service(client)
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future, timeout_sec=max(0, deadline-time.monotonic()))
        if not future.done() or future.result() is None:
            raise RuntimeError('readiness response failed: ' + client.srv_name)
        return future.result()
    try:
        if mode == 'memory':
            client = node.create_client(MemoryQuery, '/memory/query')
            request = MemoryQuery.Request()
            for key, default in [('query', 'navegar evitando la mesa'), ('user_id', 'U01'),
                                 ('location', 'salon'), ('task', 'navegacion'), ('goal', 'dormitorio')]:
                setattr(request, key, node.declare_parameter(key, default).value)
            request.k = node.declare_parameter('k', 3).value
            response = call(client, request)
            if not response.success:
                raise RuntimeError('memory preflight failed: ' + response.message)
        elif mode == 'recommendation':
            wait_service(node.create_client(NavigationRecommendation, '/memory/navigation_recommendation'))
        elif mode == 'nav2':
            clients = {name: node.create_client(GetState, '/' + name + '/get_state') for name in NAV_NODES}
            action = ActionClient(node, NavigateToPose, '/navigate_to_pose')
            planner = ActionClient(node, ComputePathToPose, '/compute_path_to_pose')
            seen = {}
            def observe(key, msg):
                seen[key] = time.monotonic()
            subscriptions = [
                node.create_subscription(Odometry, '/odom', lambda msg: observe('odom', msg), 10),
                node.create_subscription(LaserScan, '/scan_fixed', lambda msg: observe('scan', msg), 10),
                node.create_subscription(Clock, '/clock', lambda msg: observe('clock', msg), 10),
            ]
            while rclpy.ok() and time.monotonic() < deadline:
                states = {name: call(client, GetState.Request()).current_state.id
                          for name, client in clients.items()}
                if (all_active(states) and action.server_is_ready() and planner.server_is_ready()
                        and len(seen) == 3 and all(time.monotonic() - t < 1.0 for t in seen.values())):
                    node.get_logger().info('READY nav2: all eight lifecycle nodes ACTIVE and action available')
                    break
                rclpy.spin_once(node, timeout_sec=0.2)
            else:
                raise RuntimeError('Nav2 readiness failed')
        else:
            raise RuntimeError('unknown readiness mode: ' + mode)
        node.get_logger().info('READY ' + mode)
        return 0
    except (KeyboardInterrupt, ExternalShutdownException):
        return 1
    except Exception as error:
        node.get_logger().error(str(error))
        return 1
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    sys.exit(main())
