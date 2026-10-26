"""Check the exact tested simulation artifacts before starting any process or DB."""
import hashlib,json
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def mission_lock(path=Path('/tmp/tfm_park_simulation.lock')):
    import fcntl,os
    with path.open('a+') as stream:
        try:fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another PARK simulation mission is already running') from None
        stream.seek(0);stream.truncate();stream.write(str(os.getpid())+'\n');stream.flush()
        try:yield
        finally:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def check_files(root,expected):
    root=root.resolve()
    if not expected:raise RuntimeError('Empty integrity inventory')
    for relative,expected_sha in expected.items():
        path=root/relative
        # Source installs may contain symlinks; inventory names must stay relative.
        if Path(relative).is_absolute() or '..' in Path(relative).parts:raise RuntimeError('Invalid integrity inventory path')
        if not path.is_file() or sha(path)!=expected_sha:raise RuntimeError('Release artifact missing or changed: '+relative)

def verify_release(profile,code_root,code_directory):
    record=json.loads((profile/'simulation_acceptance.json').read_text())
    if record.get('scope')!='PARK_GAZEBO_SIMULATION' or record.get('status')!='PARK_SIMULATION_RELEASE_READY':raise RuntimeError('Profile is not an accepted simulation release')
    check_files(profile,record['profile_sha256']);check_files(code_directory,record['code_sha256']);check_files(code_root,record['source_sha256'])
    return record
