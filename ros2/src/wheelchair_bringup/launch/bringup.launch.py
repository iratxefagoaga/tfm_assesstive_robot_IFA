from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg = get_package_share_directory("wheelchair_bringup")
    pkg_description = get_package_share_directory("wheelchair_description")
    pkg_navigation = get_package_share_directory("wheelchair_navigation")

    environment = LaunchConfiguration("environment")

    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, "launch", "simulation.launch.py")),
        launch_arguments={"environment": environment}.items(),
    )

    bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, "launch", "bridge.launch.py"))
    )

    robot_state_publisher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_description, "launch", "robot_state_publisher.launch.py")
        )
    )

    rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, "launch", "rviz.launch.py"))
    )

    scan_frame_fixer = Node(
        package="wheelchair_bringup",
        executable="scan_frame_fixer.py",
        name="scan_frame_fixer",
        output="screen",
    )

    memory_node = Node(
        package="wheelchair_memory",
        executable="memory_node",
        name="memory_node",
        output="screen",
    )

    navigation_memory = TimerAction(
        period=3.0,
        actions=[
            Node(
                package="wheelchair_memory",
                executable="navigation_memory_node",
                name="navigation_memory_node",
                output="screen",
            )
        ],
    )

    navigation = TimerAction(
        period=5.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_navigation, "launch", "navigation.launch.py")
                ),
                launch_arguments={"environment": environment}.items(),
            )
        ],
    )

    navigation_adapter = TimerAction(
        period=10.0,
        actions=[
            Node(
                package="wheelchair_memory",
                executable="navigation_adapter",
                name="navigation_memory_adapter",
                output="screen",
            )
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "environment",
            default_value="apartment",
            description="Integrated environment: apartment or home",
        ),
        simulation,
        bridge,
        robot_state_publisher,
        scan_frame_fixer,
        rviz,
        memory_node,
        navigation_memory,
        navigation,
        navigation_adapter,
    ])
