#!/usr/bin/env python3
'''Run declared scenarios with repeatable Memory OFF/ON experiment batches.'''

import argparse
import csv
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
MEMORY_PROJECT = Path(__file__).resolve().parents[2]
ROS_WORKSPACE = MEMORY_PROJECT / 'ros2'
ROS_SETUP = Path('/opt/ros/jazzy/setup.bash')
RESULT_FIELDS = [
    'timestamp_utc', 'experiment_id', 'scenario_id', 'condition', 'run_id',
    'user_id', 'location', 'task', 'goal_label', 'initial_x', 'initial_y',
    'initial_yaw', 'goal_x', 'goal_y', 'nav2_result', 'success', 'time_s',
    'distance_m', 'replanning_events', 'memory_ids', 'semantic_score',
    'context_score', 'final_score', 'strategy', 'waypoint_x', 'waypoint_y',
    'retrieved_strategy', 'strategy_applied', 'selected_waypoint_x', 'selected_waypoint_y',
    'waypoint_nav2_result', 'final_goal_x', 'final_goal_y', 'final_goal_nav2_result',
]


def load_json(path):
    with path.open(encoding='utf-8') as stream:
        return json.load(stream)


def required(data, key):
    value = data.get(key)
    if value in (None, ''):
        raise ValueError(f'Missing required scenario field: {key}')
    return value


def read_last_csv_row(path):
    if not path.exists() or path.stat().st_size == 0:
        return {}
    with path.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    return rows[-1] if rows else {}


def validate_result(row):
    missing = [field for field in RESULT_FIELDS if field not in row]
    if missing:
        raise ValueError(f'Raw result misses required columns: {missing}')
    required_values = (
        'experiment_id', 'scenario_id', 'condition', 'run_id', 'timestamp_utc',
        'nav2_result', 'success', 'time_s', 'distance_m', 'replanning_events',
    )
    for field in required_values:
        if row[field] in (None, ''):
            raise ValueError(f'Raw result has empty required value: {field}')
    memory_fields = ('memory_ids', 'semantic_score', 'context_score', 'final_score', 'strategy')
    if row['condition'] == 'MEMORY_ON':
        for field in memory_fields:
            if row[field] in (None, ''):
                raise ValueError(f'Memory ON result has empty required value: {field}')
    elif row['condition'] == 'MEMORY_OFF':
        populated = [field for field in memory_fields if row[field] not in (None, '')]
        if populated:
            raise ValueError(f'Memory OFF result unexpectedly contains memory fields: {populated}')

def append_csv(path, row, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open('a', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, '') for field in fields})


def terminate_process_group(process):
    if process.poll() is not None:
        return False
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    return True


def launch_arguments(scenario, condition, experiment_id, run_id, raw_path):
    pose, goal = required(scenario, 'initial_pose'), required(scenario, 'goal')
    common = {
        'experiment_id': experiment_id, 'scenario_id': required(scenario, 'scenario_id'),
        'run_id': run_id, 'user_id': required(scenario, 'user_id'),
        'location': required(scenario, 'location'), 'task': required(scenario, 'task'),
        'goal_label': required(goal, 'label'), 'initial_x': pose['x'],
        'initial_y': pose['y'], 'initial_z': pose.get('z', 0.11),
        'initial_yaw': pose['yaw'], 'goal_x': goal['x'], 'goal_y': goal['y'],
        'results_path': str(raw_path),
    }
    if condition == 'memory_on':
        common.update({'query': required(scenario, 'query'), 'goal': goal['label'], 'k': 5})
        offsets = scenario.get('strategy_waypoint_offsets')
        if isinstance(offsets, dict):
            common['strategy_waypoint_offsets'] = ','.join(
                f'{strategy}:{offset[0]}:{offset[1]}'
                for strategy, offset in offsets.items()
            )
        elif offsets:
            raise ValueError('strategy_waypoint_offsets must be an object of strategy: [dx, dy]')
    return [f'{key}:={value}' for key, value in common.items()]


def run_condition(scenario, settings, condition, run_id, output_directory):
    details = settings['conditions'][condition]
    experiment_id, scenario_id = settings['experiment_id'], scenario['scenario_id']
    raw_path = output_directory / f'{scenario_id}__{condition}__{run_id}.csv'
    log_path = output_directory / f'{scenario_id}__{condition}__{run_id}.log'
    if raw_path.exists() or log_path.exists():
        raise FileExistsError(f'Refusing to overwrite existing run artifacts for {condition}/{run_id}')
    args = launch_arguments(scenario, condition, experiment_id, run_id, raw_path)
    command = [
        'bash', '-lc',
        'source ' + shlex.quote(str(ROS_SETUP)) +
        ' && source ' + shlex.quote(str(ROS_WORKSPACE / 'install/setup.bash')) +
        ' && ros2 launch wheelchair_bringup ' + shlex.quote(details['launch']) +
        ' ' + ' '.join(shlex.quote(argument) for argument in args),
    ]
    with log_path.open('w', encoding='utf-8') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True, cwd=ROS_WORKSPACE)
        timed_out = False
        deadline = time.monotonic() + details['timeout_s']
        while process.poll() is None and not raw_path.exists():
            if time.monotonic() >= deadline:
                timed_out = terminate_process_group(process)
                break
            time.sleep(1)
        if raw_path.exists() and process.poll() is None:
            terminate_process_group(process)
    raw = read_last_csv_row(raw_path)
    if raw:
        validate_result(raw)
    status = raw.get('nav2_result', 'NO_RESULT')
    manifest = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'experiment_id': experiment_id, 'scenario_id': scenario_id,
        'condition': condition, 'run_id': run_id, 'user_id': scenario['user_id'],
        'location': scenario['location'], 'task': scenario['task'],
        'initial_x': scenario['initial_pose']['x'], 'initial_y': scenario['initial_pose']['y'],
        'initial_yaw': scenario['initial_pose']['yaw'], 'goal_x': scenario['goal']['x'],
        'goal_y': scenario['goal']['y'], 'goal_label': scenario['goal']['label'],
        'obstacle_configuration': scenario['obstacle_configuration'],
        'expected_preference': scenario['expected_preference'],
        'strategy_waypoint_offsets': json.dumps(scenario.get('strategy_waypoint_offsets', {}), sort_keys=True),
        'memory_enabled': str(details['memory_enabled']).lower(),
        'raw_result_path': str(raw_path), 'log_path': str(log_path),
        'launcher_timed_out': str(timed_out).lower(), 'observed_nav2_status': status,
    }
    return manifest, raw


def normalized_conditions(requested):
    if requested == 'both':
        return ('baseline', 'memory_on')
    return ('baseline' if requested == 'memory_off' else requested,)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', required=True, type=Path)
    parser.add_argument('--condition', choices=('baseline', 'memory_off', 'memory_on', 'both'), default='both')
    parser.add_argument('--number-of-runs', type=int, default=1)
    parser.add_argument('--run-prefix', default='run')
    parser.add_argument('--run-id', help='Legacy explicit ID; valid only with one repetition.')
    parser.add_argument('--config', type=Path, default=MEMORY_PROJECT / 'experiments/configs/navigation_conditions.json')
    args = parser.parse_args()
    if args.number_of_runs < 1:
        parser.error('--number-of-runs must be positive')
    if args.run_id and args.number_of_runs != 1:
        parser.error('--run-id cannot be combined with multiple repetitions')
    scenario, settings = load_json(args.scenario), load_json(args.config)
    required(scenario, 'scenario_id')
    directory_name = settings.get('automated_results_directory', settings['results_directory'])
    output_directory = MEMORY_PROJECT / directory_name
    output_directory.mkdir(parents=True, exist_ok=True)
    manifest_fields = [
        'timestamp_utc', 'experiment_id', 'scenario_id', 'condition', 'run_id',
        'user_id', 'location', 'task', 'initial_x', 'initial_y', 'initial_yaw',
        'goal_x', 'goal_y', 'goal_label', 'obstacle_configuration',
        'expected_preference', 'strategy_waypoint_offsets', 'memory_enabled', 'raw_result_path', 'log_path',
        'launcher_timed_out', 'observed_nav2_status',
    ]
    for index in range(1, args.number_of_runs + 1):
        run_id = args.run_id or f'{args.run_prefix}_{index:03d}'
        for condition in normalized_conditions(args.condition):
            manifest, raw = run_condition(scenario, settings, condition, run_id, output_directory)
            append_csv(output_directory / 'run_manifest.csv', manifest, manifest_fields)
            if raw:
                append_csv(output_directory / 'navigation_results.csv', raw, RESULT_FIELDS)
            print(json.dumps(manifest, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (FileExistsError, KeyError, ValueError) as error:
        print(f'error: {error}', file=sys.stderr)
        raise SystemExit(2)
