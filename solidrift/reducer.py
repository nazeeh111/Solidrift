"""Bounded native failure reduction by valid, oriented edge contraction.

Run with Blender's --background --python. Importing this module uses only the
standard library and the independent mesh validator, so its geometry and
ancestry rules can also be checked without starting Blender. This is a greedy
search over three contraction positions, not a global minimum or certificate.
"""
import argparse
from collections import Counter
from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct
import sys
import time

from .numeric import check, cross, dot, sub, norm
from .guard import check_exact


class CollapseRejected(ValueError):
    pass


def native_float(value):
    """Blender mesh coordinates use binary32; reject overflowing candidates."""
    try:
        result = struct.unpack('f', struct.pack('f', value))[0]
    except (OverflowError, struct.error):
        raise CollapseRejected('nonfinite_geometry')
    if not math.isfinite(result):
        raise CollapseRejected('nonfinite_geometry')
    return result


@dataclass
class MeshState:
    name: str
    vertices: list
    faces: list
    ancestry: list

    @classmethod
    def original(cls, name, data):
        return cls(name, [list(v) for v in data['vertices']],
                   [list(f) for f in data['faces']],
                   [{'weights': {i: 1.0}, 'cluster': [i]}
                    for i in range(len(data['vertices']))])

    def geometry(self):
        return dict(name=self.name, vertices=self.vertices, faces=self.faces,
                    ancestry=self.ancestry)


def vertex_link(faces, vertex):
    points, edges = set(), set()
    for face in faces:
        if vertex in face:
            other = [i for i in face if i != vertex]
            points.update(other)
            edges.add(tuple(sorted(other)))
    return points, edges


def link_condition(faces, edge):
    """The full simplicial link condition, including its edge simplices.

    Comparing only common neighbor vertices incorrectly permits contracting a
    tetrahedron edge: its two vertex links also share the opposite edge.
    """
    u, v = edge
    if u == v:
        return False
    incident = [f for f in faces if u in f and v in f]
    if len(incident) != 2:
        return False
    opposite = {i for f in incident for i in f if i not in edge}
    up, ue = vertex_link(faces, u)
    vp, ve = vertex_link(faces, v)
    return len(opposite) == 2 and up & vp == opposite and not (ue & ve)


def ancestry_check(state, original_count):
    if len(state.ancestry) != len(state.vertices):
        raise CollapseRejected('ancestry_bookkeeping')
    flattened = []
    for item in state.ancestry:
        cluster = item['cluster']
        weights = item['weights']
        if not cluster or len(cluster) != len(set(cluster)):
            raise CollapseRejected('ancestry_bookkeeping')
        if not weights or not set(weights).issubset(cluster):
            raise CollapseRejected('ancestry_bookkeeping')
        if any(not math.isfinite(w) or w <= 0 for w in weights.values()):
            raise CollapseRejected('ancestry_bookkeeping')
        if abs(math.fsum(weights.values()) - 1) > 1e-12:
            raise CollapseRejected('ancestry_bookkeeping')
        flattened.extend(cluster)
    if sorted(flattened) != list(range(original_count)):
        raise CollapseRejected('ancestry_bookkeeping')


def invalid_reason(metrics):
    for key in ('boundary_edges', 'nonmanifold_edges', 'inconsistent_edges',
                'bad_vertex_links', 'degenerate_faces', 'intersections'):
        if metrics[key]:
            return key
    if not math.isfinite(metrics['volume']) or metrics['volume'] <= 0:
        return 'nonpositive_volume'
    return None


def collapse(state, edge, choice, point=None):
    """Contract an existing edge, remove its two triangles, compact indices.

    Every surviving face retains its original winding, with a positive normal
    alignment guard before the independent closed-solid/intersection check.
    Endpoint choices retain affine support at that endpoint while their source
    cluster still records all vertices consumed by the contraction.
    """
    u, v = sorted(edge)
    if not link_condition(state.faces, (u, v)):
        raise CollapseRejected('link_condition')
    alpha = {'midpoint': .5, 'first': 0., 'second': 1.}[choice]
    position = point if point is not None else [
        (1-alpha)*a + alpha*b for a, b in zip(state.vertices[u], state.vertices[v])]
    position = [native_float(x) for x in position]
    vertices = [list(p) for p in state.vertices]
    vertices[u] = position
    span = max(max(p[k] for p in vertices)-min(p[k] for p in vertices)
               for k in range(3))
    area_epsilon = max(span*1e-9, 1e-12)**2
    faces = []
    face_keys = set()
    for old in state.faces:
        if u in old and v in old:
            continue
        face = [u if i == v else i for i in old]
        if len(set(face)) != 3:
            raise CollapseRejected('degenerate_faces')
        key = tuple(sorted(face))
        if key in face_keys:
            raise CollapseRejected('duplicate_faces')
        face_keys.add(key)
        before = [state.vertices[i] for i in old]
        after = [vertices[i] for i in face]
        old_normal = cross(sub(before[1], before[0]), sub(before[2], before[0]))
        new_normal = cross(sub(after[1], after[0]), sub(after[2], after[0]))
        if norm(new_normal) <= area_epsilon:
            raise CollapseRejected('degenerate_faces')
        if dot(old_normal, new_normal) <= 0:
            raise CollapseRejected('face_inversion')
        faces.append(face)
    # An affine combination of supports, plus the independent consumed cluster.
    weights = {}
    for amount, ancestry in ((1-alpha, state.ancestry[u]),
                             (alpha, state.ancestry[v])):
        for source, weight in ancestry['weights'].items():
            if amount:
                weights[source] = weights.get(source, 0.) + amount*weight
    merged = dict(weights=weights, cluster=sorted(
        set(state.ancestry[u]['cluster']) | set(state.ancestry[v]['cluster'])))
    ancestry = [dict(weights=dict(a['weights']), cluster=list(a['cluster']))
                for a in state.ancestry]
    ancestry[u] = merged
    del vertices[v]
    del ancestry[v]
    faces = [[i-1 if i > v else i for i in face] for face in faces]
    result = MeshState(state.name, vertices, faces, ancestry)
    ancestry_check(result, sum(len(a['cluster']) for a in state.ancestry))
    metrics = check(result.vertices, result.faces)
    reason = invalid_reason(metrics)
    if reason:
        raise CollapseRejected(reason)
    return result, metrics


def edges_by_length(state):
    edges = {tuple(sorted((a, b))) for f in state.faces
             for a, b in zip(f, f[1:]+f[:1])}
    return sorted(edges, key=lambda e: (dot(sub(state.vertices[e[0]], state.vertices[e[1]]),
                                            sub(state.vertices[e[0]], state.vertices[e[1]])), e))


def failure_signature(inputs, output):
    a, b = (m['volume'] for m in inputs)
    result = output['volume']
    largest = max(a, b)
    finite = all(math.isfinite(x) for x in (a, b, result))
    matches = finite and a > 0 and b >= 1.1*a and result > 0 and \
        abs(result-a) <= 1e-5*largest and result < .9*largest
    return dict(family='FLOAT_UNION_missing_second_operand_volume', matches=matches,
                input_a_volume=a, input_b_volume=b, output_volume=result,
                absolute_difference_from_a=abs(result-a), tolerance=1e-5*largest,
                b_to_a_ratio=b/a if a else None)

