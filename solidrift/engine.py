"""Bounded failure-preserving search. Native operations are injected explicitly."""
from collections import Counter
import copy
import math
import time
from .gate import check_exact
from .io import f32
from .numeric import check, cross, dot, sub, norm
from .reducer import MeshState, CollapseRejected, collapse, edges_by_length, link_condition, ancestry_check, failure_signature
from .surface import correspondence

LIMITS = [
    'Two explicitly triangulated, finite, single connected outward closed shells only; 256 vertices and triangles per input.',
    'One scoped failure family: FLOAT union signed volume follows operand A while omitting a larger operand B.',
    'Greedy local reduction and near-planar group interventions; no global minimum or generally successful repair guarantee.',
    'Stored-number rational guards are conservative software checks, not formally verified certificates.',
    'MANIFOLD is an independent solver comparator; paired-surface agreement does not prove the true union.',
    'Ancestry clusters cover original vertices; affine weights are approximate after binary32 rounding.',
]

class BudgetExhausted(RuntimeError):
    pass

class Budget:
    def __init__(self, max_queries=1500, max_seconds=120):
        self.max_queries = max_queries; self.max_seconds = max_seconds
        self.started = time.monotonic(); self.queries = 0; self.stages = Counter()
    def available(self, reserve=0, stage_limit=None, stage=None):
        return (self.queries + reserve < self.max_queries and
                time.monotonic()-self.started < self.max_seconds - 2 and
                (stage_limit is None or self.stages[stage] < stage_limit))
    def evaluate(self, pair, solver, backend, stage):
        if self.queries >= self.max_queries:
            raise BudgetExhausted('native_query_budget')
        if time.monotonic()-self.started >= self.max_seconds:
            raise BudgetExhausted('elapsed_time_budget')
        self.queries += 1; self.stages[stage] += 1
        return backend(pair, solver)
    def evidence(self):
        return {'max_native_queries': self.max_queries, 'max_seconds': self.max_seconds,
                'native_backend_queries': self.queries, 'queries_by_stage': dict(self.stages),
                'elapsed_seconds': time.monotonic()-self.started,
                'hard_process_timeout': 'CLI kills the worker process group at the requested wall-time limit.'}

def metrics(mesh):
    return check(mesh['vertices'], mesh['faces'])

def valid(mesh):
    return check_exact(mesh['vertices'], mesh['faces'])

def evaluate(pair, solver, backend, budget, stage):
    return budget.evaluate(pair, solver, backend, stage)

def reduce_pair(originals, baseline, backend, budget):
    current = [MeshState.original(m['name'], m) for m in originals]
    accepted, rejected = [], Counter()
    stage_start = budget.queries
    stage_limit = max(3, int((budget.max_queries-stage_start)*.68))
    current_metrics = [metrics(s.geometry()) for s in current]
    last = baseline['outputs']['FLOAT']
    exhaustion = None; search_exhausted = False
    while True:
        progress = False
        for side in ((0,1) if len(accepted)%2 == 0 else (1,0)):
            state = current[side]
            for edge in edges_by_length(state):
                if not link_condition(state.faces, edge):
                    rejected['link_condition'] += 1; continue
                for choice in ('midpoint','first','second'):
                    if not budget.available(reserve=7, stage_limit=stage_limit-2, stage='reduction'):
                        exhaustion = 'search_budget'; break
                    try:
                        candidate, preliminary = collapse(state, edge, choice)
                        if not valid(candidate.geometry())['valid']:
                            raise CollapseRejected('exact_input_guard')
                        states = current[:]; states[side] = candidate
                        inputs = current_metrics[:]; inputs[side] = preliminary
                        if inputs[1]['volume'] < 1.1*inputs[0]['volume']:
                            raise CollapseRejected('input_volume_ratio')
                        output = evaluate([s.geometry() for s in states], 'FLOAT', backend, budget, 'reduction')
                        signature = failure_signature(inputs, output)
                        if not signature['matches']:
                            raise CollapseRejected('failure_signature_changed')
                    except CollapseRejected as error:
                        rejected[str(error)] += 1; continue
                    # Unexpected/native failures deliberately propagate and fail
                    # this run. They are not interchangeable with this defect.
                    accepted.append({'step': len(accepted)+1, 'operand': side,
                        'operand_name': state.name, 'edge': list(edge), 'choice': choice,
                        'source_edge': [state.ancestry[i]['cluster'] for i in edge],
                        'vertex_before': [state.vertices[i] for i in edge],
                        'vertex_after': candidate.vertices[min(edge)],
                        'input_metrics': inputs, 'failure_signature': signature,
                        'native_query': budget.queries})
                    current, current_metrics, last = states, inputs, output
                    progress = True; break
                if progress or exhaustion: break
            if progress or exhaustion: break
        if exhaustion: break
        if not progress:
            search_exhausted = True; break
    pair = [s.geometry() for s in current]
    floated = evaluate(pair,'FLOAT',backend,budget,'reduction')
    reference = evaluate(pair,'MANIFOLD',backend,budget,'reduction')
    signature = failure_signature(current_metrics,floated)
    if not signature['matches']:
        raise RuntimeError('final repeated FLOAT query lost the original failure family')
    for s,o in zip(current,originals):
        ancestry_check(s,len(o['vertices']))
        if not valid(s.geometry())['valid']:
            raise RuntimeError('final witness failed exact input guard')
    return {'schema_version':1, 'method':'greedy_valid_oriented_edge_collapse',
        'original_operands':[MeshState.original(m['name'],m).geometry() for m in originals],
        'operands':pair, 'accepted_steps':accepted, 'rejected_counts':dict(rejected),
        'original_input_metrics':[metrics(m) for m in originals], 'final_input_metrics':current_metrics,
        'initial_failure_signature':failure_signature([metrics(m) for m in originals],baseline['outputs']['FLOAT']),
        'final_failure_signature':signature, 'native_backend_queries':budget.queries-stage_start,
        'search_exhausted':search_exhausted, 'budget_exhaustion':exhaustion,
        'final_outputs':{'FLOAT':floated,'MANIFOLD':reference},
        'claim_scope':'Bounded local search; exact stored-number validity guard, no global minimum or formal certificate.'}

def boundary_groups(mesh, span):
    groups = {}
    for fi,face in enumerate(mesh['faces']):
        a,b,c = [mesh['vertices'][i] for i in face]
        n = cross(sub(b,a),sub(c,a)); length = norm(n)
        if length == 0: continue
        n = tuple(x/length for x in n)
        ids = tuple(i for i,p in enumerate(mesh['vertices']) if abs(dot(n,sub(p,a))) <= span*1e-6)
        if 3 <= len(ids) < len(mesh['vertices']) and ids not in groups:
            groups[ids] = {'vertices':list(ids),'normal':list(n),'seed_face':fi}
    return list(groups.values())

def displaced(mesh, indices, delta):
    result = copy.deepcopy(mesh)
    for i in indices:
        result['vertices'][i] = [f32(x+y) for x,y in zip(result['vertices'][i],delta)]
    return result

def quality(pair, backend, budget, span):
    checks = [valid(m) for m in pair]
    if not all(x['valid'] for x in checks):
        return False, {'reason':'invalid_input'}
    if not all(metrics(m)['valid'] for m in pair):
        return False, {'reason':'numeric_input_prefilter'}
    floated = evaluate(pair,'FLOAT',backend,budget,'repair')
    fcheck = valid(floated)
    if not fcheck['valid']:
        return False, {'reason':'invalid_float_output'}
    reference = evaluate(pair,'MANIFOLD',backend,budget,'repair')
    rcheck = valid(reference)
    if not rcheck['valid']:
        return False, {'reason':'invalid_reference_output'}
    fm, rm = metrics(floated), metrics(reference)
    if abs(fm['volume']-rm['volume']) > max(abs(rm['volume']),1)*1e-5:
        return False, {'reason':'reference_volume_disagreement'}
    surface = correspondence(floated, reference, span*1e-6)
    if not surface['bijection'] or not surface['within_tolerance']:
        return False, {'reason':'reference_surface_disagreement','surface':surface}
    return True, {'reason':'agreement', 'output_geometry':floated,'reference_geometry':reference,
                  'output':fm,'reference':rm, 'exact_output':fcheck,'exact_reference':rcheck,
                  'surface_correspondence':surface}

def repair_pair(reduction, backend, budget):
    pair,originals = reduction['operands'],reduction['original_operands']
    span = max(max(v[k] for m in pair for v in m['vertices'])-min(v[k] for m in pair for v in m['vertices']) for k in range(3))
    full_span = max(max(v[k] for m in originals for v in m['vertices'])-min(v[k] for m in originals for v in m['vertices']) for k in range(3))
    groups = [boundary_groups(m,span) for m in pair]
    accepted, attempts = None, []
    start = budget.queries
    exhausted = False
    for scale in (1e-7,1e-6,1e-5,1e-4):
        for side,m in enumerate(pair):
            for group in groups[side]:
                for sign in (1,-1):
                    # Up to four native local/full comparisons and one undo,
                    # with reserve for any remaining mandatory checks.
                    if not budget.available(reserve=5):
                        exhausted=True; break
                    delta=[x*span*scale*sign for x in group['normal']]
                    changed=copy.deepcopy(pair); changed[side]=displaced(m,group['vertices'],delta)
                    okay,local=quality(changed,backend,budget,span)
                    trial={'side':side,'vertices':group['vertices'],'seed_face':group['seed_face'],
                           'delta':delta,'local_reason':local['reason']}
                    if okay:
                        cluster=sorted({i for vi in group['vertices'] for i in m['ancestry'][vi]['cluster']})
                        lifted=copy.deepcopy(originals);lifted[side]=displaced(originals[side],cluster,delta)
                        full_ok,full=quality(lifted,backend,budget,full_span)
                        trial['full_reason']=full['reason']
                        if full_ok:
                            patch=[{'vertex':i,'before':originals[side]['vertices'][i],
                                    'after':lifted[side]['vertices'][i]} for i in cluster]
                            restored=copy.deepcopy(lifted)
                            for change in patch:
                                if restored[side]['vertices'][change['vertex']] != change['after']:
                                    raise RuntimeError('patch precondition mismatch')
                                restored[side]['vertices'][change['vertex']]=list(change['before'])
                            if restored != originals:
                                raise RuntimeError('stored undo did not restore original imported geometry')
                            undo=evaluate(restored,'FLOAT',backend,budget,'repair')
                            undo_signature=failure_signature([metrics(x) for x in restored],undo)
                            if not undo_signature['matches']:
                                raise RuntimeError('actual undo query did not restore failure')
                            accepted={'intervention':trial,'cluster':cluster,'patch':patch,
                                'undo_inputs':restored,'witness_repaired':changed,'full_repaired':lifted,
                                'witness_check':local,'full_check':full,
                                'undo_signature':dict(undo_signature,geometry=undo),
                                'original_signature':reduction['initial_failure_signature'],
                                'witness_signature':reduction['final_failure_signature']}
                    attempts.append(trial)
                    if accepted:break
                if accepted or exhausted:break
            if accepted or exhausted:break
        if accepted or exhausted:break
    return {'accepted':accepted,'attempts':attempts,'groups':groups,
            'method':'nearplanar_boundary_group_translation_and_ancestry_lift',
            'backend_queries':budget.queries-start,'budget_exhausted':exhausted,
            'limits':'Native single-shell guards plus volume and oriented paired-surface comparator agreement. No generally successful repair or universal union proof.'}

def analyze(pair, backend, backend_identity, budget, publish):
    report={'schema_version':1,'status':'running','baseline':None,'reduction':None,'repair':None,'limits':LIMITS}
    for m in pair:
        guard=valid(m)
        if not guard['valid']:
            report.update(status='refused',reason='input guard refused '+m['name'],input_guard=guard)
            publish(report);return report
    baseline=dict(backend_identity,operation='UNION',inputs={m['name']:m for m in pair},outputs={})
    for solver in ('FLOAT','MANIFOLD'):
        baseline['outputs'][solver]=evaluate(pair,solver,backend,budget,'baseline')
    baseline['input_checks']=[valid(m) for m in pair]
    baseline['reference_check']=valid(baseline['outputs']['MANIFOLD'])
    baseline['failure_signature']=failure_signature([metrics(m) for m in pair],baseline['outputs']['FLOAT'])
    report['baseline']=baseline
    if not baseline['reference_check']['valid']:
        report.update(status='refused',reason='MANIFOLD comparator is outside the accepted single-shell domain')
        publish(report);return report
    if not baseline['failure_signature']['matches']:
        report.update(status='no_failure',reason='The selected missing-second-volume failure family was not reproduced; other defects are outside this scope.')
        publish(report);return report
    report['status']='witness';publish(report)
    reduction=reduce_pair(pair,baseline,backend,budget)
    report['reduction']=reduction;publish(report)
    repair=repair_pair(reduction,backend,budget)
    report['repair']=repair
    report['status']='repaired' if repair['accepted'] else 'witness'
    report['reason']='Validated reversible intervention found.' if repair['accepted'] else 'Failure preserved; bounded intervention search found no accepted repair.'
    publish(report);return report
