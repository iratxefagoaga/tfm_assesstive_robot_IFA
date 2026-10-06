"""Isolated experimental evaluators; no production code or DB mutations."""
import csv
import json
import math
import statistics
from pathlib import Path


def load_ground_truth(path, kind, approved=False):
    data = json.loads(Path(path).read_text())
    if data.get('schema_version') != 1 or data.get('status') not in ('DRAFT', 'DRAFT_REVIEWED', 'FROZEN'):
        raise ValueError('Invalid schema/status')
    if approved and (data['status'] != 'FROZEN' or not data.get('review', {}).get('approved') or not data['review'].get('reviewer') or not data['review'].get('date')):
        raise ValueError('Human review required: ground truth remains DRAFT')
    id_key = 'query_id' if kind == 'E2' else 'case_id'
    ids = [case[id_key] for case in data['cases']]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Cases must be nonempty and unique')
    for case in data['cases']:
        if not case.get('rationale') or set(case['context']) != {'user_id', 'location', 'task', 'goal'}:
            raise ValueError('Explicit context and rationale required')
        if kind == 'E2' and (not case.get('relevant_memory_ids') or len(case['relevant_memory_ids']) != len(set(case['relevant_memory_ids']))):
            raise ValueError('Relevance judgements required')
        if kind in ('E1', 'E3') and case.get('ground_truth_strategy') not in ('west', 'direct', 'central', 'alternative'):
            raise ValueError('Invalid ground truth strategy')
        if kind == 'E1':
            geometry = case['route_geometry']
            if geometry['frame'] != 'map' or len(geometry['west_region']) != 4:
                raise ValueError('Independent map-frame geometry required')
        if kind == 'E2' and data['status'] != 'DRAFT':
            judgements = case.get('relevance_judgements', [])
            if len(judgements) != 50 or len({j['memory_id'] for j in judgements}) != 50:
                raise ValueError('All 50 memory judgements required')
            if {j['memory_id'] for j in judgements if j['relevant']} != set(case['relevant_memory_ids']):
                raise ValueError('Relevance list and individual judgements disagree')
        if kind == 'E3':
            groups = {g['evidence_group_id']: g for g in data.get('evidence_groups', [])}
            group = groups.get(case.get('evidence_group_id'))
            if not group or case.get('evidence_memory_ids') != group['evidence_memory_ids']:
                raise ValueError('Complete evidence group IDs required')
            if group['user_id'] != case['context']['user_id']:
                raise ValueError('Evidence groups must belong to the same user')
    return data


def route_classifier(samples, geometry, complete):
    """Classify map-frame geometry only; never consult labels or expected strategy."""
    if not complete or len(samples) < 2:
        return 'N/A'
    points = []
    for sample in samples:
        if sample.get('frame') != geometry['frame']:
            return 'N/A'
        try:
            p = tuple(float(sample[k]) for k in ('t', 'x', 'y'))
        except (KeyError, TypeError, ValueError):
            return 'N/A'
        if not all(math.isfinite(v) for v in p):
            return 'N/A'
        points.append(p)
    for a, b in zip(points, points[1:]):
        if not 0 < b[0] - a[0] <= geometry['max_gap_s'] or math.dist(a[1:], b[1:]) > geometry['max_segment_m']:
            return 'N/A'
    tol = geometry['endpoint_tolerance_m']
    if math.dist(points[0][1:], geometry['spawn']) > tol or math.dist(points[-1][1:], geometry['goal']) > tol:
        return 'N/A'
    def inside(p, box):
        xmin, xmax, ymin, ymax = box
        return xmin <= p[1] <= xmax and ymin <= p[2] <= ymax
    # Both criteria apply to an uninterrupted sequence of original samples.
    count = 0
    entered = None
    minimum = geometry.get('west_min_consecutive_samples', 3)
    dwell = geometry.get('west_min_dwell_s', 0.2)
    if minimum < 3 or dwell < 0.2:
        raise ValueError('West evidence thresholds cannot be weaker than reviewed defaults')
    for p in points:
        if inside(p, geometry['west_region']):
            count += 1
            if entered is None:
                entered = p[0]
            if count >= minimum and p[0] - entered + 1e-9 >= dwell:
                return 'west'
        else:
            count = 0
            entered = None
    if all(inside(p, geometry['direct_corridor']) for p in points):
        return 'direct'
    return 'N/A'  # Unclassified routes are not automatically direct.


def evaluate_navigation(case, result, samples):
    observed = route_classifier(samples, case['route_geometry'], result.get('trajectory_complete') is True)
    compliance = 'N/A' if observed == 'N/A' else int(observed == case['ground_truth_strategy'])
    return {**result, 'strategy_observed': observed, 'context_compliance': compliance,
            'min_clearance_m': 'N/A', 'intervention_appropriate': 'N/A',
            'memory_latency_ms': 'N/A' if result['memory_condition'] == 'N0' else result.get('memory_latency_ms', 'N/A')}


def retrieval_metrics(retrieved, relevant, k=3):
    if not relevant or len(retrieved) != len(set(retrieved)) or k < 1:
        raise ValueError('Nonempty relevance, unique rankings and positive k required')
    relevant = set(relevant)
    top = retrieved[:k]
    hits = sum(mid in relevant for mid in top)
    rr = next((1 / rank for rank, mid in enumerate(retrieved, 1) if mid in relevant), 0.0)
    return {'hits_at_3': hits, 'precision_at_3': hits / k, 'recall_at_3': hits / len(relevant),
            'reciprocal_rank': rr, 'hit_at_3': int(hits > 0)}


def read_only_service(service):
    """Require PostgreSQL transaction defaults; never call store_memory."""
    from sqlalchemy import text
    with service.engine.connect() as connection:
        if connection.execute(text('SHOW default_transaction_read_only')).scalar() != 'on':
            raise ValueError('DB read-only mode required before evaluation')
    return service


def retrieve_condition(service, case, method):
    if method == 'R0':
        # With no context, production final score is 0.90 * cosine; same ordering.
        return service.retrieve_memories(query=case['query'], user_id=None,
                                        location=None, task=None, goal=None, k=50)
    if method == 'R1':
        return service.retrieve_memories(query=case['query'], **case['context'], k=50)
    raise ValueError('Unknown method')


def episodic_condition(ranked, excluded_ids, condition):
    if condition not in ('P0', 'P1'):
        raise ValueError('Unknown condition')
    excluded = set(excluded_ids) if condition == 'P0' else set()
    return [dict(row) for row in ranked if row['memory_id'] not in excluded][:3]


def recommend(ranked):
    # Reuse the exact production recommendation method without a ROS node/service.
    from types import SimpleNamespace
    from wheelchair_memory.navigation_memory_node import NavigationMemoryNode
    response = SimpleNamespace(success=True, message='', memory_ids=[m['memory_id'] for m in ranked])
    for attr, field in [('actions','action'),('preferences','preference'),('observations','observation'),
                        ('outcomes','outcome'),('semantic_scores','semantic_similarity'),
                        ('context_scores','context_score'),('final_scores','final_score')]:
        setattr(response, attr, [m[field] for m in ranked])
    return NavigationMemoryNode.build_navigation_recommendation(None, response)


def evaluate_e3(case, ranked, condition, recommendation_fn=recommend):
    if 'ABLATION_CONTAMINATED' in case.get('flags', []):
        raise ValueError('ABLATION_CONTAMINATED: human review required before evaluation')
    evidence = case['evidence_memory_ids']
    selected = episodic_condition(ranked, evidence, condition)
    answer = recommendation_fn(selected)
    strategy = answer.get('strategy') if answer.get('success') else None
    source = answer.get('source_memory', answer.get('memory_id'))
    correct = int(strategy == case['ground_truth_strategy']) if strategy else 'N/A'
    primary_eligible = case.get('primary_eligible', True) and 'DEFAULT_SENSITIVE' not in case.get('flags', [])
    source_row = next((m for m in selected if m['memory_id'] == source), {})
    explicit_direct = 'ruta directa' in source_row.get('action', '').lower()
    return {'case_id': case['case_id'], 'method': condition, 'condition': condition,
            'evidence_group_id': case.get('evidence_group_id', 'SYNTHETIC'),
            'excluded_ids': list(evidence) if condition == 'P0' else [],
            'strategy': strategy or 'N/A', 'strategy_correct': correct,
            'strategy_accuracy': correct if primary_eligible else 'N/A',
            'primary_eligible': primary_eligible, 'flags': list(case.get('flags', [])),
            'source_memory': source or 'N/A', 'source_explicit_direct': explicit_direct,
            'evaluable_coverage': int(bool(strategy)),
            'relevant_memory_used': int(source in evidence) if source else 'N/A',
            'memory_hit': int(any(m['memory_id'] in evidence for m in selected)),
            'ranked_ids': [m['memory_id'] for m in selected]}


def write_new(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', newline='') as stream:
        if not rows:
            stream.write('[]\n')
        elif path.suffix == '.csv':
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        else:
            json.dump(rows, stream, indent=2)
            stream.write('\n')


def descriptive(values):
    vals = [float(v) for v in values if v not in ('N/A', '', None)]
    if not vals:
        return {'n': 0, 'mean': None, 'std': None, 'median': None, 'IQR': None}
    if not all(math.isfinite(v) for v in vals):
        raise ValueError('Nonfinite metric values are invalid, not missing observations')
    vals.sort()
    def quantile(p):
        pos = (len(vals) - 1) * p
        lo = int(pos)
        hi = math.ceil(pos)
        return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)
    return {'n': len(vals), 'mean': statistics.mean(vals),
            'std': statistics.stdev(vals) if len(vals) > 1 else None,
            'median': statistics.median(vals), 'IQR': quantile(.75) - quantile(.25)}


def compare_independent(a, b):
    from scipy.stats import mannwhitneyu, PermutationMethod
    if not a or not b:
        return {'status': 'NOT_EVALUABLE'}
    test = mannwhitneyu(a, b, alternative='two-sided', method=PermutationMethod(n_resamples=9999, random_state=20261004))
    delta = sum((x > y) - (x < y) for x in a for y in b) / (len(a) * len(b))
    return {'U': float(test.statistic), 'p': float(test.pvalue), 'cliffs_delta_N1_minus_N0': delta}


def binary_summary(values):
    vals = [float(v) for v in values if v not in ('N/A', '', None)]
    if any(v not in (0,1) for v in vals):
        raise ValueError('Binary values required')
    return {'n': len(vals), 'count': int(sum(vals)), 'percentage': 100 * sum(vals)/len(vals) if vals else None}


def compare_paired(a, b, binary=False):
    """Matched arrays, effect b-minus-a; missing pairs are reported by caller."""
    import numpy as np
    from scipy.stats import binomtest, permutation_test
    if len(a) != len(b):
        raise ValueError('Matched pairs required')
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise ValueError('Finite paired values required')
    if binary and not (np.isin(x, [0,1]).all() and np.isin(y, [0,1]).all()):
        raise ValueError('Binary paired values required')
    difference = y-x
    if len(a) < 2:
        return {'status': 'NOT_EVALUABLE' if not a else 'INSUFFICIENT_SAMPLE_FOR_INFERENCE',
                'inferential_test_status': 'NO_EVALUABLE_PAIRS' if not a else 'INSUFFICIENT_SAMPLE_FOR_INFERENCE',
                'n_pairs': len(a), 'observed_first': x.tolist(), 'observed_second': y.tolist(),
                'observed_differences': difference.tolist(),
                'effect_second_minus_first': float(difference.mean()) if len(a) else None,
                'paired_bootstrap_95_CI': None, 'p': None}
    rng = np.random.default_rng(20261005)
    boot = difference[rng.integers(0, len(a), (9999, len(a)))].mean(axis=1)
    result = {'inferential_test_status': 'EVALUATED', 'n_pairs': len(a), 'effect_second_minus_first': float(difference.mean()),
              'paired_bootstrap_95_CI': [float(v) for v in np.quantile(boot, [.025, .975])],
              'CI_scope': 'Empirical case collection; small-sample descriptive uncertainty.'}
    if binary:
        if not (np.isin(x, [0,1]).all() and np.isin(y, [0,1]).all()):
            raise ValueError('Binary paired values required')
        gained = int(((x == 0) & (y == 1)).sum())
        lost = int(((x == 1) & (y == 0)).sum())
        result.update(test='exact_McNemar', gains=gained, losses=lost,
                      p=float(binomtest(gained, gained+lost, .5).pvalue) if gained+lost else 1.0)
    else:
        if not np.any(difference):
            pvalue = 1.0
        else:
            test = permutation_test((x,y), lambda a,b,axis: np.mean(b-a,axis=axis),
                                    permutation_type='samples', vectorized=True,
                                    n_resamples=9999, alternative='two-sided', random_state=20261005)
            pvalue = float(test.pvalue)
        result.update(test='paired_sign_flip_permutation', p=pvalue)
    return result


def holm_adjust(pvalues):
    """Preserve metric names, monotone step-down adjustment of the declared family."""
    ordered = sorted(pvalues, key=pvalues.get)
    adjusted, previous = {}, 0.0
    for i, name in enumerate(ordered):
        previous = max(previous, min(1.0, (len(ordered)-i)*pvalues[name]))
        adjusted[name] = previous
    return adjusted


def analyze_paired(rows, kind):
    if kind not in ('E2', 'E3'):
        raise ValueError('Paired analysis is only E2/E3')
    identity = 'query_id' if kind == 'E2' else 'case_id'
    conditions = ('R0','R1') if kind == 'E2' else ('P0','P1')
    metrics = ({'recall_at_3': False, 'precision_at_3': False, 'reciprocal_rank': False, 'hit_at_3': True}
               if kind == 'E2' else {'strategy_accuracy': True, 'relevant_memory_used': True,
                                    'memory_hit': True, 'latency_ms': False, 'evaluable_coverage': True})
    pairs = {}
    for row in rows:
        key = row[identity]
        condition = row.get('condition', row.get('method'))
        if condition not in conditions or condition in pairs.setdefault(key, {}):
            raise ValueError('Unique declared conditions per matched case required')
        pairs[key][condition] = row
    results = {}
    primary = 'recall_at_3' if kind == 'E2' else 'strategy_accuracy'
    for metric, binary in metrics.items():
        a, b = [], []
        for pair in pairs.values():
            if not all(c in pair and pair[c].get(metric) not in (None,'N/A','') for c in conditions):
                continue
            if kind == 'E3' and metric == primary and not all(pair[c].get('primary_eligible', True) for c in conditions):
                continue
            a.append(float(pair[conditions[0]][metric])); b.append(float(pair[conditions[1]][metric]))
        result = compare_paired(a,b,binary=binary)
        result['pairs_missing_or_ineligible'] = len(pairs)-len(a)
        result['descriptives'] = {c:(binary_summary(v) if binary else descriptive(v)) for c,v in zip(conditions,(a,b))}
        results[metric] = result
    # Keep the declared family size conservatively; unavailable inference stays null in output.
    adjusted = holm_adjust({m:v['p'] if v.get('p') is not None else 1.0 for m,v in results.items() if m != primary})
    for metric,pvalue in adjusted.items():
        results[metric]['secondary_Holm_p'] = pvalue if results[metric].get('p') is not None else None
    return {'design': 'paired', 'matched_by': identity, 'conditions': list(conditions),
            'primary': primary, 'cases_total': len(pairs), 'metrics': results}
