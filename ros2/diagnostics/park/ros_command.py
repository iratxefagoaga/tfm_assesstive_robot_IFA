"""Run a local diagnostic command with the selected installed ROS overlay."""
import argparse,subprocess
from pathlib import Path
from diagnose import ros_environment
p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
if not a.command:raise SystemExit('Missing diagnostic command')
raise SystemExit(subprocess.run(a.command,env=ros_environment(a.code_root),cwd=a.code_root).returncode)
