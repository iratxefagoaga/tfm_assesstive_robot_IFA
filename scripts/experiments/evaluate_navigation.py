"""Process one immutable E1 logger row with separate map trajectory evidence."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from scripts.experiments.evaluation_core import load_ground_truth,evaluate_navigation,write_new


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ground-truth',type=Path,required=True)
    parser.add_argument('--case-id',required=True)
    parser.add_argument('--condition',choices=['N0','N1'],required=True)
    parser.add_argument('--result',type=Path,required=True)
    parser.add_argument('--classification',choices=['SUCCESS','NAVIGATION_FAILURE','INFRASTRUCTURE_FAILURE','INFRASTRUCTURE_BLOCKED','CLEANUP_FAILURE'],required=True,help='Separate predeclared attempt audit classification; never infer from missing CSV')
    parser.add_argument('--trajectory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--trajectory-complete',action='store_true',help='Requires independently verified capture/start/end coverage')
    parser.add_argument('--synthetic',action='store_true',help='Allow DRAFT solely for explicitly synthetic fixtures')
    args=parser.parse_args()
    data=load_ground_truth(args.ground_truth,'E1',approved=not args.synthetic)
    case=next(c for c in data['cases'] if c['case_id']==args.case_id)
    rows=list(csv.DictReader(args.result.open()))
    if len(rows)!=1:parser.error('Exactly one finalized raw logger row required')
    samples=[json.loads(line) for line in args.trajectory.read_text().splitlines() if line]
    bad=any('capture_error' in row for row in samples)
    raw=rows[0]
    expected_condition={'N0':'MEMORY_OFF','N1':'MEMORY_ON'}[args.condition]
    if raw.get('condition') != expected_condition:
        parser.error('Condition disagrees with immutable raw logger row')
    if not raw.get('scenario_id','').startswith(case['case_id']):
        parser.error('Raw scenario does not match ground truth case')
    if raw.get('success') not in ('true','false'):
        parser.error('Raw success must be explicitly true or false')
    if args.classification == 'SUCCESS' and raw['success'] != 'true':
        parser.error('SUCCESS classification contradicts raw navigation result')
    result={**raw,'scenario':case['scenario'],'case_id':case['case_id'],
            'memory_condition':args.condition,'success':int(raw.get('success')=='true'),
            'classification':args.classification,
            'trajectory_complete':args.trajectory_complete and not bad,
            'memory_latency_ms':raw.get('memory_latency_ms','N/A'),'synthetic':args.synthetic}
    processed=evaluate_navigation(case,result,samples if not bad else [])
    processed['provenance']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.ground_truth,args.result,args.trajectory]}
    write_new(args.output,[processed])


if __name__=='__main__':main()
