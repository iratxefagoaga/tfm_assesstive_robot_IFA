"""Verify preserved final-result bytes and frozen inputs offline."""
from pathlib import Path
import hashlib
import json
ROOT = Path(__file__).resolve().parents[2]

def verify(root=ROOT):
    directory = root/"experiments/results/final"
    manifest = json.loads((directory/"artifact_manifest.json").read_text(encoding="utf-8"))
    for base, entries in [(root,manifest["scientific_sha256"]),(directory,manifest["files_sha256"])]:
        for name, expected in entries.items():
            target = (base/name).resolve()
            if not target.is_relative_to(base.resolve()):
                raise ValueError("Manifest path escapes artifact root")
            if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise ValueError("Artifact integrity mismatch: "+name)
    return len(manifest["files_sha256"])

if __name__ == "__main__":
    print(f"PASS: {verify()} final artifacts and frozen scientific inputs unchanged")
