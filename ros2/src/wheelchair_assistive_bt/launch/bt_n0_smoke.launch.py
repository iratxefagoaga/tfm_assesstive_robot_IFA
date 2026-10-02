from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription, RegisterEventHandler
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
        ('result_csv', '/tmp/bt_n0_contract_smoke.csv'),
        ('experiment_id', 'bt_phase1_smoke'), ('scenario_id', 'S001_shared_safe_goal'),
        ('run_id', 'n0_001'), ('initial_x', '2.0'), ('initial_y', '-3.0'),
        ('initial_z', '0.11'), ('initial_yaw', '0.0'), ('goal_x', '2.5'),
        ('goal_y', '-3.0'), ('goal_yaw', '0.0'),
        ('wait_for_nav2_timeout_s', '60.0'), ('navigation_timeout_s', '120.0'),
    ]
    declared = [DeclareLaunchArgument(name, default_value=value) for name, value in defaults]
    value = {name: LaunchConfiguration(name) for name, _ in defaults}

    def include(package, filename, args=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(package, 'launch', filename)),
            launch_arguments=(args or {}).items(),
        )

    orchestrator = Node(
        package='wheelchair_assistive_bt',
        executable='assistive_bt_orchestrator',
        name='assistive_bt_orchestrator',
        output='screen',
        parameters=[{
            'experiment_id': value['experiment_id'],
            'scenario_id': value['scenario_id'],
            'condition': 'MEMORY_OFF',
            'result_csv': value['result_csv'],
            'run_id': value['run_id'],
            'goal_x': value['goal_x'], 'goal_y': value['goal_y'],
            'goal_yaw': value['goal_yaw'],
            'wait_for_nav2_timeout_s': value['wait_for_nav2_timeout_s'],
            'navigation_timeout_s': value['navigation_timeout_s'],
        }],
    )

    stack = [
        include(bringup, 'simulation.launch.py', {
            'gui': 'false',
            'initial_x': value['initial_x'], 'initial_y': value['initial_y'],
            'initial_z': value['initial_z'], 'initial_yaw': value['initial_yaw'],
        }),
        include(bringup, 'bridge.launch.py'),
        include(description, 'robot_state_publisher.launch.py'),
        Node(package='wheelchair_bringup', executable='scan_frame_fixer.py', output='screen'),
        include(navigation, 'navigation.launch.py'),
    ]
    nav_ready = Node(package='wheelchair_assistive_bt', executable='wait_for_smoke_ready.py',
                     parameters=[{'mode': 'nav2'}], output='screen')

    def after_ready(actions):
        def callback(event, context):
            if context.is_shutdown:
                return []
            if event.returncode != 0:
                return [EmitEvent(event=Shutdown(reason='Smoke readiness failed'))]
            return actions
        return callback

    handlers = [
        RegisterEventHandler(OnProcessExit(target_action=nav_ready, on_exit=after_ready([orchestrator]))),
        RegisterEventHandler(OnProcessExit(target_action=orchestrator,
            on_exit=[EmitEvent(event=Shutdown(reason='Smoke completed'))])),
    ]
    return LaunchDescription(declared + handlers + stack + [nav_ready])
