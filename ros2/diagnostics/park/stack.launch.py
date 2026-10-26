"""PARK waypoint control: same installed stack, explicit goals, no memory."""
from pathlib import Path
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler, EmitEvent, TimerAction, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    def include(package, filename, args=None):
        p=Path(get_package_share_directory(package))/'launch'/filename
        return IncludeLaunchDescription(PythonLaunchDescriptionSource(str(p)),launch_arguments=(args or {}).items())
    sender=Node(package='wheelchair_assistive_bt',executable='wait_for_smoke_ready.py',
                parameters=[{'mode':'nav2','readiness_timeout_s':120.0}],output='screen')
    controller=ExecuteProcess(cmd=['/usr/bin/python3',str(Path(__file__).with_name('sequence.py')),
                                  '--output',os.environ['PARK_DIAGNOSTIC_OUTPUT']],output='screen')
    def ready(event,context):
        if context.is_shutdown:return []
        if event.returncode:return [EmitEvent(event=Shutdown(reason='Diagnostic readiness failed'))]
        return [controller]
    return LaunchDescription([
        RegisterEventHandler(OnProcessExit(target_action=sender,on_exit=ready)),
        RegisterEventHandler(OnProcessExit(target_action=controller,on_exit=[EmitEvent(event=Shutdown(reason='Diagnostic sequence complete'))])),
        include('wheelchair_bringup','simulation.launch.py',{'environment':'park','gui':'false','initial_x':'0.0','initial_y':'-9.0','initial_z':'0.11','initial_yaw':'0.0'}),
        include('wheelchair_bringup','bridge.launch.py'),
        include('wheelchair_description','robot_state_publisher.launch.py'),
        Node(package='wheelchair_bringup',executable='scan_frame_fixer.py',output='screen'),
        include('wheelchair_navigation','navigation.launch.py',{'environment':'park','initial_x':'0.0','initial_y':'-9.0','initial_yaw':'0.0'}),
        TimerAction(period=10.0,actions=[sender]),
    ])
