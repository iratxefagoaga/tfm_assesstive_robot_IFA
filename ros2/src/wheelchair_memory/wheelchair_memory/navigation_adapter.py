from pathlib import Path

TFM_ROOT = Path(__file__).resolve().parents[4]
#!/usr/bin/env python3
'''Traceable Memory-ON bridge with the common experimental result schema.'''

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

from wheelchair_interfaces.srv import MemoryQuery, NavigationRecommendation


RESULT_FIELDS = [
    'timestamp_utc', 'experiment_id', 'scenario_id', 'condition', 'run_id',
    'user_id', 'location', 'task', 'goal_label', 'initial_x', 'initial_y',
    'initial_yaw', 'goal_x', 'goal_y', 'nav2_result', 'success', 'time_s',
    'distance_m', 'replanning_events', 'memory_ids', 'semantic_score',
    'context_score', 'final_score', 'strategy', 'waypoint_x', 'waypoint_y',
    'retrieved_strategy', 'strategy_applied', 'selected_waypoint_x', 'selected_waypoint_y',
    'waypoint_nav2_result', 'final_goal_x', 'final_goal_y', 'final_goal_nav2_result',
]


class NavigationMemoryAdapter(Node):
    '''Runs one Memory-ON navigation and persists retrieval plus measured navigation data.'''

    def __init__(self):
        super().__init__('navigation_memory_adapter')
        defaults = {
            'query': 'U01 quiere ir del salon al dormitorio y necesita una ruta con espacio lateral.',
            'user_id': 'U01', 'location': 'salon', 'task': 'navegacion',
            'goal': 'dormitorio', 'goal_label': 'dormitorio', 'k': 5,
            'experiment_id': '', 'scenario_id': '', 'run_id': '',
            'initial_x': 2.0, 'initial_y': -3.0, 'initial_yaw': 0.0,
            'goal_x': 2.5, 'goal_y': -3.0, 'use_strategy_waypoint': True,
            'strategy_waypoint_offsets': 'west:-1.0:0.0',
            'results_path': str(TFM_ROOT / 'experiments/results/memory_on_navigation_results.csv'),
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self.memory_client = self.create_client(MemoryQuery, '/memory/query')
        self.recommendation_client = self.create_client(
            NavigationRecommendation, '/memory/navigation_recommendation'
        )
        self.nav_client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        self.nav_state_client = self.create_client(GetState, '/bt_navigator/get_state')
        self.create_subscription(Odometry, '/odom', self.on_odom, 20)
        self.create_subscription(Path, '/plan', self.on_plan, 10)
        self.pending_goal = None
        self.navigation_stage = None
        self.dispatch_timer = None
        self.state_request_pending = False
        self.started = False
        self.nav_started_at = None
        self.previous_xy = None
        self.distance_m = 0.0
        self.plan_messages = 0
        self.record = self.initial_record()
        self.create_timer(1.0, self.start_once)

    def value(self, name):
        return self.get_parameter(name).value

    def initial_record(self):
        return {
            'timestamp_utc': '', 'experiment_id': self.value('experiment_id'),
            'scenario_id': self.value('scenario_id'), 'condition': 'MEMORY_ON',
            'run_id': self.value('run_id'), 'user_id': self.value('user_id'),
            'location': self.value('location'), 'task': self.value('task'),
            'goal_label': self.value('goal_label'), 'initial_x': self.value('initial_x'),
            'initial_y': self.value('initial_y'), 'initial_yaw': self.value('initial_yaw'),
            'goal_x': self.value('goal_x'), 'goal_y': self.value('goal_y'),
            'nav2_result': '', 'success': '', 'time_s': '', 'distance_m': '',
            'replanning_events': '', 'memory_ids': '', 'semantic_score': '',
            'context_score': '', 'final_score': '', 'strategy': '',
            'waypoint_x': '', 'waypoint_y': '',
            'retrieved_strategy': '', 'strategy_applied': 'false', 'selected_waypoint_x': '', 'selected_waypoint_y': '',
            'waypoint_nav2_result': 'NOT_APPLIED', 'final_goal_x': f"{self.value('goal_x'):.3f}",
            'final_goal_y': f"{self.value('goal_y'):.3f}", 'final_goal_nav2_result': 'NOT_SENT',
        }

    def on_odom(self, msg):
        if self.nav_started_at is None:
            return
        point = (msg.pose.pose.position.x, msg.pose.pose.position.y)
        if self.previous_xy is not None:
            self.distance_m += math.dist(self.previous_xy, point)
        self.previous_xy = point

    def on_plan(self, _msg):
        if self.nav_started_at is not None:
            self.plan_messages += 1

    def start_once(self):
        if self.started:
            return
        if not self.memory_client.wait_for_service(timeout_sec=0.1):
            return
        if not self.recommendation_client.wait_for_service(timeout_sec=0.1):
            return
        if not self.nav_client.wait_for_server(timeout_sec=0.1):
            return
        self.started = True
        request = MemoryQuery.Request()
        request.query = self.value('query')
        request.user_id = self.value('user_id')
        request.location = self.value('location')
        request.task = self.value('task')
        request.goal = self.value('goal')
        request.k = self.value('k')
        self.get_logger().info('Memory ON: query -> /memory/query')
        self.memory_client.call_async(request).add_done_callback(self.on_query)

    def on_query(self, future):
        try:
            response = future.result()
        except Exception as error:
            self.finish(f'MEMORY_QUERY_ERROR: {error}')
            return
        if not response.success or not response.memory_ids:
            self.finish(f'MEMORY_QUERY_FAILED: {response.message}')
            return
        self.record['memory_ids'] = '|'.join(response.memory_ids)
        self.get_logger().info(f"Memory ON: retrieved {self.record['memory_ids']}")
        request = NavigationRecommendation.Request()
        request.query = self.value('query')
        request.user_id = self.value('user_id')
        request.location = self.value('location')
        request.task = self.value('task')
        request.goal = self.value('goal')
        request.k = self.value('k')
        self.get_logger().info('Memory ON: retrieval -> recommendation')
        self.recommendation_client.call_async(request).add_done_callback(self.on_recommendation)

    def on_recommendation(self, future):
        try: response = future.result()
        except Exception as error:
            self.finish(f'RECOMMENDATION_ERROR: {error}'); return
        if not response.success:
            self.finish(f'RECOMMENDATION_FAILED: {response.message}'); return
        self.record['strategy'] = response.strategy
        self.record['retrieved_strategy'] = response.strategy
        self.record['semantic_score'] = f'{response.semantic_score:.10f}'
        self.record['context_score'] = f'{response.context_score:.10f}'
        self.record['final_score'] = f'{response.final_score:.10f}'
        waypoint = self.select_strategy_waypoint(response.strategy)
        self.record['strategy_applied'] = str(waypoint is not None).lower()
        if waypoint is None:
            self.prepare_final_goal()
        else:
            self.record['waypoint_x'] = self.record['selected_waypoint_x'] = f'{waypoint[0]:.3f}'
            self.record['waypoint_y'] = self.record['selected_waypoint_y'] = f'{waypoint[1]:.3f}'
            self.navigation_stage = 'waypoint'
            self.pending_goal = self.make_goal(*waypoint)
        self.get_logger().info(f'Memory ON: strategy={response.strategy}, applied={self.record["strategy_applied"]}, stage={self.navigation_stage}')
        self.dispatch_timer = self.create_timer(1.0, self.dispatch_when_nav2_active)

    def make_goal(self, x, y):
        goal = NavigateToPose.Goal(); goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'; goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = x; goal.pose.pose.position.y = y; goal.pose.pose.orientation.w = 1.0
        return goal

    def select_strategy_waypoint(self, strategy):
        if not self.value('use_strategy_waypoint') or strategy == 'direct': return None
        for entry in self.value('strategy_waypoint_offsets').split(','):
            try:
                name, dx, dy = entry.split(':')
                if name == strategy:
                    dx, dy = float(dx), float(dy)
                    return None if (dx == 0.0 and dy == 0.0) else (self.value('goal_x') + dx, self.value('goal_y') + dy)
            except ValueError: self.get_logger().warn(f'Ignoring invalid strategy waypoint entry: {entry}')
        return None

    def prepare_final_goal(self):
        self.navigation_stage = 'final_goal'
        self.pending_goal = self.make_goal(self.value('goal_x'), self.value('goal_y'))

    def dispatch_when_nav2_active(self):
        if self.state_request_pending:
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
        self.destroy_timer(self.dispatch_timer)
        self.dispatch_timer = None
        if self.nav_started_at is None:
            self.previous_xy = None
            self.distance_m = 0.0
            self.plan_messages = 0
            self.nav_started_at = time.monotonic()
        self.nav_client.send_goal_async(self.pending_goal).add_done_callback(self.on_goal_response)

    def on_goal_response(self, future):
        try:
            handle = future.result()
        except Exception as error:
            self.finish(f'NAV2_GOAL_ERROR: {error}')
            return
        if not handle.accepted:
            self.finish('NAV2_REJECTED')
            return
        self.get_logger().info(f'Memory ON: Nav2 {self.navigation_stage} goal accepted.')
        handle.get_result_async().add_done_callback(self.on_nav_result)

    def on_nav_result(self, future):
        try:
            status = future.result().status
        except Exception as error:
            self.finish(f'NAV2_RESULT_ERROR: {error}')
            return
        labels = {
            GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED',
            GoalStatus.STATUS_ABORTED: 'ABORTED',
            GoalStatus.STATUS_CANCELED: 'CANCELED',
        }
        result = labels.get(status, f'STATUS_{status}')
        if self.navigation_stage == 'waypoint':
            self.record['waypoint_nav2_result'] = result
            if result != 'SUCCEEDED':
                self.record['final_goal_nav2_result'] = 'NOT_SENT'
                self.finish(f'WAYPOINT_{result}')
                return
            self.prepare_final_goal()
            self.dispatch_timer = self.create_timer(1.0, self.dispatch_when_nav2_active)
            return
        self.record['final_goal_nav2_result'] = result
        self.finish(result)

    def finish(self, nav2_result):
        if self.record['nav2_result']:
            return
        self.record['timestamp_utc'] = datetime.now(timezone.utc).isoformat()
        self.record['nav2_result'] = nav2_result
        self.record['success'] = str(nav2_result == 'SUCCEEDED').lower()
        if self.nav_started_at is not None:
            self.record['time_s'] = f'{time.monotonic() - self.nav_started_at:.3f}'
            self.record['distance_m'] = f'{self.distance_m:.3f}'
            self.record['replanning_events'] = max(0, self.plan_messages - 1)
        path = self.value('results_path')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        exists = os.path.exists(path)
        with open(path, 'a', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=RESULT_FIELDS)
            if not exists:
                writer.writeheader()
            writer.writerow(self.record)
        self.get_logger().info(f"Memory ON result saved: {nav2_result}; ids={self.record['memory_ids']}")
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = NavigationMemoryAdapter()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
