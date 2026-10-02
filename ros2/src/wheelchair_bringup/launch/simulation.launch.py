from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction, SetEnvironmentVariable, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory

import os


SUPPORTED_ENVIRONMENTS = {"apartment", "home"}


def _simulation_actions(context, gazebo_pkg, wheelchair_model):
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

    actions = [gazebo_server, gazebo_gui]

    # Home is loaded from its SDF file instead of model://home.  On Linux,
    # Gazebo / sdformat can interpret the authority "home" as the POSIX /home
    # path before consulting the model resource path.  Explicit spawning also
    # keeps the environment model independent of Fuel / URI resolution.
    if environment == "home":
        home_model = os.path.join(gazebo_pkg, "models", "home", "model.sdf")
        if not os.path.isfile(home_model):
            raise RuntimeError(f"Home model not found: {home_model}")
        actions.append(
            TimerAction(
                period=1.0,
                actions=[Node(
                    package="ros_gz_sim",
                    executable="create",
                    name="spawn_home",
                    output="screen",
                    arguments=["-name", "home", "-file", home_model],
                )],
            )
        )

    # Spawn the wheelchair after the static environment has been inserted.
    actions.append(
        TimerAction(
            period=2.0,
            actions=[Node(
                package="ros_gz_sim",
                executable="create",
                name="spawn_wheelchair",
                output="screen",
                arguments=[
                    "-name", "wheelchair", "-file", wheelchair_model,
                    "-x", initial_x, "-y", initial_y, "-z", initial_z,
                    "-Y", initial_yaw,
                ],
            )],
        )
    )
    return actions


def generate_launch_description():
    gazebo_pkg = get_package_share_directory("wheelchair_gazebo")
    wheelchair_model = os.path.join(gazebo_pkg, "models", "wheelchair", "model.sdf")

    # Keep the normal model search path for any nested resources used by models.
    models_dir = os.path.join(gazebo_pkg, "models")
    existing_resource_path = os.environ.get("GZ_SIM_RESOURCE_PATH", "")
    resource_roots = [models_dir]
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
        OpaqueFunction(function=_simulation_actions, args=[gazebo_pkg, wheelchair_model]),
    ])
