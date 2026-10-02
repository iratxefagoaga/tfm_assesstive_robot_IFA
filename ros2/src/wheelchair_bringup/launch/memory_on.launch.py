from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    bringup = get_package_share_directory('wheelchair_bringup')
    description = get_package_share_directory('wheelchair_description')
    navigation = get_package_share_directory('wheelchair_navigation')

    def include(package, filename):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(package, 'launch', filename))
        )

    return LaunchDescription([
        include(bringup, 'simulation.launch.py'),
        include(bringup, 'bridge.launch.py'),
        include(description, 'robot_state_publisher.launch.py'),
        Node(package='wheelchair_bringup', executable='scan_frame_fixer.py',
             name='scan_frame_fixer', output='screen'),
        # Load the embedding model before activating Nav2.  On this host model
        # warm-up is CPU intensive and must finish before Nav2 activates.
        TimerAction(period=5.0, actions=[Node(
            package='wheelchair_memory', executable='memory_node',
            name='memory_node', output='screen',
            additional_env={'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'TOKENIZERS_PARALLELISM': 'false'})]),
        # Start the unchanged Nav2 launch only after the model warm-up window.
        TimerAction(period=180.0, actions=[include(navigation, 'navigation.launch.py')]),
        TimerAction(period=182.0, actions=[Node(
            package='wheelchair_memory', executable='navigation_memory_node',
            name='navigation_memory_node', output='screen')]),
        TimerAction(period=187.0, actions=[Node(
            package='wheelchair_memory', executable='navigation_adapter',
            name='navigation_memory_adapter', output='screen',
            # Same collision-free endpoint validated in Phase 2.  This proves the
            # Memory-ON wiring; it is not evidence of a geometric west-route effect.
            parameters=[{'west_waypoint_x': 2.5, 'west_waypoint_y': -3.0}])]),
    ])