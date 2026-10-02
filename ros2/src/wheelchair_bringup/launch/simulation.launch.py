from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory

import os


def generate_launch_description():
    initial_x = LaunchConfiguration('initial_x')
    initial_y = LaunchConfiguration('initial_y')
    initial_z = LaunchConfiguration('initial_z')
    initial_yaw = LaunchConfiguration('initial_yaw')

    gazebo_pkg = get_package_share_directory('wheelchair_gazebo')
    world = os.path.join(gazebo_pkg, 'worlds', 'apartment.world')
    model = os.path.join(gazebo_pkg, 'models', 'wheelchair', 'model.sdf')

    resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH', value=os.path.join(gazebo_pkg, 'models')
    )
    # Separate foreground processes: no shell and no untracked forked sessions.
    gazebo_server = ExecuteProcess(
        cmd=['gz', 'sim', '-s', '-r', world], name='gazebo_server', output='screen')
    gazebo_gui = ExecuteProcess(
        cmd=['gz', 'sim', '-g', world], name='gazebo_gui', output='screen',
        condition=IfCondition(LaunchConfiguration('gui')))
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-name', 'wheelchair', '-file', model,
            '-x', initial_x, '-y', initial_y, '-z', initial_z,
            '-Y', initial_yaw,
        ],
    )
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('initial_x', default_value='2.0'),
        DeclareLaunchArgument('initial_y', default_value='-3.0'),
        DeclareLaunchArgument('initial_z', default_value='0.11'),
        DeclareLaunchArgument('initial_yaw', default_value='0.0'),
        resource_path, gazebo_server, gazebo_gui, spawn,
    ])
