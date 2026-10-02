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
    include = lambda package, file: IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(package, 'launch', file)))
    return LaunchDescription([
        include(bringup, 'simulation.launch.py'),
        include(bringup, 'bridge.launch.py'),
        include(description, 'robot_state_publisher.launch.py'),
        Node(package='wheelchair_bringup', executable='scan_frame_fixer.py', name='scan_frame_fixer', output='screen'),
        TimerAction(period=5.0, actions=[include(navigation, 'navigation.launch.py')]),
        TimerAction(period=12.0, actions=[Node(package='wheelchair_bringup', executable='baseline_runner.py', name='baseline_runner', output='screen')]),
    ])