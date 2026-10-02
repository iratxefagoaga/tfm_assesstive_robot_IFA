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
        ('experiment_id', 'bt_phase2_smoke'), ('scenario_id', 'S001_shared_safe_goal'),
        ('run_id', 'n1_001'), ('query', 'navegar evitando la mesa'),
        ('user_id', 'U01'), ('location', 'salon'), ('task', 'navegacion'),
        ('goal_label', 'dormitorio'), ('k', '3'), ('initial_x', '2.0'),
        ('initial_y', '-3.0'), ('initial_z', '0.11'), ('initial_yaw', '0.0'),
        ('goal_x', '2.5'), ('goal_y', '-3.0'), ('goal_yaw', '0.0'),
        ('memory_timeout_s', '90.0'), ('wait_for_nav2_timeout_s', '60.0'),
        ('navigation_timeout_s', '120.0'),
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
        executable='memory_observation_bt_orchestrator',
        name='memory_observation_bt_orchestrator',
        output='screen',
        parameters=[{name: value[name] for name, _ in defaults if name not in ('initial_x', 'initial_y', 'initial_z', 'initial_yaw')}],
    )

    return LaunchDescription(declared + [
        include(bringup, 'simulation.launch.py', {
            'initial_x': value['initial_x'], 'initial_y': value['initial_y'],
            'initial_z': value['initial_z'], 'initial_yaw': value['initial_yaw'],
        }),
        include(bringup, 'bridge.launch.py'),
        include(description, 'robot_state_publisher.launch.py'),
        Node(package='wheelchair_bringup', executable='scan_frame_fixer.py',
             name='scan_frame_fixer', output='screen'),
        TimerAction(period=1.0, actions=[Node(
            package='wheelchair_memory', executable='memory_node', name='memory_node', output='screen',
            additional_env={'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'TOKENIZERS_PARALLELISM': 'false'},
        )]),
        TimerAction(period=175.0, actions=[Node(
            package='wheelchair_memory', executable='navigation_memory_node',
            name='navigation_memory_node', output='screen',
        )]),
        TimerAction(period=180.0, actions=[include(navigation, 'navigation.launch.py')]),
        TimerAction(period=185.0, actions=[orchestrator]),
        RegisterEventHandler(OnProcessExit(
            target_action=orchestrator,
            on_exit=[EmitEvent(event=Shutdown(reason='Assistive BT N1 phase 2 completed'))],
        )),
    ])