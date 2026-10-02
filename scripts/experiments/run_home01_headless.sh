#!/usr/bin/env bash
set -uo pipefail

# Reproducible HOME-01 calibration runner.
# Runs each attempt in a fresh ROS/Gazebo process group, classifies readiness
# failures separately from actual navigation outcomes, and preserves per-attempt
# CSV/log artifacts. It never provisions, seeds, or mutates the memory DB.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ROS_DIR="$ROOT/ros2"
OUT_DIR="${HOME01_OUT_DIR:-$ROOT/results/home01_calibration}"
ATTEMPTS="${HOME01_ATTEMPTS:-3}"
WAYPOINT_OFFSETS="${HOME01_WAYPOINT_OFFSETS:-west:-7.5:-8.7}"
CONDITION="${HOME01_CONDITION:-n1}"

mkdir -p "$OUT_DIR"

if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "ERROR: ROS 2 Jazzy not found at /opt/ros/jazzy/setup.bash" >&2
  exit 2
fi
if [[ ! -f "$ROS_DIR/install/setup.bash" ]]; then
  echo "ERROR: build the workspace first: cd $ROS_DIR && colcon build --symlink-install" >&2
  exit 2
fi

# Prefer the project venv when present. This is needed by the memory service.
if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
# shellcheck disable=SC1091
source "$ROS_DIR/install/setup.bash"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PGOPTIONS="${PGOPTIONS:--c default_transaction_read_only=on}"

if [[ "$CONDITION" == "n1" ]]; then
  missing=0
  for name in MEMORY_DB_HOST MEMORY_DB_PORT MEMORY_DB_NAME MEMORY_DB_USER MEMORY_DB_PASSWORD; do
    if [[ -z "${!name:-}" ]]; then
      echo "ERROR: $name is not set" >&2
      missing=1
    fi
  done
  (( missing == 0 )) || exit 2
fi

cleanup_ros() {
  # Only processes launched by this script are normally killed by timeout/launch
  # shutdown. These targeted names remove stragglers between attempts without
  # touching Docker/PostgreSQL.
  pkill -INT -f 'gz sim.*home.world' 2>/dev/null || true
  pkill -INT -f 'home_n[01].launch.py' 2>/dev/null || true
  sleep 3
}
trap cleanup_ros EXIT INT TERM

classify_csv() {
  local csv="$1"
  python3 - "$csv" <<'PY'
import csv, sys
p=sys.argv[1]
try:
    with open(p, newline='') as f:
        rows=list(csv.DictReader(f))
except FileNotFoundError:
    print('INFRASTRUCTURE_FAILURE:no_csv')
    raise SystemExit
if not rows:
    print('INFRASTRUCTURE_FAILURE:empty_csv')
    raise SystemExit
r=rows[-1]
stage=(r.get('failure_stage') or '').strip()
reason=(r.get('failure_reason') or '').strip()
result=(r.get('nav2_result') or '').strip()
success=(r.get('success') or '').strip().lower()
if success == 'true' and result == 'SUCCEEDED':
    print('SUCCESS')
elif stage == 'readiness' or result in ('', 'NOT_SENT'):
    print('INFRASTRUCTURE_FAILURE:' + (reason or stage or 'not_sent'))
else:
    print('NAVIGATION_FAILURE:' + (stage or 'unknown') + ':' + (reason or result or 'unknown'))
PY
}

printf 'HOME-01 headless calibration\n'
printf 'condition=%s attempts=%s output=%s\n' "$CONDITION" "$ATTEMPTS" "$OUT_DIR"
printf 'waypoint_offsets=%s\n' "$WAYPOINT_OFFSETS"

summary="$OUT_DIR/summary.tsv"
printf 'attempt\tclassification\tcsv\tlog\n' > "$summary"

for ((i=1; i<=ATTEMPTS; i++)); do
  cleanup_ros
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  run_id="home_01_${CONDITION}_cal_${i}_${stamp}"
  csv="$OUT_DIR/${run_id}.csv"
  log="$OUT_DIR/${run_id}.log"
  rm -f "$csv"

  echo "=== attempt $i/$ATTEMPTS: $run_id ==="
  if [[ "$CONDITION" == "n1" ]]; then
    cmd=(ros2 launch wheelchair_assistive_bt home_n1.launch.py
      gui:=false result_csv:="$csv" run_id:="$run_id"
      strategy_waypoint_offsets:="$WAYPOINT_OFFSETS")
  elif [[ "$CONDITION" == "n0" ]]; then
    cmd=(ros2 launch wheelchair_assistive_bt home_n0.launch.py
      gui:=false result_csv:="$csv" run_id:="$run_id")
  else
    echo "ERROR: HOME01_CONDITION must be n0 or n1" >&2
    exit 2
  fi

  # Hard ceiling prevents a broken launch from blocking the calibration batch.
  set +e
  timeout --signal=INT --kill-after=20s 420s "${cmd[@]}" 2>&1 | tee "$log"
  launch_rc=${PIPESTATUS[0]}
  set -e

  if [[ -f "$csv" ]]; then
    classification="$(classify_csv "$csv")"
  elif [[ $launch_rc -eq 124 || $launch_rc -eq 137 ]]; then
    classification="INFRASTRUCTURE_FAILURE:runner_timeout"
  else
    classification="INFRASTRUCTURE_FAILURE:no_csv_rc_${launch_rc}"
  fi
  printf '%s\t%s\t%s\t%s\n' "$i" "$classification" "$csv" "$log" >> "$summary"
  echo "RESULT: $classification"
done

cleanup_ros
printf '\n=== HOME-01 summary ===\n'
column -t -s $'\t' "$summary" 2>/dev/null || cat "$summary"
