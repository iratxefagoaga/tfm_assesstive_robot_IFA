from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


SUPPORTED_ENVIRONMENTS = {"apartment", "home", "park", "airport"}


def _navigation_actions(context, pkg, params_file, required_nodes):
    environment = LaunchConfiguration("environment").perform(context)
    if environment not in SUPPORTED_ENVIRONMENTS:
        raise RuntimeError(
            f"Unsupported environment '{environment}'. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_ENVIRONMENTS))}"
        )

    map_file = os.path.join(pkg, "maps", f"{environment}.yaml")
    if not os.path.isfile(map_file):
        raise RuntimeError(f"Map metadata not found: {map_file}")

    map_server = Node(
        package="nav2_map_server", executable="map_server", name="map_server",
        output="screen", parameters=[params_file, {"yaml_filename": map_file, "use_sim_time": True}],
    )
    initial_pose = {
        "initial_pose": {
            "x": float(LaunchConfiguration("initial_x").perform(context)),
            "y": float(LaunchConfiguration("initial_y").perform(context)),
            "z": 0.0,
            "yaw": float(LaunchConfiguration("initial_yaw").perform(context)),
        }
    }
    amcl = Node(
        package="nav2_amcl", executable="amcl", name="amcl",
        output="screen", parameters=[params_file, initial_pose],
    )
    planner_server = Node(
        package="nav2_planner", executable="planner_server", name="planner_server",
        output="screen", parameters=[params_file],
    )
    controller_server = Node(
        package="nav2_controller", executable="controller_server", name="controller_server",
        output="screen", parameters=[params_file] + (
            [os.path.join(pkg, "config", "airport_costmap.yaml")]
            if environment == "airport" else []
        ), remappings=[("cmd_vel", "/cmd_vel_nav")],
    )
    behavior_server = Node(
        package="nav2_behaviors", executable="behavior_server", name="behavior_server",
        output="screen", parameters=[params_file],
    )
    bt_navigator = Node(
        package="nav2_bt_navigator", executable="bt_navigator", name="bt_navigator",
        output="screen", parameters=[params_file],
    )
    waypoint_follower = Node(
        package="nav2_waypoint_follower", executable="waypoint_follower", name="waypoint_follower",
        output="screen", parameters=[params_file],
    )
    velocity_smoother = Node(
        package="nav2_velocity_smoother", executable="velocity_smoother", name="velocity_smoother",
        output="screen", parameters=[params_file],
        remappings=[("cmd_vel", "/cmd_vel_nav"), ("cmd_vel_smoothed", "/cmd_vel")],
    )
    lifecycle_manager = Node(
        package="nav2_lifecycle_manager", executable="lifecycle_manager",
        name="lifecycle_manager_navigation", output="screen",
        parameters=[{"use_sim_time": True, "autostart": True, "node_names": required_nodes}],
    )

    return [
        map_server, amcl, planner_server, controller_server, behavior_server,
        bt_navigator, waypoint_follower, velocity_smoother, lifecycle_manager,
    ]


def generate_launch_description():
    pkg = get_package_share_directory("wheelchair_navigation")

    with open(os.path.join(pkg, "config", "required_nav2_nodes.txt")) as source:
        required_nodes = [line.strip() for line in source if line.strip()]
    if not required_nodes or len(required_nodes) != len(set(required_nodes)):
        raise RuntimeError("Invalid canonical Nav2 lifecycle node list")

    params_file = os.path.join(pkg, "config", "nav2_params.yaml")

    return LaunchDescription([
        DeclareLaunchArgument(
            "environment",
            default_value="apartment",
            description="Navigation map: apartment, home, park, or airport",
        ),
        DeclareLaunchArgument("initial_x", default_value="2.0"),
        DeclareLaunchArgument("initial_y", default_value="-3.0"),
        DeclareLaunchArgument("initial_yaw", default_value="0.0"),
        OpaqueFunction(
            function=_navigation_actions,
            args=[pkg, params_file, required_nodes],
        ),
    ])
