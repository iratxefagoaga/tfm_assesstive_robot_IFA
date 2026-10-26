"""Start only the existing named memory container, fingerprint read-only, restore stopped state."""
import argparse,json,os,subprocess,time
from pathlib import Path
from diagnose import fingerprint
p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
name='tfm_memory_postgres'
info=json.loads(subprocess.run(['docker','inspect',name],capture_output=True,text=True,check=True).stdout)[0]
was_running=info['State']['Running'];report={'container':name,'initially_running':was_running,'created_new_container':False,'used_existing_volume':bool(info.get('Mounts'))}
variables=dict(v.split('=',1) for v in info['Config']['Env'] if '=' in v)
env=os.environ.copy()
for suffix,key in [('USER','USER'),('PASSWORD','PASSWORD'),('DB','NAME')]:env['MEMORY_DB_'+key]=variables['POSTGRES_'+suffix]
bindings=info['HostConfig']['PortBindings'].get('5432/tcp',[])
if len(bindings)!=1:raise SystemExit('Ambiguous published database port')
env.update(MEMORY_DB_HOST='localhost',MEMORY_DB_PORT=bindings[0]['HostPort'],PGOPTIONS='-c default_transaction_read_only=on')
try:
    if not was_running:
        subprocess.run(['docker','start',name],capture_output=True,check=True,timeout=30)
    for _ in range(30):
        r=subprocess.run(['docker','exec',name,'pg_isready','-U',variables['POSTGRES_USER'],'-d',variables['POSTGRES_DB']],capture_output=True,timeout=5)
        if r.returncode==0:break
        time.sleep(1)
    else:raise RuntimeError('Existing database did not become ready')
    before=fingerprint(a.code_root,env);after=fingerprint(a.code_root,env)
    frozen=json.loads((a.code_root/'experiments/configs/evaluation_design.json').read_text())['memory_fingerprint']
    report.update(before=before,after=after,unchanged=before==after,matches_frozen_reference=before==frozen)
except Exception as exc:report.update(error_type=type(exc).__name__,reason=str(exc))
finally:
    if not was_running:
        # One signal to the DB container owner. No forced kill or volume operations.
        subprocess.run(['docker','kill','--signal=SIGINT',name],capture_output=True,check=True,timeout=10)
        try:
            subprocess.run(['docker','wait',name],capture_output=True,check=True,timeout=30);report['restored_stopped_state']=True
        except subprocess.TimeoutExpired:report['restored_stopped_state']=False
    a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
