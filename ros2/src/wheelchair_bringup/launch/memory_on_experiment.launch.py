from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    bringup = get_package_share_directory('wheelchair_bringup')
    description = get_package_share_directory('wheelchair_description')
    navigation = get_package_share_directory('wheelchair_navigation')
    names = [
        ('experiment_id', 'phase4'), ('scenario_id', ''), ('run_id', ''),
        ('query', ''), ('user_id', ''), ('location', ''), ('task', ''),
        ('goal_label', ''), ('goal', ''), ('k', '5'),
        ('initial_x', '2.0'), ('initial_y', '-3.0'), ('initial_z', '0.11'),
        ('initial_yaw', '0.0'), ('goal_x', '2.5'), ('goal_y', '-3.0'),
        ('results_path', ''), ('strategy_waypoint_offsets', 'west:-1.0:0.0'),
    ]
    arguments = [DeclareLaunchArgument(name, default_value=value) for name, value in names]
    value = {name: LaunchConfiguration(name) for name, _ in names}

    def include(package, filename, launch_arguments=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(package, 'launch', filename)),
            launch_arguments=(launch_arguments or {}).items(),
        )

    simulation_arguments = {
        'initial_x': value['initial_x'], 'initial_y': value['initial_y'],
        'initial_z': value['initial_z'], 'initial_yaw': value['initial_yaw'],
    }
    adapter_parameters = {
        name: value[name] for name in (
            'experiment_id', 'scenario_id', 'run_id', 'query', 'user_id', 'goal_label',
            'location', 'task', 'goal', 'k', 'initial_x', 'initial_y',
            'initial_yaw', 'goal_x', 'goal_y', 'results_path', 'strategy_waypoint_offsets',
        )
    }
    adapter_parameters['use_strategy_waypoint'] = True
    adapter_parameters['strategy_waypoint_offsets'] = value['strategy_waypoint_offsets']

    return LaunchDescription(arguments + [
        include(bringup, 'simulation.launch.py', simulation_arguments),
        include(bringup, 'bridge.launch.py'),
        include(description, 'robot_state_publisher.launch.py'),
        Node(package='wheelchair_bringup', executable='scan_frame_fixer.py',
             name='scan_frame_fixer', output='screen'),
        TimerAction(period=5.0, actions=[Node(
            package='wheelchair_memory', executable='memory_node', name='memory_node',
            output='screen', additional_env={
                'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
                'TOKENIZERS_PARALLELISM': 'false',
            },
        )]),
        TimerAction(period=180.0, actions=[include(navigation, 'navigation.launch.py')]),
        TimerAction(period=182.0, actions=[Node(
            package='wheelchair_memory', executable='navigation_memory_node',
            name='navigation_memory_node', output='screen',
        )]),
        TimerAction(period=187.0, actions=[Node(
            package='wheelchair_memory', executable='navigation_adapter',
            name='navigation_memory_adapter', output='screen',
            parameters=[adapter_parameters],
        )]),
    ])
