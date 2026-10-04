from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
import os


def generate_launch_description():
    path = os.path.join(get_package_share_directory("wheelchair_assistive_bt"), "launch", "home_n0.launch.py")
    return LaunchDescription([IncludeLaunchDescription(
        PythonLaunchDescriptionSource(path), launch_arguments={
            "environment": "airport", "experiment_id": "airport01",
            "scenario_id": "AIRPORT_01_east_detour", "run_id": "airport_n0_001",
            "result_csv": "/tmp/airport01_n0.csv", "initial_x": "0.0", "initial_y": "-8.0",
            "initial_yaw": "0.0", "goal_x": "0.0", "goal_y": "8.0", "goal_yaw": "0.0",
        }.items())])
