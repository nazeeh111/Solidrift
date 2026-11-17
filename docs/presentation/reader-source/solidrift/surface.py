"""Conservative oriented correspondence bounds for two stored surfaces."""
from collections import Counter
from fractions import Fraction as Q
import math

def canonical(face):
    return min(tuple(face[i:]+face[:i]) for i in range(3))

def correspondence(a, b, tolerance=None):
    av, bv = a['vertices'], b['vertices']
    if not av or len(av) != len(bv):
        return {'bijection': False, 'reason': 'different or empty vertex counts'}
    mapping, distances = [], []
    for p in av:
        values = [sum((Q(x)-Q(y))**2 for x,y in zip(p,q)) for q in bv]
        best = min(values)
        candidates = [i for i,x in enumerate(values) if x == best]
        if len(candidates) != 1:
            return {'bijection': False, 'reason': 'nearest vertex ambiguous'}
        mapping.append(candidates[0]); distances.append(best)
    if len(set(mapping)) != len(mapping):
        return {'bijection': False, 'reason': 'nearest mapping not injective'}
    af = Counter(canonical([mapping[i] for i in f]) for f in a['faces'])
    bf = Counter(canonical(list(f)) for f in b['faces'])
    if af != bf:
        return {'bijection': False, 'reason': 'oriented triangulations differ'}
    squared = max(distances)
    bound = math.sqrt(float(squared))
    while Q(bound)**2 < squared:
        bound = math.nextafter(bound, math.inf)
    within = tolerance is None or squared <= Q(tolerance)**2
    return {'bijection': True, 'oriented_triangle_bijection': True,
            'vertex_mapping': mapping, 'max_vertex_squared_distance_exact': str(squared),
            'whole_paired_surface_distance_upper_bound': bound,
            'tolerance': tolerance, 'within_tolerance': within,
            'bound_reason': 'Matching oriented triangles use the same barycentric weights; every paired surface point is displaced by at most the maximum vertex displacement, in both directions.',
            'scope': 'This bounds agreement with a second solver, not the true union or a formally verified checker.'}
