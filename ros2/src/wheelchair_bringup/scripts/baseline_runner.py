from pathlib import Path

TFM_ROOT = Path(__file__).resolve().parents[4]
#!/usr/bin/env python3
'''Memory-OFF navigation runner with the common experimental result schema.'''

import csv
import math
import os
import time
from datetime import datetime, timezone

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry, Path
from rclpy.action import ActionClient
from rclpy.node import Node


RESULT_FIELDS = [
    'timestamp_utc', 'experiment_id', 'scenario_id', 'condition', 'run_id',
    'user_id', 'location', 'task', 'goal_label', 'initial_x', 'initial_y',
    'initial_yaw', 'goal_x', 'goal_y', 'nav2_result', 'success', 'time_s',
    'distance_m', 'replanning_events', 'memory_ids', 'semantic_score',
    'context_score', 'final_score', 'strategy', 'waypoint_x', 'waypoint_y',
    'retrieved_strategy', 'strategy_applied', 'selected_waypoint_x', 'selected_waypoint_y',
    'waypoint_nav2_result', 'final_goal_x', 'final_goal_y', 'final_goal_nav2_result',
]


class BaselineRunner(Node):
    def __init__(self):
        super().__init__('baseline_runner')
        defaults = {
            'experiment_id': '', 'scenario_id': '', 'run_id': '', 'user_id': '',
            'location': '', 'task': '', 'goal_label': '', 'initial_x': 2.0,
            'initial_y': -3.0, 'initial_yaw': 0.0, 'goal_x': 2.5, 'goal_y': -3.0,
            'results_path': str(TFM_ROOT / 'experiments/results/baseline_navigation_results.csv'),
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self.client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        self.nav_state_client = self.create_client(GetState, '/bt_navigator/get_state')
        self.create_subscription(Odometry, '/odom', self.on_odom, 20)
        self.create_subscription(Path, '/plan', self.on_plan, 10)
        self.previous_xy = None
        self.distance_m = 0.0
        self.plan_messages = 0
        self.started_at = None
        self.sent = False
        self.state_request_pending = False
        self.create_timer(1.0, self.send_goal_once)

    def value(self, name):
        return self.get_parameter(name).value

    def on_odom(self, msg):
        if self.started_at is None:
            return
        point = (msg.pose.pose.position.x, msg.pose.pose.position.y)
        if self.previous_xy is not None:
            self.distance_m += math.dist(self.previous_xy, point)
        self.previous_xy = point

    def on_plan(self, _msg):
        if self.started_at is not None:
            self.plan_messages += 1

    def send_goal_once(self):
        if self.sent or self.state_request_pending:
            return
        if not self.client.wait_for_server(timeout_sec=0.1):
            return
        if not self.nav_state_client.wait_for_service(timeout_sec=0.1):
            return
        self.state_request_pending = True
        self.nav_state_client.call_async(GetState.Request()).add_done_callback(self.on_nav_state)

    def on_nav_state(self, future):
        self.state_request_pending = False
        try:
            active = future.result().current_state.label == 'active'
        except Exception as error:
            self.get_logger().warn(f'Unable to read bt_navigator state: {error}')
            return
        if not active:
            self.get_logger().info('Waiting for bt_navigator lifecycle state active...')
            return
        self.sent = True
        self.previous_xy = None
        self.distance_m = 0.0
        self.plan_messages = 0
        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = self.value('goal_x')
        goal.pose.pose.position.y = self.value('goal_y')
        goal.pose.pose.orientation.w = 1.0
        self.started_at = time.monotonic()
        self.client.send_goal_async(goal).add_done_callback(self.on_goal_response)
        self.get_logger().info('Baseline MEMORY=OFF: scenario goal sent.')

    def on_goal_response(self, future):
        try:
            handle = future.result()
        except Exception as error:
            self.save(f'GOAL_ERROR: {error}')
            return
        if not handle.accepted:
            self.save('REJECTED')
            return
        handle.get_result_async().add_done_callback(self.on_result)

    def on_result(self, future):
        try:
            status = future.result().status
        except Exception as error:
            self.save(f'RESULT_ERROR: {error}')
            return
        labels = {
            GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED',
            GoalStatus.STATUS_ABORTED: 'ABORTED',
            GoalStatus.STATUS_CANCELED: 'CANCELED',
        }
        self.save(labels.get(status, f'STATUS_{status}'))

    def save(self, status):
        elapsed = time.monotonic() - self.started_at if self.started_at else None
        row = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'experiment_id': self.value('experiment_id'),
            'scenario_id': self.value('scenario_id'),
            'condition': 'MEMORY_OFF', 'run_id': self.value('run_id'),
            'user_id': self.value('user_id'), 'location': self.value('location'),
            'task': self.value('task'), 'goal_label': self.value('goal_label'),
            'initial_x': self.value('initial_x'), 'initial_y': self.value('initial_y'),
            'initial_yaw': self.value('initial_yaw'), 'goal_x': self.value('goal_x'),
            'goal_y': self.value('goal_y'), 'nav2_result': status,
            'success': str(status == 'SUCCEEDED').lower(),
            'time_s': '' if elapsed is None else f'{elapsed:.3f}',
            'distance_m': '' if elapsed is None else f'{self.distance_m:.3f}',
            'replanning_events': '' if elapsed is None else max(0, self.plan_messages - 1),
            'memory_ids': '', 'semantic_score': '', 'context_score': '',
            'final_score': '', 'strategy': '', 'waypoint_x': '', 'waypoint_y': '',
            'retrieved_strategy': '', 'strategy_applied': '', 'selected_waypoint_x': '', 'selected_waypoint_y': '',
            'waypoint_nav2_result': '', 'final_goal_x': f"{self.value('goal_x'):.3f}", 'final_goal_y': f"{self.value('goal_y'):.3f}", 'final_goal_nav2_result': '',
        }
        path = self.value('results_path')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        exists = os.path.exists(path)
        with open(path, 'a', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=RESULT_FIELDS)
            if not exists:
                writer.writeheader()
            writer.writerow(row)
        self.get_logger().info(f'Baseline result saved: {status}')
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = BaselineRunner()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
