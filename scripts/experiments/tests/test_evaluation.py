import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts.experiments.evaluation_core import (
    load_ground_truth,route_classifier,evaluate_navigation,retrieval_metrics,
    retrieve_condition,episodic_condition,evaluate_e3,write_new,descriptive,
    binary_summary,read_only_service,recommend,
)
from scripts.experiments.run_evaluation import e1_plan
ROOT=Path(__file__).resolve().parents[3]
GT=ROOT/'experiments/ground_truth'

@pytest.mark.parametrize('kind,name,count',[('E1','navigation_ground_truth',2),('E2','contextual_retrieval',20),('E3','episodic_personalization',10)])
def test_schemas_frozen_and_approval_gate(kind,name,count,tmp_path):
    path=GT/f'{name}.json'
    data=load_ground_truth(path,kind,approved=True)
    assert data['status']=='FROZEN' and len(data['cases'])==count
    assert data['review']['approved'] and data['review']['reviewer']=='HUMAN_APPROVED'
    # Approval must be complete; merely setting FROZEN cannot authorize execution.
    for status,field,value in [('DRAFT_REVIEWED','approved',True),('FROZEN','approved',False),
                              ('FROZEN','reviewer',None),('FROZEN','date',None)]:
        candidate=json.loads(path.read_text());candidate['status']=status
        candidate['review'][field]=value
        fixture=tmp_path/f'{kind}_{field}_{status}.json'
        fixture.write_text(json.dumps(candidate))
        with pytest.raises(ValueError,match='Human review'):
            load_ground_truth(fixture,kind,approved=True)


def trajectory(points):return [dict(t=i*.2,x=x,y=y,frame='map') for i,(x,y) in enumerate(points)]
def geometry():return {'frame':'map','spawn':[0,0],'goal':[1,0],'endpoint_tolerance_m':.1,'max_gap_s':.5,'max_segment_m':.8,'west_region':[-.6,-.3,-.2,.2],'direct_corridor':[-.1,1.1,-.2,.2]}
@pytest.mark.parametrize('condition',['N0','N1'])
def test_same_geometry_for_both_conditions(condition):
    case={'ground_truth_strategy':'west','route_geometry':geometry()}
    west=trajectory([(0,0),(-.5,0),(-.4,0),(-.3,0),(0,0),(.5,0),(1,0)])
    direct=trajectory([(0,0),(.5,0),(1,0)])
    result={'memory_condition':condition,'trajectory_complete':True,'expected_strategy':'arbitrary'}
    assert evaluate_navigation(case,result,west)['context_compliance']==1
    assert evaluate_navigation(case,result,direct)['context_compliance']==0
    case['ground_truth_strategy']='direct'
    assert evaluate_navigation(case,result,direct)['context_compliance']==1

@pytest.mark.parametrize('fault',['frame','gap','jump','incomplete','unknown','nan'])
def test_missing_or_ambiguous_evidence_na(fault):
    pts=trajectory([(0,0),(.5,0),(1,0)]); complete=True
    if fault=='frame':pts[1]['frame']='odom'
    if fault=='gap':pts[1]['t']=5
    if fault=='jump':pts[1]['x']=9
    if fault=='incomplete':complete=False
    if fault=='unknown':pts[1]['y']=.4
    if fault=='nan':pts[1]['x']=float('nan')
    assert route_classifier(pts,geometry(),complete)=='N/A'

def test_metrics_standard_and_mrr_full_ranking():
    result=retrieval_metrics(['X','A','B','C'],['A','C'])
    assert result=={'hits_at_3':1,'precision_at_3':1/3,'recall_at_3':.5,'reciprocal_rank':.5,'hit_at_3':1}
    assert retrieval_metrics(['X','Y','Z','A'],['A'])['reciprocal_rank']==.25
    assert retrieval_metrics([],['A'])['precision_at_3']==0
    with pytest.raises(ValueError):retrieval_metrics(['A','A'],['A'])


def test_semantic_baseline_has_no_context_and_reuses_production():
    calls=[]
    service=SimpleNamespace(retrieve_memories=lambda **kw:calls.append(kw) or [])
    case={'query':'q','context':dict(user_id='U01',location='salon',task='navegacion',goal='g')}
    retrieve_condition(service,case,'R0'); retrieve_condition(service,case,'R1')
    assert all(calls[0][k] is None for k in case['context'])
    assert calls[1]['user_id']=='U01'
    assert calls[0]['k']==calls[1]['k']==50


def test_e3_isolation_does_not_mutate_or_change_remaining_order():
    ranked=[{'memory_id':'A'},{'memory_id':'B'},{'memory_id':'C'},{'memory_id':'D'}]
    before=json.dumps(ranked)
    assert [r['memory_id'] for r in episodic_condition(ranked,['B'],'P0')]==['A','C','D']
    assert [r['memory_id'] for r in episodic_condition(ranked,['B'],'P1')]==['A','B','C']
    assert json.dumps(ranked)==before
    case={'case_id':'c','evidence_memory_ids':['A'],'ground_truth_strategy':'west'}
    fake=lambda rows:dict(success=bool(rows),strategy='west',source_memory=rows[0]['memory_id'])
    assert evaluate_e3(case,ranked,'P1',fake)['relevant_memory_used']==1
    assert evaluate_e3(case,ranked,'P0',fake)['relevant_memory_used']==0


def test_readonly_gate_and_no_writes():
    calls=[]
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def execute(self,statement):
            calls.append(str(statement));return SimpleNamespace(scalar=lambda:'on')
    service=SimpleNamespace(engine=SimpleNamespace(connect=lambda:Connection()))
    assert read_only_service(service) is service
    assert calls==['SHOW default_transaction_read_only']


def test_raw_exclusive_and_summary_missingness(tmp_path):
    p=tmp_path/'raw.json';write_new(p,[{'a':1}])
    with pytest.raises(FileExistsError):write_new(p,[{'a':2}])
    assert descriptive([1,2,3,'N/A'])['n']==3
    assert descriptive([1,2,3])['IQR']==1
    assert binary_summary([1,0,'N/A'])=={'n':2,'count':1,'percentage':50}


def test_forty_job_manifest_no_airport():
    dataset=load_ground_truth(GT/'navigation_ground_truth.json','E1')
    config=json.loads((ROOT/'experiments/configs/evaluation_design.json').read_text())
    a=e1_plan(config,dataset);assert a==e1_plan(config,dataset);assert len(a)==40
    assert {row['scenario'] for row in a}=={'home','park'}
    for scenario in ('home','park'):
        for condition in ('N0','N1'):assert sum(r['scenario']==scenario and r['memory_condition']==condition for r in a)==10


def test_reuse_real_recommendation_no_node_or_db():
    row=dict(memory_id='SYNTHETIC',action='Ruta oeste',preference='',observation='',outcome='',semantic_similarity=.8,context_score=1,final_score=.82)
    assert recommend([row])['strategy']=='west'


def test_e3_groups_include_all_declared_same_user_personalized_evidence():
    import csv
    rows={r['memory_id']:r for r in csv.DictReader((ROOT/'experiments/data/memory_seed.csv').open())}
    data=load_ground_truth(GT/'episodic_personalization.json','E3')
    for case in data['cases']:
        assert all(rows[mid]['user_id']==case['context']['user_id'] for mid in case['evidence_memory_ids'])
    group=data['cases'][0]['evidence_memory_ids']
    assert {'M001','M002','M006','M007','M013','M015','M046'} <= set(group)
    assert 'semantic' in rows['M013']['memory_type'].split(';')
    assert data['claim'].startswith('Availability of personalized evidence')


def test_analysis_effect_and_na_latency():
    from scripts.experiments.evaluation_core import compare_independent
    from scripts.experiments.run_evaluation import analyze
    assert compare_independent([3,4],[1,2])['cliffs_delta_N1_minus_N0']==1
    rows=[]
    for condition,compliance in [('N0',0),('N1',1)]:
        for i in range(2):
            rows.append(dict(scenario='home',memory_condition=condition,classification='SUCCESS',success=1,context_compliance=compliance,navigation_time_s=2+i,distance_m=1+i,replanning_count=i,memory_latency_ms='N/A'))
    output=analyze(rows)['home']
    assert output['N0']['memory_latency_ms']['n']==0
    assert output['binary_comparisons']['context_compliance']['risk_difference_N1_minus_N0']==1


def test_default_readonly_off_is_rejected():
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def execute(self,statement):return SimpleNamespace(scalar=lambda:'off')
    with pytest.raises(ValueError,match='read-only'):
        read_only_service(SimpleNamespace(engine=SimpleNamespace(connect=lambda:Connection())))


@pytest.mark.parametrize('value',[None,'invalid'])
def test_incomplete_coordinates_are_na(value):
    points=trajectory([(0,0),(.5,0),(1,0)])
    points[1]['x']=value
    assert route_classifier(points,geometry(),True)=='N/A'
    del points[1]['x']
    assert route_classifier(points,geometry(),True)=='N/A'


def test_invalid_numeric_metrics_rejected():
    with pytest.raises(ValueError):binary_summary([.5])
    with pytest.raises(ValueError):descriptive([float('nan')])


def test_synthetic_analysis_cannot_mix_with_experiment():
    from scripts.experiments.run_evaluation import analyze
    with pytest.raises(ValueError,match='Synthetic'):
        analyze([dict(synthetic=True)])
    with pytest.raises(ValueError,match='Synthetic'):
        analyze([dict(synthetic=True),dict(synthetic=False)],allow_synthetic=True)


@pytest.mark.parametrize('kind',['E2','E3'])
def test_offline_runner_raw_processed_and_summaries(kind,tmp_path,monkeypatch):
    import sys,types
    import scripts.experiments.run_evaluation as runner
    calls=[]
    sample=dict(memory_id='A',action='Ruta oeste',preference='',observation='',outcome='',semantic_similarity=.8,context_score=1,final_score=.82)
    service=SimpleNamespace(engine=SimpleNamespace(dispose=lambda:calls.append('dispose')),
                            retrieve_memories=lambda **kwargs:[dict(sample)])
    module=types.ModuleType('memory.memory_service');module.MemoryService=lambda:service
    monkeypatch.setitem(sys.modules,'memory.memory_service',module)
    monkeypatch.setattr(runner,'read_only_service',lambda obj:obj)
    fp={'row_count':50,'logical_sha256':'synthetic','embeddings_sha256':'synthetic'}
    monkeypatch.setattr(runner,'fingerprint',lambda obj:dict(fp))
    case=dict(query_id='synthetic_query',case_id='synthetic_case',query='synthetic',context=dict(user_id='u',location='l',task='t',goal='g'),relevant_memory_ids=['A'],evidence_memory_ids=['A'],ground_truth_strategy='west')
    runner.execute_retrieval(kind,dict(memory_fingerprint=fp,cases=[case]),tmp_path)
    assert len(list((tmp_path/'raw').glob('*.json')))==2
    assert (tmp_path/'processed/metrics.csv').exists()
    summary=json.loads((tmp_path/'processed/summary.json').read_text())[0]
    if kind=='E2':assert summary['R0']['MRR']==summary['R1']['MRR']==1
    else:
        assert summary['P1']['strategy_accuracy']==1
        assert summary['P0']['evaluable_cases']==0
        assert summary['P0']['memory_hit_rate']==0
    assert calls==['dispose']


@pytest.mark.parametrize('points', [
    [(0,0),(-.5,0),(0,0),(.5,0),(1,0)],
    [(0,0),(-.5,0),(0,0),(-.5,0),(0,0),(.5,0),(1,0)],
])
def test_isolated_or_nonconsecutive_west_samples_are_not_west(points):
    assert route_classifier(trajectory(points),geometry(),True)=='N/A'


def test_short_fast_sequence_does_not_meet_dwell_and_boundary_is_inclusive():
    points=trajectory([(0,0),(-.6,0),(-.5,0),(-.3,0),(0,0),(.5,0),(1,0)])
    assert route_classifier(points,geometry(),True)=='west'
    for i,p in enumerate(points):p['t']=i*.01
    assert route_classifier(points,geometry(),True)=='N/A'


def test_route_parameters_cannot_weaken_reviewed_rule():
    g=geometry();g['west_min_consecutive_samples']=1
    with pytest.raises(ValueError,match='thresholds'):
        route_classifier(trajectory([(0,0),(.5,0),(1,0)]),g,True)


def test_all_relevance_judgements_are_exhaustive_same_user_and_temporally_coherent():
    import csv
    memories={m['memory_id']:m for m in csv.DictReader((ROOT/'experiments/data/memory_seed.csv').open())}
    cases=load_ground_truth(GT/'contextual_retrieval.json','E2')['cases']
    for c in cases:
        assert set(c['reviewed_memory_ids'])==set(memories)
        assert len(c['relevance_judgements'])==50
        assert all(memories[mid]['user_id']==c['context']['user_id'] for mid in c['relevant_memory_ids'])
        assert all(j['rationale'] for j in c['relevance_judgements'])
        assert not {'M046','M048'} & set(c['relevant_memory_ids'])
    assert 'M047' in cases[9]['relevant_memory_ids']
    assert 'M047' in cases[10]['relevant_memory_ids']
    assert 'M047' not in cases[12]['relevant_memory_ids']


@pytest.mark.parametrize('mid,expected',[('M002','alternative'),('M016','central'),('M008','direct'),('M014','direct'),('M041','central'),('M047','west')])
def test_taxonomy_matches_real_production_parser_without_equivalence(mid,expected):
    import csv
    memory=next(m for m in csv.DictReader((ROOT/'experiments/data/memory_seed.csv').open()) if m['memory_id']==mid)
    row={**memory,'semantic_similarity':.8,'context_score':1.,'final_score':.82}
    assert recommend([row])['strategy']==expected


def test_group_ablation_filters_before_top3_and_records_exact_ids():
    ranked=[dict(memory_id=mid) for mid in ['A','B','C','D','E','F']]
    group=['A','B','C']
    case=dict(case_id='synthetic',evidence_group_id='group',evidence_memory_ids=group,ground_truth_strategy='west')
    fake=lambda rows:dict(success=True,strategy='west',source_memory=rows[0]['memory_id'])
    answer=evaluate_e3(case,ranked,'P0',fake)
    assert answer['excluded_ids']==group
    assert answer['ranked_ids']==['D','E','F']
    assert evaluate_e3(case,ranked,'P1',fake)['excluded_ids']==[]


def test_contamination_blocks_evaluation_and_defaults_are_withheld_from_primary():
    case=dict(case_id='synthetic',evidence_memory_ids=['A'],ground_truth_strategy='direct',flags=['ABLATION_CONTAMINATED'])
    with pytest.raises(ValueError,match='ABLATION_CONTAMINATED'):
        evaluate_e3(case,[],'P1')
    case['flags']=['DEFAULT_SENSITIVE']
    answer=evaluate_e3(case,[dict(memory_id='A',action='unrecognized')],'P1',lambda rows:dict(success=True,strategy='direct',source_memory='A'))
    assert answer['strategy_correct']==1
    assert answer['strategy_accuracy']=='N/A'
    assert answer['source_explicit_direct'] is False


def test_paired_effect_exact_binary_test_and_holm():
    from scripts.experiments.evaluation_core import compare_paired,holm_adjust
    answer=compare_paired([0,0,0],[1,1,1],binary=True)
    assert answer['n_pairs']==3 and answer['p']==.25
    assert answer['effect_second_minus_first']==1
    assert answer['paired_bootstrap_95_CI']==[1,1]
    assert compare_paired([1,2],[1,2])['p']==1
    assert holm_adjust({'a':.01,'b':.04,'c':.03})=={'a':.03,'c':.06,'b':.06}
    with pytest.raises(ValueError):compare_paired([1],[1,2])


def test_paired_analysis_matches_ids_and_reports_missing_not_independent_groups():
    from scripts.experiments.evaluation_core import analyze_paired
    rows=[]
    for q in ['q1','q2']:
        for condition,value in [('R0',0),('R1',1)]:
            rows.append(dict(query_id=q,condition=condition,recall_at_3=value,precision_at_3=value,reciprocal_rank=value,hit_at_3=value))
    rows.append(dict(query_id='missing',condition='R0',recall_at_3=0))
    result=analyze_paired(rows,'E2')
    assert result['design']=='paired' and result['matched_by']=='query_id'
    assert result['metrics']['recall_at_3']['n_pairs']==2
    assert result['metrics']['recall_at_3']['pairs_missing_or_ineligible']==1
    assert result['metrics']['hit_at_3']['test']=='exact_McNemar'
    assert 'secondary_Holm_p' in result['metrics']['precision_at_3']
    with pytest.raises(ValueError,match='Unique'):
        analyze_paired(rows+[rows[0]],'E2')


@pytest.mark.parametrize('legacy,condition',[(True,'N0'),(True,'N1'),(False,'N0'),(False,'N1')])
def test_csv_to_observed_trajectory_pipeline_preserves_raw_and_latency(tmp_path,monkeypatch,legacy,condition):
    import csv,hashlib,sys
    from scripts.experiments.evaluate_navigation import main
    fields=['condition','scenario_id','success','expected_strategy','strategy_applied']
    if not legacy:fields.append('memory_latency_ms')
    raw=tmp_path/'raw.csv'
    with raw.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        row=dict(condition={'N0':'MEMORY_OFF','N1':'MEMORY_ON'}[condition],scenario_id='HOME_01',success='true',expected_strategy='direct',strategy_applied='false')
        if not legacy:row['memory_latency_ms']='123.456'
        writer.writerow(row)
    before=hashlib.sha256(raw.read_bytes()).hexdigest()
    trace=tmp_path/'trace.jsonl';points=[]
    anchors=[(2,-6),(0,-4),(4,-4)]
    for a,b in zip(anchors,anchors[1:]):
        for i in range(10):points.append((a[0]+(b[0]-a[0])*i/10,a[1]+(b[1]-a[1])*i/10))
    points.append(anchors[-1])
    trace.write_text(''.join(json.dumps(p)+'\n' for p in trajectory(points)))
    output=tmp_path/'processed.json'
    monkeypatch.setattr(sys,'argv',['evaluate_navigation','--ground-truth',str(GT/'navigation_ground_truth.json'),'--case-id','HOME_01','--condition',condition,'--result',str(raw),'--classification','SUCCESS','--trajectory',str(trace),'--trajectory-complete','--synthetic','--output',str(output)])
    main();result=json.loads(output.read_text())[0]
    assert result['context_compliance']==1 and result['strategy_observed']=='west'
    assert result['memory_latency_ms']==('123.456' if not legacy and condition=='N1' else 'N/A')
    assert hashlib.sha256(raw.read_bytes()).hexdigest()==before
    with pytest.raises(FileExistsError):main()


@pytest.mark.parametrize('binary',[False,True])
def test_zero_pairs_have_no_inference_or_observations(monkeypatch,binary):
    import scipy.stats
    from scripts.experiments.evaluation_core import compare_paired
    def forbidden(*args,**kwargs):raise AssertionError('No inference without enough pairs')
    monkeypatch.setattr(scipy.stats,'permutation_test',forbidden)
    monkeypatch.setattr(scipy.stats,'binomtest',forbidden)
    result=compare_paired([],[],binary=binary)
    assert result['n_pairs']==0 and result['p'] is None
    assert result['inferential_test_status']=='NO_EVALUABLE_PAIRS'
    assert result['observed_first']==result['observed_second']==result['observed_differences']==[]
    assert result['effect_second_minus_first'] is None
    assert result['paired_bootstrap_95_CI'] is None


@pytest.mark.parametrize('a,b,binary',[([2],[5],False),([2],[2],False),([0],[1],True),([1],[1],True)])
def test_single_pair_preserves_description_without_claiming_no_effect(monkeypatch,a,b,binary):
    import scipy.stats
    from scripts.experiments.evaluation_core import compare_paired
    def forbidden(*args,**kwargs):raise AssertionError('No inference with one pair')
    monkeypatch.setattr(scipy.stats,'permutation_test',forbidden)
    monkeypatch.setattr(scipy.stats,'binomtest',forbidden)
    result=compare_paired(a,b,binary=binary)
    assert result['n_pairs']==1 and result['p'] is None
    assert result['inferential_test_status']=='INSUFFICIENT_SAMPLE_FOR_INFERENCE'
    assert result['observed_first']==a and result['observed_second']==b
    assert result['observed_differences']==[b[0]-a[0]]
    assert result['effect_second_minus_first']==b[0]-a[0]
    assert result['paired_bootstrap_95_CI'] is None


def test_two_pairs_keep_planned_inference_and_zero_difference_is_distinct(monkeypatch):
    import scipy.stats
    from scripts.experiments.evaluation_core import compare_paired
    original=scipy.stats.permutation_test;calls=[]
    def counted(*args,**kwargs):
        calls.append(kwargs['permutation_type']);return original(*args,**kwargs)
    monkeypatch.setattr(scipy.stats,'permutation_test',counted)
    result=compare_paired([1,2],[3,4])
    assert calls==['samples'] and result['n_pairs']==2
    assert result['inferential_test_status']=='EVALUATED' and 0<=result['p']<=1
    no_difference=compare_paired([1,2],[1,2])
    insufficient=compare_paired([1],[1])
    assert no_difference['p']==1 and no_difference['inferential_test_status']=='EVALUATED'
    assert insufficient['p'] is None
    assert insufficient['inferential_test_status']!='EVALUATED'


def test_unavailable_paired_inference_is_not_fabricated_by_multiplicity():
    from scripts.experiments.evaluation_core import analyze_paired
    rows=[dict(query_id='synthetic',condition=c,recall_at_3=v,precision_at_3=v,reciprocal_rank=v,hit_at_3=v) for c,v in [('R0',0),('R1',1)]]
    metrics=analyze_paired(rows,'E2')['metrics']
    assert all(m['p'] is None and m['n_pairs']==1 for m in metrics.values())
    assert all(m.get('secondary_Holm_p') is None for m in metrics.values())
