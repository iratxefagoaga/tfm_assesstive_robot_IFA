"""Prospective PARK replication: fixed 10 N0 + 10 N1, no replacement trials."""
import argparse, hashlib, json, random, subprocess, sys, time
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entrypoint', type=Path, required=True)
    p.add_argument('--code-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--campaign-id', default='PARK_CORRECTED_20261026')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    release = a.entrypoint.parent / json.loads((a.entrypoint.parent/'current.json').read_text())['release']
    manifest = release/'profile/simulation_acceptance.json'
    order = ['direct']*10 + ['memory']*10
    random.Random(20261026).shuffle(order)
    protocol = {
        'campaign': a.campaign_id, 'kind': 'PROSPECTIVE_POST_CORRECTION_REPLICATION',
        'seed': 20261026, 'order': order, 'planned_per_condition': 10, 'retries': 0,
        'case': 'PARK_01', 'start': [0, -9, 0], 'waypoint_N1': [-1, -9, 0], 'goal': [1, -9, 0],
        'primary_outcome': 'successful applicable Nav2 goals AND independent Gazebo arrival and settled pose <=0.25 m/0.25 rad; recent pose <=2 s; clean shutdown',
        'denominator': 'all scheduled attempts; no replacement or silent exclusion; interrupted campaign reported incomplete',
        'secondary_outcome': 'original Nav2 action success alone, reported separately',
        'same_corrected_profile_for_N0_N1': True, 'no_fault_injection': True,
        'stop_rule': 'stop on process residues or changed DB fingerprint; preserve every failure',
        'release_manifest_sha256': sha(manifest), 'entrypoint_sha256': sha(a.entrypoint),
        'runner_sha256': sha(Path(__file__)), 'frozen_E1': 'unchanged, separate historical campaign',
        'limitations': ['single canonical mission and static environment', 'same local machine, no independent replication', 'post hoc correction after original E1; no causal attribution to a single change']}
    (a.output/'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    rows = []
    status = 'RUNNING'
    try:
        for i, mode in enumerate(order, 1):
            if sha(manifest) != protocol['release_manifest_sha256']:
                raise RuntimeError('Release changed during campaign')
            directory = a.output/f'{i:02d}_{mode}'
            with (a.output/f'{i:02d}_{mode}.log').open('w') as log:
                command = [sys.executable, str(a.entrypoint), '--code-root', str(a.code_root), '--mode', mode, '--output', str(directory)]
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
            decision_path = directory/'physical_acceptance.json'
            pilot_path = directory/'pilot_results.json'
            pilot = json.loads(pilot_path.read_text())[0] if pilot_path.exists() else {}
            decision = json.loads(decision_path.read_text()) if decision_path.exists() else {'accepted': False, 'reasons': ['execution_did_not_finalize_acceptance']}
            final_rows = pilot.get('result', [])
            final = final_rows[0] if len(final_rows)==1 else {}
            before, after = directory/'db_before.json', directory/'db_after.json'
            db_ok = mode != 'memory' or (before.exists() and after.exists() and json.loads(before.read_text()) == json.loads(after.read_text()))
            row = {'index': i, 'mode': mode, 'condition': 'N0' if mode=='direct' else 'N1', 'directory': directory.name,
                   'returncode': result.returncode, 'accepted': result.returncode==0 and decision['accepted'],
                   'decision': decision, 'action_success': final.get('success')=='true' and final.get('final_goal_nav2_result')=='SUCCEEDED',
                   'cleanup_ok': pilot.get('cleanup_ok', False), 'residual_pids': pilot.get('residual_pids', []),
                   'db_unchanged': db_ok, 'csv': final, 'categories': pilot.get('categories', {})}
            rows.append(row)
            summary = {'campaign': protocol['campaign'], 'completed': len(rows), 'planned': 20, 'runs': rows,
                       'conditions': {c: {'attempts': sum(r['condition']==c for r in rows), 'accepted': sum(r['condition']==c and r['accepted'] for r in rows), 'action_successes': sum(r['condition']==c and r['action_success'] for r in rows)} for c in ['N0','N1']}}
            (a.output/'results.json').write_text(json.dumps(summary, indent=2)+'\n')
            print(json.dumps({'completed': i, 'condition': row['condition'], 'accepted': row['accepted'], 'returncode': result.returncode}), flush=True)
            if row['residual_pids'] or not db_ok or not pilot.get('processes_terminated', False):
                raise RuntimeError('Campaign stopped: unsafe process state or DB integrity unavailable; no replacement trials')
        status = 'COMPLETED'
    finally:
        (a.output/'status.json').write_text(json.dumps({'status': status if len(rows)==20 else 'INCOMPLETE_STOPPED', 'completed': len(rows), 'planned': 20}, indent=2)+'\n')
    return 0 if status=='COMPLETED' else 1


if __name__=='__main__':
    raise SystemExit(main())
