import hashlib
import json
import pytest
from scripts.experiments import run_evaluation as runner


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    # Synthetic metadata exercises the gate; never scientific observations.
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    capture = tmp_path/'scripts/experiments/capture_trajectory.py'
    put(capture, {'synthetic_guard_fixture': True})
    science = tmp_path/'frozen.json'
    put(science, {'synthetic_guard_fixture': True})
    hashes = {'frozen.json': digest(science)}
    put(tmp_path/'experiments/configs/freeze_manifest.json', {'artifacts_sha256': hashes})
    state = {'status': 'E1_RUNTIME_MEASUREMENT_VALIDATED', 'included_in_e1_campaign': False,
             'included_in_h1_analysis': False, 'capture_sha256': digest(capture),
             'scientific_sha256': hashes, 'runs': {}}
    for condition in ['N0', 'N1']:
        directory = tmp_path/condition
        artifact = directory/'raw.json'
        put(artifact, {'synthetic_guard_fixture': True})
        validation = directory/'validation.json'
        put(validation, {'status': 'PASS', 'condition': condition,
            'included_in_e1_campaign': False, 'included_in_h1_analysis': False,
            'tf_errors': 0, 'csv_columns': 36, 'offline_replay': 'BYTE_IDENTICAL',
            'artifact_sha256': {'raw.json': digest(artifact)}})
        state['runs'][condition] = {'directory': str(directory), 'validation_sha256': digest(validation)}
    path = tmp_path/'technical_state.json'
    put(path, state)
    return path, state, tmp_path


def test_guard_accepts_complete_unchanged_excluded_evidence(evidence):
    path, state, _ = evidence
    assert runner.require_e1_runtime_validation(path) == state


def test_guard_rejects_missing_state(tmp_path):
    with pytest.raises(ValueError):
        runner.require_e1_runtime_validation(tmp_path/'absent.json')


@pytest.mark.parametrize('mutation', ['missing_N1', 'capture', 'raw', 'campaign_inclusion'])
def test_guard_rejects_incomplete_or_mutated_evidence(evidence, mutation):
    path, state, root = evidence
    if mutation == 'missing_N1':
        del state['runs']['N1']
        put(path, state)
    elif mutation == 'capture':
        (root/'scripts/experiments/capture_trajectory.py').write_text('changed')
    elif mutation == 'raw':
        (root/'N1/raw.json').write_text('changed')
    else:
        state['included_in_e1_campaign'] = True
        put(path, state)
    with pytest.raises(ValueError):
        runner.require_e1_runtime_validation(path)
