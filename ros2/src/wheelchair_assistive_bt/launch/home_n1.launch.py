from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    bringup = get_package_share_directory('wheelchair_bringup')
    description = get_package_share_directory('wheelchair_description')
    navigation = get_package_share_directory('wheelchair_navigation')

    defaults = [
        ('result_csv', '/tmp/home_01_n1.csv'),
        ('experiment_id', 'home_01'), ('scenario_id', 'HOME_01_clearance_preference'),
        ('run_id', 'home_01_n1_001'),
        ('query', 'navegar evitando la mesa'), ('user_id', 'U01'),
        ('location', 'salon'), ('task', 'navegacion'), ('goal_label', 'dormitorio'), ('k', '3'),
        ('initial_x', '2.0'), ('initial_y', '-3.0'), ('initial_z', '0.11'), ('initial_yaw', '0.0'),
        ('goal_x', '6.0'), ('goal_y', '5.5'), ('goal_yaw', '0.0'),
        ('strategy_waypoint_offsets', 'west:-12.0:-3.0'),
        ('memory_timeout_s', '120.0'), ('wait_for_nav2_timeout_s', '120.0'),
        ('navigation_timeout_s', '300.0'), ('gui', 'true'),
    ]
    declared = [DeclareLaunchArgument(name, default_value=value) for name, value in defaults]
    value = {name: LaunchConfiguration(name) for name, _ in defaults}

    def include(package, filename, args=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(package, 'launch', filename)),
            launch_arguments=(args or {}).items(),
        )

    excluded = {'initial_x', 'initial_y', 'initial_z', 'initial_yaw', 'gui'}
    orchestrator = Node(
        package='wheelchair_assistive_bt', executable='memory_observation_bt_orchestrator',
        name='home_n1_orchestrator', output='screen',
        parameters=[{name: value[name] for name, _ in defaults if name not in excluded}],
    )

    stack = [
        include(bringup, 'simulation.launch.py', {
            'environment': 'home', 'gui': value['gui'],
            'initial_x': value['initial_x'], 'initial_y': value['initial_y'],
            'initial_z': value['initial_z'], 'initial_yaw': value['initial_yaw'],
        }),
        include(bringup, 'bridge.launch.py'),
        include(description, 'robot_state_publisher.launch.py'),
        Node(package='wheelchair_bringup', executable='scan_frame_fixer.py', output='screen'),
        include(navigation, 'navigation.launch.py', {'environment': 'home'}),
    ]
    nav_ready = Node(
        package='wheelchair_assistive_bt', executable='wait_for_smoke_ready.py',
        parameters=[{'mode': 'nav2'}], output='screen')

    def after_ready(actions):
        def callback(event, context):
            if context.is_shutdown:
                return []
            if event.returncode != 0:
                return [EmitEvent(event=Shutdown(reason='HOME-01 readiness failed'))]
            return actions
        return callback

    # The core `memory` package lives at the repository root rather than inside the
    # ROS package.  managed_memory_process imports it transitively from MemoryNode,
    # so expose the repository root explicitly instead of relying on the shell cwd.
    ros2_dir = os.path.abspath(os.path.join(bringup, '..', '..', '..', '..', '..'))
    repo_root = os.path.abspath(os.path.join(ros2_dir, '..'))
    existing_pythonpath = os.environ.get('PYTHONPATH', '')
    memory_pythonpath = repo_root + (os.pathsep + existing_pythonpath if existing_pythonpath else '')
    memory_env = {
        'PYTHONPATH': memory_pythonpath,
        'OMP_NUM_THREADS': '1',
        'MKL_NUM_THREADS': '1',
        'TOKENIZERS_PARALLELISM': 'false',
    }

    memory = Node(
        package='wheelchair_assistive_bt', executable='managed_memory_process.py',
        arguments=['memory'], output='screen', additional_env=memory_env)
    memory_ready = Node(
        package='wheelchair_assistive_bt', executable='wait_for_smoke_ready.py',
        parameters=[{'mode': 'memory', 'query': value['query'], 'user_id': value['user_id'],
                     'location': value['location'], 'task': value['task'],
                     'goal': value['goal_label'], 'k': value['k']}], output='screen')
    recommendation = Node(
        package='wheelchair_assistive_bt', executable='managed_memory_process.py',
        arguments=['recommendation'], output='screen', additional_env=memory_env)
    recommendation_ready = Node(
        package='wheelchair_assistive_bt', executable='wait_for_smoke_ready.py',
        parameters=[{'mode': 'recommendation'}], output='screen')

    handlers = [
        RegisterEventHandler(OnProcessExit(
            target_action=memory_ready,
            on_exit=after_ready([recommendation, recommendation_ready]))),
        RegisterEventHandler(OnProcessExit(
            target_action=recommendation_ready,
            on_exit=after_ready(stack + [nav_ready]))),
        RegisterEventHandler(OnProcessExit(
            target_action=nav_ready,
            on_exit=after_ready([orchestrator]))),
        RegisterEventHandler(OnProcessExit(
            target_action=orchestrator,
            on_exit=[EmitEvent(event=Shutdown(reason='HOME-01 N1 completed'))])),
    ]
    return LaunchDescription(declared + handlers + [memory, memory_ready])
