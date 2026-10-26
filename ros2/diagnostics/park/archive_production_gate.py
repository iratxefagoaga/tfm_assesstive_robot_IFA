"""Preserve explicit engineering evidence only; no environment or credentials."""
import argparse,hashlib,json,shutil
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('inputs',nargs='+',type=Path);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    for source in a.inputs:
        if not source.is_dir() or source.parent!=Path('/tmp') or not source.name.startswith('park_production_'):
            raise RuntimeError('Only explicitly named PARK production evidence directories may be archived')
        shutil.copytree(source,a.output/source.name)
    code=a.output/'diagnostic_code';code.mkdir()
    for source in Path(__file__).parent.iterdir():
        if source.suffix in {'.py','.md'}:shutil.copy2(source,code/source.name)
    manifest={str(f.relative_to(a.output)):hashlib.sha256(f.read_bytes()).hexdigest() for f in a.output.rglob('*') if f.is_file()}
    (a.output/'archive_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'archive':str(a.output),'files':len(manifest)}))
if __name__=='__main__':main()
