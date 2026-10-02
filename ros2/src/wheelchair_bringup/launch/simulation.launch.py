from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory

import os


SUPPORTED_ENVIRONMENTS = {"apartment", "home"}


def _simulation_actions(context, gazebo_pkg, model):
    environment = LaunchConfiguration("environment").perform(context)
    if environment not in SUPPORTED_ENVIRONMENTS:
        raise RuntimeError(
            f"Unsupported environment '{environment}'. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_ENVIRONMENTS))}"
        )

    world = os.path.join(gazebo_pkg, "worlds", f"{environment}.world")
    if not os.path.isfile(world):
        raise RuntimeError(f"Gazebo world not found: {world}")

    initial_x = LaunchConfiguration("initial_x")
    initial_y = LaunchConfiguration("initial_y")
    initial_z = LaunchConfiguration("initial_z")
    initial_yaw = LaunchConfiguration("initial_yaw")

    gazebo_server = ExecuteProcess(
        cmd=["gz", "sim", "-s", "-r", world],
        name="gazebo_server",
        output="screen",
    )
    gazebo_gui = ExecuteProcess(
        cmd=["gz", "sim", "-g", world],
        name="gazebo_gui",
        output="screen",
        condition=IfCondition(LaunchConfiguration("gui")),
    )
    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-name", "wheelchair", "-file", model,
            "-x", initial_x, "-y", initial_y, "-z", initial_z,
            "-Y", initial_yaw,
        ],
    )
    return [gazebo_server, gazebo_gui, spawn]


def generate_launch_description():
    gazebo_pkg = get_package_share_directory("wheelchair_gazebo")
    model = os.path.join(gazebo_pkg, "models", "wheelchair", "model.sdf")

    # Gazebo resolves model://<name> by looking for <resource-root>/<name>/model.config.
    # Therefore the resource root must be the parent of the package's models directory,
    # not the models directory itself.  With the ament install layout this is the
    # wheelchair_gazebo package share directory, where models/home/model.config lives.
    existing_resource_path = os.environ.get("GZ_SIM_RESOURCE_PATH", "")
    resource_roots = [gazebo_pkg]
    if existing_resource_path:
        resource_roots.append(existing_resource_path)
    resource_path = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=os.pathsep.join(resource_roots),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "environment",
            default_value="apartment",
            description="Simulation environment: apartment or home",
        ),
        DeclareLaunchArgument("gui", default_value="true"),
        DeclareLaunchArgument("initial_x", default_value="2.0"),
        DeclareLaunchArgument("initial_y", default_value="-3.0"),
        DeclareLaunchArgument("initial_z", default_value="0.11"),
        DeclareLaunchArgument("initial_yaw", default_value="0.0"),
        resource_path,
        OpaqueFunction(function=_simulation_actions, args=[gazebo_pkg, model]),
    ])
