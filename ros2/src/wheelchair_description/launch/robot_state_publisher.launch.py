from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory

import os


def generate_launch_description():

    xacro_file = os.path.join(
        get_package_share_directory("wheelchair_description"),
        "urdf",
        "wheelchair.urdf.xacro",
    )

    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "use_sim_time": True,
                "robot_description": Command([
                    "xacro ",
                    xacro_file,
                ]),
            }
        ],
    )

    return LaunchDescription([
        rsp,
    ])