import hashlib
import json
import pytest
from scripts.experiments.verify_final_results import verify

@pytest.fixture
def collection(tmp_path):
    directory = tmp_path/"experiments/results/final"
    directory.mkdir(parents=True)
    frozen = tmp_path/"frozen.json"
    frozen.write_text("synthetic fixture")
    result = directory/"result.json"
    result.write_text("synthetic result")
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"scientific_sha256":{"frozen.json":sha(frozen)},
                "files_sha256":{"result.json":sha(result)}}
    (directory/"artifact_manifest.json").write_text(json.dumps(manifest))
    return tmp_path, directory, manifest

def test_intact_collection(collection):
    assert verify(collection[0]) == 1

@pytest.mark.parametrize("file", ["frozen.json","experiments/results/final/result.json"])
def test_reject_mutated_science_or_results(collection,file):
    root, _, _ = collection
    (root/file).write_text("changed")
    with pytest.raises(ValueError,match="integrity mismatch"):
        verify(root)

def test_reject_path_escape(collection):
    root, directory, manifest = collection
    manifest["files_sha256"] = {"../../../../outside.json":"irrelevant"}
    (directory/"artifact_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match="escapes"):
        verify(root)
