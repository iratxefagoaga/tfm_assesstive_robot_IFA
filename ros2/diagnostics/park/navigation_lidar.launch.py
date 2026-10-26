"""Isolated proposed-lidar profile, retaining the frozen N1 orchestration."""
import ast,importlib.util,os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,ExecuteProcess,RegisterEventHandler,EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown

def generate_launch_description():
    condition=os.environ.get('PARK_LIDAR_CONDITION','memory')
    if condition not in {'direct','memory'}:raise RuntimeError('Unsupported profile condition')
    suffix='n0' if condition=='direct' else 'n1'
    package=Path(get_package_share_directory('wheelchair_assistive_bt'));path=package/f'launch/home_{suffix}.launch.py'
    spec=importlib.util.spec_from_file_location('original_n1_with_proposed_sensor',path);source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source);original_node=source.Node
    original_description_source=source.PythonLaunchDescriptionSource
    def description_source(path):
        if isinstance(path,str) and Path(path).name=='bridge.launch.py':path=str(Path(__file__).with_name('managed_bridge.launch.py'))
        return original_description_source(path)
    source.PythonLaunchDescriptionSource=description_source
    filters=[]
    def node(*args,**kwargs):
        if kwargs.get('package')=='wheelchair_assistive_bt' and kwargs.get('executable')=='managed_memory_process.py' and kwargs.get('arguments')==['memory']:
            environment=kwargs['additional_env'];interpreter=Path(environment['PATH'].split(os.pathsep)[0])/'python'
            return ExecuteProcess(cmd=[str(interpreter),str(Path(__file__).with_name('mission_memory_process.py'))],additional_env=environment,output='screen')
        if kwargs.get('package')=='wheelchair_bringup' and kwargs.get('executable')=='scan_frame_fixer.py':
            process=ExecuteProcess(cmd=['/usr/bin/python3',str(Path(__file__).with_name('navigation_scan_filter.py'))],output='screen');filters.append(process);return process
        return original_node(*args,**kwargs)
    source.Node=node
    syntax=ast.parse((package/f'launch/park_{suffix}.launch.py').read_text());assignment=next(n for n in ast.walk(syntax) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='defaults' for t in n.targets));defaults=ast.literal_eval(assignment.value)
    bridge=ExecuteProcess(cmd=[str(Path(__file__).with_name('park_bridge')),'--bridge-kind=navigation_scan'],output='screen')
    entities=source.generate_launch_description().entities
    def failed(event,context):
        return [] if context.is_shutdown else [EmitEvent(event=Shutdown(reason='Proposed lidar pipeline exited'))]
    handlers=[RegisterEventHandler(OnProcessExit(target_action=process,on_exit=failed)) for process in [bridge,*filters]]
    return LaunchDescription([*[DeclareLaunchArgument(k,default_value=v) for k,v in defaults.items()],*handlers,bridge,*entities])
