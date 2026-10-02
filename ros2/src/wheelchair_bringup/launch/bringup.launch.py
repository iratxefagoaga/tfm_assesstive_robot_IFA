from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():

    pkg = get_package_share_directory("wheelchair_bringup")
    pkg_description = get_package_share_directory("wheelchair_description")
    pkg_navigation = get_package_share_directory("wheelchair_navigation")

    # ============================================================
    # SIMULACIÓN
    # ============================================================

    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg,
                "launch",
                "simulation.launch.py"
            )
        )
    )

    # ============================================================
    # BRIDGE
    # ============================================================

    bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg,
                "launch",
                "bridge.launch.py"
            )
        )
    )

    # ============================================================
    # ROBOT STATE PUBLISHER
    # ============================================================

    robot_state_publisher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg_description,
                "launch",
                "robot_state_publisher.launch.py"
            )
        )
    )

    # ============================================================
    # RVIZ
    # ============================================================

    rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg,
                "launch",
                "rviz.launch.py"
            )
        )
    )

    # ============================================================
    # LASER SCAN FRAME FIXER
    # ============================================================

    scan_frame_fixer = Node(
        package="wheelchair_bringup",
        executable="scan_frame_fixer.py",
        name="scan_frame_fixer",
        output="screen",
    )

    # ============================================================
    # MEMORY NODE
    # ============================================================

    memory_node = Node(
        package="wheelchair_memory",
        executable="memory_node",
        name="memory_node",
        output="screen",
    )

    # ============================================================
    # NAVIGATION MEMORY NODE
    # ============================================================

    navigation_memory = TimerAction(
        period=3.0,
        actions=[
            Node(
                package="wheelchair_memory",
                executable="navigation_memory_node",
                name="navigation_memory_node",
                output="screen",
            )
        ]
    )

    # ============================================================
    # NAV2
    # ============================================================

    navigation = TimerAction(
        period=5.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(
                        pkg_navigation,
                        "launch",
                        "navigation.launch.py"
                    )
                )
            )
        ]
    )

    # ============================================================
    # NAVIGATION MEMORY ADAPTER
    #
    # Conecta:
    #
    # Memory -> NavigationMemoryAdapter -> Nav2
    #
    # El adapter espera internamente a que:
    #   /memory/query
    #   /navigate_to_pose
    #
    # estén disponibles.
    # ============================================================

    navigation_adapter = TimerAction(
        period=10.0,
        actions=[
            Node(
                package="wheelchair_memory",
                executable="navigation_adapter",
                name="navigation_memory_adapter",
                output="screen",
            )
        ]
    )

    # ============================================================
    # LAUNCH DESCRIPTION
    # ============================================================

    return LaunchDescription([

        # --------------------------------------------------------
        # Simulación
        # --------------------------------------------------------

        simulation,

        # --------------------------------------------------------
        # ROS <-> Gazebo
        # --------------------------------------------------------

        bridge,

        # --------------------------------------------------------
        # TF del robot
        # --------------------------------------------------------

        robot_state_publisher,

        # --------------------------------------------------------
        # Corrección del frame del LiDAR
        # --------------------------------------------------------

        scan_frame_fixer,

        # --------------------------------------------------------
        # Visualización
        # --------------------------------------------------------

        rviz,

        # --------------------------------------------------------
        # Memoria
        # --------------------------------------------------------

        memory_node,
        navigation_memory,

        # --------------------------------------------------------
        # Nav2
        # --------------------------------------------------------

        navigation,

        # --------------------------------------------------------
        # Memoria -> Nav2
        # --------------------------------------------------------

        navigation_adapter,
    ])