from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    bringup = get_package_share_directory('wheelchair_bringup')
    description = get_package_share_directory('wheelchair_description')
    navigation = get_package_share_directory('wheelchair_navigation')

    defaults = [
        ('environment', 'home'),
        ('result_csv', '/tmp/home_01_n0.csv'),
        ('experiment_id', 'home_01'), ('scenario_id', 'HOME_01_clearance_preference'),
        ('run_id', 'home_01_n0_001'),
        ('initial_x', '2.0'), ('initial_y', '-6.0'), ('initial_z', '0.11'), ('initial_yaw', '0.0'),
        ('goal_x', '4.0'), ('goal_y', '-4.0'), ('goal_yaw', '0.0'),
        ('wait_for_nav2_timeout_s', '120.0'), ('navigation_timeout_s', '300.0'),
        ('gui', 'true'),
    ]
    declared = [DeclareLaunchArgument(name, default_value=value) for name, value in defaults]
    value = {name: LaunchConfiguration(name) for name, _ in defaults}

    def include(package, filename, args=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(package, 'launch', filename)),
            launch_arguments=(args or {}).items(),
        )

    orchestrator = Node(
        package='wheelchair_assistive_bt', executable='assistive_bt_orchestrator',
        name='home_n0_orchestrator', output='screen',
        parameters=[{
            'experiment_id': value['experiment_id'], 'scenario_id': value['scenario_id'],
            'condition': 'MEMORY_OFF', 'result_csv': value['result_csv'], 'run_id': value['run_id'],
            'goal_x': value['goal_x'], 'goal_y': value['goal_y'], 'goal_yaw': value['goal_yaw'],
            'wait_for_nav2_timeout_s': value['wait_for_nav2_timeout_s'],
            'navigation_timeout_s': value['navigation_timeout_s'],
        }],
    )

    stack = [
        include(bringup, 'simulation.launch.py', {
            'environment': value['environment'], 'gui': value['gui'],
            'initial_x': value['initial_x'], 'initial_y': value['initial_y'],
            'initial_z': value['initial_z'], 'initial_yaw': value['initial_yaw'],
        }),
        include(bringup, 'bridge.launch.py'),
        include(description, 'robot_state_publisher.launch.py'),
        Node(package='wheelchair_bringup', executable='scan_frame_fixer.py', output='screen'),
        include(navigation, 'navigation.launch.py', {
            'environment': value['environment'],
            'initial_x': value['initial_x'], 'initial_y': value['initial_y'],
            'initial_yaw': value['initial_yaw'],
        }),
    ]
    nav_ready = Node(
        package='wheelchair_assistive_bt', executable='wait_for_smoke_ready.py',
        parameters=[{'mode': 'nav2', 'readiness_timeout_s': value['wait_for_nav2_timeout_s']}],
        output='screen')
    delayed_nav_ready = TimerAction(period=10.0, actions=[nav_ready])

    def after_ready(event, context):
        if context.is_shutdown:
            return []
        if event.returncode != 0:
            return [EmitEvent(event=Shutdown(reason='HOME-01 N0 readiness failed'))]
        return [orchestrator]

    handlers = [
        RegisterEventHandler(OnProcessExit(target_action=nav_ready, on_exit=after_ready)),
        RegisterEventHandler(OnProcessExit(
            target_action=orchestrator,
            on_exit=[EmitEvent(event=Shutdown(reason='HOME-01 N0 completed'))])),
    ]
    return LaunchDescription(declared + handlers + stack + [delayed_nav_ready])
