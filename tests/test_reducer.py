"""Geometry and provenance checks requiring neither Blender nor dependencies."""
import unittest

from solidrift.reducer import (MeshState, CollapseRejected, collapse,
                            ancestry_check, link_condition, failure_signature,
                            native_float)
from solidrift.numeric import check


def octahedron():
    vertices = [[1.,0.,0.], [-1.,0.,0.], [0.,1.,0.], [0.,-1.,0.],
                [0.,0.,1.], [0.,0.,-1.]]
    faces = [[0,2,4], [2,1,4], [1,3,4], [3,0,4],
             [2,0,5], [1,2,5], [3,1,5], [0,3,5]]
    return MeshState.original('test_octahedron', dict(vertices=vertices, faces=faces))


class TopologyAndAncestry(unittest.TestCase):
    def test_closed_octahedron_contraction_preserves_sphere(self):
        state = octahedron()
        self.assertTrue(check(state.vertices, state.faces)['valid'])
        candidate, metrics = collapse(state, (0,2), 'midpoint')
        self.assertTrue(metrics['valid'])
        self.assertEqual((len(candidate.vertices), len(candidate.faces)), (5,6))
        edges = {tuple(sorted((a,b))) for f in candidate.faces
                 for a,b in zip(f,f[1:]+f[:1])}
        self.assertEqual(len(candidate.vertices)-len(edges)+len(candidate.faces), 2)
        self.assertEqual(candidate.ancestry[0],
                         dict(weights={0:.5,2:.5}, cluster=[0,2]))
        ancestry_check(candidate, 6)
        # Do not mutate the predecessor; it remains a recovery/replay state.
        self.assertEqual(state.vertices[0], [1.,0.,0.])
        self.assertEqual(state.ancestry[0], dict(weights={0:1.}, cluster=[0]))

    def test_tetrahedron_full_link_rejects_opposite_edge(self):
        faces = [[0,2,1], [0,1,3], [1,2,3], [2,0,3]]
        # The two common neighbors alone look admissible, but their common
        # link edge would collapse the tetrahedral shell into duplicate faces.
        self.assertFalse(link_condition(faces, (0,1)))

    def test_boundary_and_absent_edges_are_rejected(self):
        state = octahedron()
        state.faces.pop(0)
        self.assertFalse(link_condition(state.faces, (0,2)))
        with self.assertRaisesRegex(CollapseRejected, 'link_condition'):
            collapse(state, (0,2), 'midpoint')
        self.assertFalse(link_condition(octahedron().faces, (0,1)))

    def test_endpoint_weights_keep_consumed_cluster(self):
        candidate, _ = collapse(octahedron(), (0,2), 'first')
        self.assertEqual(candidate.ancestry[0],
                         dict(weights={0:1.}, cluster=[0,2]))
        self.assertEqual(candidate.vertices[0], [1.,0.,0.])
        ancestry_check(candidate, 6)

    def test_compaction_keeps_all_sources_once(self):
        candidate, _ = collapse(octahedron(), (0,2), 'second')
        self.assertEqual(candidate.ancestry[0]['weights'], {2:1.})
        self.assertEqual(candidate.ancestry[2]['cluster'], [3])
        candidate.ancestry[2]['cluster'] = [2]
        with self.assertRaisesRegex(CollapseRejected, 'ancestry_bookkeeping'):
            ancestry_check(candidate, 6)

    def test_degenerate_and_inverted_positions_rejected(self):
        with self.assertRaisesRegex(CollapseRejected, 'degenerate_faces'):
            collapse(octahedron(), (0,2), 'midpoint', point=[0.,0.,1.])
        with self.assertRaisesRegex(CollapseRejected, 'face_inversion'):
            collapse(octahedron(), (0,2), 'midpoint', point=[-20.,-20.,0.])
        with self.assertRaisesRegex(CollapseRejected, 'nonfinite_geometry'):
            collapse(octahedron(), (0,2), 'midpoint', point=[float('inf'),0.,0.])

    def test_float32_import_rounding_is_explicit(self):
        self.assertEqual(native_float(1.+2**-25), 1.)
        with self.assertRaises(CollapseRejected):
            native_float(1e100)

    def test_signature_rejects_union_success_and_changed_family(self):
        inputs = [{'volume':10.}, {'volume':15.}]
        self.assertTrue(failure_signature(inputs, {'volume':10.})['matches'])
        self.assertFalse(failure_signature(inputs, {'volume':24.})['matches'])
        self.assertFalse(failure_signature(inputs, {'volume':7.})['matches'])
        self.assertFalse(failure_signature([{'volume':15.}, {'volume':10.}],
                                           {'volume':15.})['matches'])
        self.assertFalse(failure_signature(inputs, {'volume':float('nan')})['matches'])


if __name__ == '__main__':
    unittest.main()
