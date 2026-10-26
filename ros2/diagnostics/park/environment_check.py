"""Safe local ROS/DB checks. Never prints credentials or complete environment."""
import argparse,json,os,subprocess
from pathlib import Path
from diagnose import ros_environment,load_database_env,fingerprint

p=argparse.ArgumentParser();p.add_argument('--code-root',type=Path,required=True);p.add_argument('--private-env',type=Path,required=True);p.add_argument('--postgres-aliases',action='store_true');p.add_argument('--database-name');p.add_argument('--catalog',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
env=ros_environment(a.code_root)
load_database_env(a.private_env,env,a.postgres_aliases)
if a.database_name:env['MEMORY_DB_NAME']=a.database_name
env['PGOPTIONS']='-c default_transaction_read_only=on'
result={'all_required_present':all(env.get(k) for k in ['MEMORY_DB_HOST','MEMORY_DB_PORT','MEMORY_DB_NAME','MEMORY_DB_USER','MEMORY_DB_PASSWORD'])}
if a.catalog:
    code='import psycopg2,json; from memory.config import memory_database_url; c=psycopg2.connect(memory_database_url()); c.set_session(readonly=True); q=c.cursor(); q.execute("SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate"); print(json.dumps([r[0] for r in q.fetchall()])); c.rollback(); c.close()'
    r=subprocess.run([str(a.code_root/'.venv/bin/python'),'-c',code],cwd=a.code_root,env=env,capture_output=True,text=True,timeout=20)
    if r.returncode:result['catalog_error']='Catalog query failed; details suppressed'
    else:result['available_database_names']=json.loads(r.stdout)
try:
    before=fingerprint(a.code_root,env);after=fingerprint(a.code_root,env)
    frozen=json.loads((a.code_root/'experiments/configs/evaluation_design.json').read_text())['memory_fingerprint']
    result.update(before=before,after=after,unchanged=before==after,matches_frozen_reference=before==frozen)
except Exception as exc:result.update(error_type=type(exc).__name__,reason=str(exc))
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
