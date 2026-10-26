"""Core bridge with context-preserving shutdown; navigation bridge is separate."""
from pathlib import Path
from launch import LaunchDescription
from launch.actions import ExecuteProcess
def generate_launch_description():
    return LaunchDescription([ExecuteProcess(cmd=[str(Path(__file__).with_name('park_bridge')),'--bridge-kind=core'],output='screen')])
