#!/usr/bin/env bash
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
source /opt/ros/jazzy/setup.bash
source ros2/install/setup.bash
set -u
export PGOPTIONS='-c default_transaction_read_only=on'
export HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
# Each launch owns its children. Never kill unrelated ROS/Gazebo processes.
/usr/bin/python3 - "$ROOT" <<'PY'
import csv, json, os, pathlib, signal, subprocess, sys, uuid
root = pathlib.Path(sys.argv[1])
condition = os.environ.get('HOME01_CONDITION', 'both')
if condition not in ('n0', 'n1', 'both'):
    raise SystemExit('HOME01_CONDITION must be n0, n1 or both')
conditions = ['n0', 'n1'] if condition == 'both' else [condition]
repetitions = int(os.environ.get('HOME01_ATTEMPTS', '2'))
retry_limit = int(os.environ.get('HOME01_INFRA_RETRIES', '2'))
if repetitions < 1 or retry_limit < 0:
    raise SystemExit('Invalid repetition/retry count')
out = pathlib.Path(os.environ.get('HOME01_OUT_DIR', '/tmp/home01_' + uuid.uuid4().hex))
out.mkdir(parents=True, exist_ok=False)
venv = root / ('.venv-memory' if (root / '.venv-memory').exists() else '.venv')
def fingerprint():
    result = subprocess.run([str(venv / 'bin/python'), '-m', 'scripts.memory.fingerprint_memory'],
                            capture_output=True, text=True, cwd=root)
    if result.returncode:
        raise SystemExit('Read-only DB fingerprint failed; no launch started')
    return json.loads(result.stdout)
before = fingerprint() if 'n1' in conditions else None
if before:
    (out / 'db_before.json').write_text(json.dumps(before, sort_keys=True) + '\n')
summary = out / 'summary.tsv'
summary.write_text('condition\trepetition\tattempt\tclassification\tcleanup_status\tcsv\tlog\n')
try:
    for repetition in range(1, repetitions + 1):
        for condition in conditions:
            for attempt in range(1, retry_limit + 2):
                run_id = f'home_{condition}_{repetition}_{attempt}_{uuid.uuid4().hex}'
                csv_path, log_path = out / (run_id + '.csv'), out / (run_id + '.log')
                command = ['ros2', 'launch', 'wheelchair_assistive_bt', f'home_{condition}.launch.py',
                           'gui:=false', f'result_csv:={csv_path}', f'run_id:={run_id}']
                with log_path.open('w') as log:
                    proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                    try:
                        proc.wait(timeout=420)
                    except (subprocess.TimeoutExpired, KeyboardInterrupt):
                        # One signal to the owning launch; let launch wait for children.
                        proc.send_signal(signal.SIGINT)
                        proc.wait(timeout=30)
                        raise SystemExit(f'Launch interrupted; inspect {log_path}')
                log_text = log_path.read_text(errors='replace')
                rows = list(csv.DictReader(csv_path.open())) if csv_path.exists() else []
                row = rows[-1] if len(rows) == 1 else {}
                ok = row.get('success') == 'true' and row.get('final_goal_nav2_result') == 'SUCCEEDED'
                if condition == 'n1':
                    ok = ok and row.get('waypoint_nav2_result') == 'SUCCEEDED' and \
                         row.get('memory_ids') == 'M001|M046|M002' and row.get('source_memory') == 'M001' and \
                         row.get('retrieved_strategy') == 'west' and row.get('strategy_applied') == 'true'
                infra = row.get('failure_stage') == 'readiness' or \
                        '/navigate_to_pose is not ready' in row.get('failure_reason', '') or \
                        'Timed out while waiting for action server to acknowledge goal request' in log_text or \
                        ('readiness failed' in log_text.lower() and not rows)
                classification = 'SUCCESS' if ok else 'INFRASTRUCTURE_FAILURE' if infra else 'FAILURE'
                cleanup_status = 'CHILD_EXIT_WARNING' if 'process has died' in log_text else 'NO_WARNING'
                if 'SIGKILL' in log_text or 'failed to terminate' in log_text:
                    classification = 'CLEANUP_FAILURE'
                with summary.open('a') as f:
                    f.write(f'{condition}\t{repetition}\t{attempt}\t{classification}\t{cleanup_status}\t{csv_path}\t{log_path}\n')
                print(condition, repetition, attempt, classification, cleanup_status, flush=True)
                if classification == 'SUCCESS':
                    break
                if classification != 'INFRASTRUCTURE_FAILURE' or attempt == retry_limit + 1:
                    raise SystemExit(f'Validation stopped: inspect {summary}')
finally:
    if before:
        after = fingerprint()
        (out / 'db_after.json').write_text(json.dumps(after, sort_keys=True) + '\n')
        if before != after:
            raise SystemExit('DB fingerprint changed')
print('Evidence:', out)
PY
