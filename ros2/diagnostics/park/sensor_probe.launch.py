"""Minimal static sensor test, without Nav2, memory or velocity commands."""
import importlib.util,os
from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction,SetEnvironmentVariable,IncludeLaunchDescription,ExecuteProcess,RegisterEventHandler,EmitEvent
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node

def generate_launch_description():
    bringup=Path(get_package_share_directory('wheelchair_bringup'))
    gazebo=Path(get_package_share_directory('wheelchair_gazebo'))
    spec=importlib.util.spec_from_file_location('installed_simulation_launch',bringup/'launch/simulation.launch.py')
    source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
    topic=os.environ.get('PARK_SENSOR_TOPIC','/scan')
    observer=ExecuteProcess(cmd=['/usr/bin/python3',str(Path(__file__).with_name('sensor_observer.py')),
                                '--output',os.environ['PARK_SENSOR_OUTPUT'],'--topic',topic],output='screen')
    model=os.environ['PARK_SENSOR_MODEL']
    # Reuse installed simulator/spawn actions byte-for-byte; only model path varies.
    return LaunchDescription([
        *[DeclareLaunchArgument(k,default_value=v) for k,v in [('environment','park'),('gui','false'),('initial_x','0.0'),('initial_y','-9.0'),('initial_z','0.11'),('initial_yaw','0.0')]],
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH',str(gazebo/'models')),
        RegisterEventHandler(OnProcessExit(target_action=observer,on_exit=[EmitEvent(event=Shutdown(reason='Static sensor probe complete'))])),
        OpaqueFunction(function=source._simulation_actions,args=[str(gazebo),model]),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(bringup/'launch/bridge.launch.py'))),
        observer,
        *([Node(package='ros_gz_bridge',executable='parameter_bridge',arguments=[topic+'@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'],output='screen')] if topic!='/scan' else []),
    ])
