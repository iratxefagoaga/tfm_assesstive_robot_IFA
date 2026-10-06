"""Prepare/review evaluation manifests; execution is opt-in after human GT approval."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
from time import perf_counter
from scripts.experiments.evaluation_core import (
    load_ground_truth, retrieve_condition, retrieval_metrics, read_only_service,
    evaluate_e3, write_new, descriptive, binary_summary, compare_independent, analyze_paired, holm_adjust,
)
ROOT = Path(__file__).resolve().parents[2]


def fingerprint(service):
    from sqlalchemy import text
    from scripts.memory.fingerprint_memory import SELECT_SQL, fingerprint_rows
    with service.engine.connect() as connection:
        return fingerprint_rows(connection.execute(text(SELECT_SQL)).mappings().all())


def execute_retrieval(kind, dataset, out):
    # Called only after ground truth review gate, never during preparation/tests.
    os.environ['PGOPTIONS'] = '-c default_transaction_read_only=on'
    os.environ['HF_HUB_OFFLINE'] = '1'
    from memory.memory_service import MemoryService
    service = read_only_service(MemoryService())
    before = fingerprint(service)
    if before != dataset['memory_fingerprint'] or before['row_count'] != 50:
        service.engine.dispose()
        raise ValueError('Frozen DB mismatch')
    rows = []
    try:
        for case in dataset['cases']:
            if kind == 'E3' and 'ABLATION_CONTAMINATED' in case.get('flags', []):
                raise ValueError('ABLATION_CONTAMINATED: exclude from execution until human review')
            methods = ['R0','R1'] if kind == 'E2' else ['P0','P1']
            # Counterbalance deterministically per case; preserve order in raw audit.
            random.Random(20261005 + dataset['cases'].index(case)).shuffle(methods)
            for method in methods:
                started = perf_counter()
                ranked = retrieve_condition(service, case, method if kind == 'E2' else 'R1')
                retrieval_ms = (perf_counter()-started)*1000
                if kind == 'E2':
                    ids = [m['memory_id'] for m in ranked]
                    row = {'query_id': case['query_id'], 'method': method, 'condition': method,
                           'retrieved_ids': ids, 'ranks': list(range(1,len(ids)+1)),
                           'scores': [{'semantic':m['semantic_similarity'], 'context':m['context_score'], 'final':m['final_score']} for m in ranked],
                           'relevant_ids': list(case['relevant_memory_ids']),
                           **{f'rank{i+1}': ids[i] if i < len(ids) else '' for i in range(3)},
                           **retrieval_metrics(ids,case['relevant_memory_ids'])}
                else:
                    row = evaluate_e3(case,ranked,method)
                row['latency_ms'] = retrieval_ms if kind == 'E2' else (perf_counter()-started)*1000
                rows.append(row)
                write_new(out/'raw'/f"{case.get('query_id',case.get('case_id'))}_{method}.json",
                          [{'ranking': ranked, 'output': row}])
    finally:
        after = fingerprint(service)
        service.engine.dispose()
        write_new(out/'db_fingerprints.json',[{'before':before,'after':after}])
        if before != after:
            raise ValueError('DB fingerprint changed')
    write_new(out/'processed'/'metrics.csv',rows)
    summary = {}
    for method in sorted({row['method'] for row in rows}):
        group = [row for row in rows if row['method'] == method]
        if kind == 'E2':
            summary[method] = {key:sum(row[key] for row in group)/len(group)
                               for key in ['precision_at_3','recall_at_3','reciprocal_rank','hit_at_3']}
            summary[method]['MRR'] = summary[method].pop('reciprocal_rank')
        else:
            evaluable = [row for row in group if row['strategy_accuracy'] != 'N/A']
            used = [row for row in group if row['relevant_memory_used'] != 'N/A']
            summary[method] = {'evaluable_cases':len(evaluable),
                'primary_cases_withheld':sum(not row['primary_eligible'] for row in group),
                'evaluable_coverage':binary_summary([row['evaluable_coverage'] for row in group]),
                'strategy_accuracy':sum(row['strategy_accuracy'] for row in evaluable)/len(evaluable) if evaluable else None,
                'relevant_memory_used_rate':sum(row['relevant_memory_used'] for row in used)/len(used) if used else None,
                'memory_hit_rate':sum(row['memory_hit'] for row in group)/len(group)}
        summary[method]['latency_ms'] = descriptive([row['latency_ms'] for row in group])
    write_new(out/'processed'/'summary.json',[summary])
    write_new(out/'processed'/'paired_analysis.json',[analyze_paired(rows,kind)])


def require_e1_runtime_validation(path=None):
    """Gate E1 on preserved, excluded engineering evidence and source identity."""
    path = Path(path) if path is not None else ROOT/'experiments/runtime/e1_runtime_validation.json'
    try:
        state = json.loads(path.read_text())
        if state['status'] != 'E1_RUNTIME_MEASUREMENT_VALIDATED':
            raise ValueError('E1 runtime measurement not validated')
        if state['included_in_e1_campaign'] is not False or state['included_in_h1_analysis'] is not False:
            raise ValueError('Engineering evidence must be excluded from E1/H1')
        capture = ROOT/'scripts/experiments/capture_trajectory.py'
        if hashlib.sha256(capture.read_bytes()).hexdigest() != state['capture_sha256']:
            raise ValueError('Capture changed since runtime validation')
        manifest = json.loads((ROOT/'experiments/configs/freeze_manifest.json').read_text())
        if state['scientific_sha256'] != manifest['artifacts_sha256']:
            raise ValueError('Scientific freeze evidence mismatch')
        for name, digest in state['scientific_sha256'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
                raise ValueError('Scientific freeze mutation')
        for condition in ['N0', 'N1']:
            run = state['runs'][condition]
            directory = Path(run['directory'])
            validation = directory/'validation.json'
            if hashlib.sha256(validation.read_bytes()).hexdigest() != run['validation_sha256']:
                raise ValueError('Runtime validation record changed')
            evidence = json.loads(validation.read_text())
            if (evidence['status'] != 'PASS' or evidence['condition'] != condition or
                    evidence['included_in_e1_campaign'] is not False or
                    evidence['included_in_h1_analysis'] is not False or
                    evidence['tf_errors'] != 0 or evidence['csv_columns'] != 36 or
                    evidence['offline_replay'] != 'BYTE_IDENTICAL'):
                raise ValueError('Incomplete E1 runtime evidence')
            for name, digest in evidence['artifact_sha256'].items():
                if hashlib.sha256((directory/name).read_bytes()).hexdigest() != digest:
                    raise ValueError('Runtime artifact changed')
        return state
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('E1 runtime evidence missing or incomplete') from error


def e1_plan(config, dataset):
    jobs = []
    for case in dataset['cases']:
        for rep in range(1, config['repetitions_per_condition']+1):
            for condition in config['conditions']:
                jobs.append({'case_id':case['case_id'],'scenario':case['scenario'],
                             'repetition':rep,'memory_condition':condition})
    random.Random(config['randomization_seed']).shuffle(jobs)
    for i, job in enumerate(jobs):
        job['planned_order'] = i+1
        job['launch'] = f"{job['scenario']}_{job['memory_condition'].lower()}.launch.py"
        job['max_attempts'] = 2
        job['launch_command'] = ['ros2','launch','wheelchair_assistive_bt',job['launch'],
                                  'gui:=false','run_id:=<unique-run-id>', 'result_csv:=<raw-run-directory>/result.csv']
    return jobs


def analyze(rows, allow_synthetic=False):
    if any(row.get('synthetic') is True for row in rows):
        if not allow_synthetic or not all(row.get('synthetic') is True for row in rows):
            raise ValueError('Synthetic results require a separate explicitly synthetic analysis')
    if rows and 'scenario' not in rows[0]:
        return analyze_paired(rows,'E2' if 'query_id' in rows[0] else 'E3')
    output = {}
    for scenario in sorted({row['scenario'] for row in rows}):
        scenario_rows = [r for r in rows if r['scenario']==scenario]
        result = {}
        for condition in ['N0','N1']:
            group = [r for r in scenario_rows if r['memory_condition']==condition and r.get('classification') not in ['INFRASTRUCTURE_FAILURE','INFRASTRUCTURE_BLOCKED','CLEANUP_FAILURE']]
            result[condition] = {key:descriptive([r.get(key,'N/A') for r in group]) for key in ['navigation_time_s','distance_m','replanning_count','memory_latency_ms']}
            result[condition].update({key:binary_summary([r.get(key,'N/A') for r in group]) for key in ['success','context_compliance']})
            result[condition]['attempts_excluded'] = sum(r['memory_condition']==condition for r in scenario_rows)-len(group)
        result['comparisons'] = {}
        for key in ['navigation_time_s','distance_m','replanning_count']:
            groups = [[float(r[key]) for r in scenario_rows if r['memory_condition']==c and r.get('classification')=='SUCCESS' and r.get(key) not in (None,'N/A','')] for c in ['N1','N0']]
            result['comparisons'][key] = compare_independent(*groups)
        from scipy.stats import fisher_exact
        result['binary_comparisons'] = {}
        for key in ['success','context_compliance']:
            a,b = [result[c][key] for c in ['N1','N0']]
            if a['n'] and b['n']:
                table = [[a['count'],a['n']-a['count']],[b['count'],b['n']-b['count']]]
                result['binary_comparisons'][key] = {'p':float(fisher_exact(table).pvalue),'risk_difference_N1_minus_N0':a['count']/a['n']-b['count']/b['n']}
        output[scenario] = result
    adjusted = holm_adjust({name:result['binary_comparisons'].get('context_compliance',{}).get('p',1.0) for name,result in output.items()})
    for name,pvalue in adjusted.items():
        output[name]['binary_comparisons'].setdefault('context_compliance',{'status':'NOT_EVALUABLE'})['primary_Holm_p'] = pvalue
    for result in output.values():
        secondary = {key:value.get('p',1.0) for key,value in result['comparisons'].items()}
        secondary['success'] = result['binary_comparisons'].get('success',{}).get('p',1.0)
        for key,pvalue in holm_adjust(secondary).items():
            collection = result['binary_comparisons'] if key == 'success' else result['comparisons']
            collection.setdefault(key,{'status':'NOT_EVALUABLE'})['secondary_Holm_p'] = pvalue
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', choices=['E1','E2','E3','analyze'])
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--synthetic',action='store_true',help='Analyze an exclusively synthetic fixture dataset')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--input',type=Path)
    args = parser.parse_args()
    if args.experiment=='analyze':
        if not args.input:
            parser.error('--input processed JSON required')
        rows=json.loads(args.input.read_text())
        write_new(args.output,[{'synthetic':args.synthetic,'analysis':analyze(rows,allow_synthetic=args.synthetic)}])
        return
    names={'E1':'navigation_ground_truth','E2':'contextual_retrieval','E3':'episodic_personalization'}
    path=ROOT/'experiments/ground_truth'/f'{names[args.experiment]}.json'
    dataset=load_ground_truth(path,args.experiment,approved=args.execute)
    config=json.loads((ROOT/'experiments/configs/evaluation_design.json').read_text())
    if args.experiment=='E1':
        if args.execute:
            try:
                require_e1_runtime_validation()
            except ValueError as error:
                parser.error(str(error))
        # Existing E1 branch emits its campaign plan; it never launches processes.
        # --execute now checks preserved technical evidence before permitting it.
        write_new(args.output,e1_plan(config,dataset))
    elif not args.execute:
        write_new(args.output,[{'status':dataset['status'],'experiment':args.experiment,'case_count':len(dataset['cases']),
                                'ground_truth_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'execution':'NOT_RUN'}])
    else:
        if args.output.exists():
            parser.error('Use a fresh output directory; raw results cannot be overwritten')
        args.output.mkdir(parents=True)
        write_new(args.output/'manifest.json',[{'ground_truth_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'baseline_commit':dataset['baseline_commit'],'experiment':args.experiment}])
        execute_retrieval(args.experiment,dataset,args.output)


if __name__ == '__main__':
    main()
