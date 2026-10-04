from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
import os


def generate_launch_description():
    defaults = {
        'environment': 'park',
        'experiment_id': 'park01',
        'scenario_id': 'PARK_01_west_path_preference',
        'run_id': 'park_n0_001',
        'result_csv': '/tmp/park01_n0.csv',
        'initial_x': '0.0',
        'initial_y': '-9.0',
        'initial_yaw': '0.0',
        'goal_x': '1.0',
        'goal_y': '-9.0',
        'goal_yaw': '0.0',
    }
    path = os.path.join(get_package_share_directory("wheelchair_assistive_bt"),
                        "launch", "home_n0.launch.py")
    declared = [DeclareLaunchArgument(name, default_value=value)
                for name, value in defaults.items()]
    return LaunchDescription(declared + [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(path),
        launch_arguments={name: LaunchConfiguration(name) for name in defaults}.items(),
    )])
