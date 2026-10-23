# Evidence and scope

The public demo is a recorded native run of the release-candidate engine, not a browser simulation. Download its [complete evidence bundle](https://nazeeh111.github.io/Solidrift/demo/evidence.zip), extract it, and run:

```sh
python -m solidrift verify /path/to/extracted/report.json
```

That command checks stored original bytes, input conversion, operand validity, all accepted contractions, source clusters, the lifted patch, exact input undo and the paired-surface bound. It **does not rerun Blender**, authenticate the report's author or prove ideal union correctness. `demo --blender ... --out NEW_DIRECTORY` performs the fresh native search. Results can vary with Blender builds.

From version 0.1.2, retained output signed integrals are recomputed using exact rational arithmetic on stored coordinates and compared with serialized native volumes at relative tolerance `1e-9`, without an absolute floor. Failure tests use the recomputed values. Intermediate per-contraction output surfaces were not retained, so those steps' output-volume observations remain recorded native claims; replay independently checks their input geometry and internally consistent predicate values, not a fresh backend query. A consistent report is not authenticated evidence of who ran Blender.

## Source and native run

The unchanged fixtures come from [Manifold](https://github.com/elalish/manifold/tree/761661c15bacb6c8459d682c715de84591d51774/test/models), revision `761661c15bacb6c8459d682c715de84591d51774`. The upstream [OffsetSelfIntersect regression](https://github.com/elalish/manifold/blob/761661c15bacb6c8459d682c715de84591d51774/test/boolean_complex_test.cpp#L1541) combines them by union. Apache-2.0 license and source identities are included in the bundle and [NOTICE](../NOTICE).

| Input | Bytes | SHA256 |
|---|---:|---|
| Offset3.obj | 2242 | `ca13ac6d4154725116886999d576ce22c164e55a3fccb645ef71e17b0871e8a6` |
| Offset4.obj | 2760 | `c894fd2ca43a8cc0ce259cc2473c7062efc59dd7217603a91c1b7d897e0264c3` |

Blender `5.3.0 Alpha`, build `bad8871dc58d`, factory-startup process. Decimal OBJ coordinates become Python binary64 and then native binary32. Vertex/triangle order is preserved; maximum coordinate conversion delta is about `1.796e-6`. Exact source bytes remain unchanged.

The release-candidate CLI run completed in **11.207 seconds** including process startup, with **395 actual native Boolean queries**: 2 baseline, 329 reduction and 64 repair. This is an observed small-case runtime, not a general benchmark or a promised speed.

Original A: 30 vertices/56 triangles, signed volume approximately `10803.4722`. B: 40/76, approximately `15240.5823`. FLOAT's exported signed integral is approximately `10803.4722`, while MANIFOLD's is `24655.8312`. Original FLOAT's surface has degeneracy/intersection failures, so its integral is not a certified solid volume. Point `(0,40,10)` lies inside B, outside A/FLOAT and inside MANIFOLD under three independent unambiguous rational ray directions. This supports an actual missing-region defect rather than a triangle-count difference.

The 60 accepted contractions reduce both inputs to triangular bipyramids: 5 vertices/6 triangles each, 10/12 total. Every accepted operand state passes the conservative closed, oriented, single-shell guard. Independent replay covers all 120 per-step operand states. Point `(0,35,5)` is inside reduced B and MANIFOLD but outside reduced A/FLOAT. The semantic omission survives, although the malformed triangles of the original failed output disappear. This is one declared failure family, not preservation of every original artifact detail.

## Lifted repair and independent rerun

The accepted boundary translation changes witness A vertices `[1,2,4]`. Their source clusters select 13 original A vertices:

```text
4,6,10,11,12,13,14,19,21,25,27,28,29
delta = [0, 0.00018747975765806915, 0.0006093091091297353]
```

Actual maximum displacement after native rounding: `0.0006374205319770713` model units. Operand B and every face remain unchanged. The patch stores actual before/after coordinates, rather than pretending weighted ancestry is exact after repeated binary32 rounding.

A separate reviewer ran one fresh Blender process with ten native queries: FLOAT/MANIFOLD for original full, original witness, repaired full, repaired witness and undo. It checked the stored exports against fresh oriented coordinate-triangle multisets. The original and undo surfaces agree exactly as geometry; vertex numbering may change. Both repaired input pairs and all repaired exports pass the independent guard.

| Repaired outputs | Oriented triangle correspondence | Maximum paired surface separation |
|---|---|---:|
| Full | 89 vertices / 174 triangles | `4.2716200035021115e-6` |
| Witness | 24 vertices / 44 triangles | `5.415829034614825e-6` |

Each corresponding triangle maps points using the same nonnegative barycentric weights. The triangle inequality bounds the distance by the largest corresponding vertex displacement, in both directions. The stored bound is rounded upward using exact squared distances. This is a bound **between the exported solver surfaces**, not between either solver and an ideal union.

The independent reviewer also used 222 finite membership probes for each stage. Original FLOAT disagreed with input A-or-B membership at 14 full-case probes and 5 witness probes. Both repaired solvers disagreed at zero probes. These are finite controls, not an all-points proof.

## Conventional comparisons

A separate fresh Blender process tested a fixed 12-case ordinary Decimate COLLAPSE sweep and two generic triangle-deletion controls. Eleven Decimate input pairs passed the independent solid guard, including three pairs with exactly 12 triangles and valid pairs with 8 and 10 triangles. None retained the missing-B predicate. The deletion controls failed closed-solid validity after removing unused vertices. This is a scoped fixed sweep, not all simplification configurations or a claim that their output unions were universally correct.

Switching the unchanged originals to MANIFOLD produced a valid result with all 132 input triangles. That is an effective workaround here. Solidrift serves a different workflow: a valid small witness, source ancestry and an input intervention tested on the full case, with undo.

## Prior work and boundaries

Topology-preserving edge contraction and delta debugging are established techniques. See [CGAL surface simplification](https://doc.cgal.org/Manual/4.2/doc_html/cgal_manual/Surface_mesh_simplification/Chapter_main.html), [Picire](https://github.com/renatahodovan/picire) and [GReduce](https://arxiv.org/abs/2402.04623). Manifold is an established robust Boolean alternative. Solidrift does not claim to invent those algorithms or to be the first geometry reducer. Its demonstrated workflow combines native same-failure reduction, source clusters, conservative output comparison and a full-model reversible intervention.

Only two bounded triangular single connected outward shells are supported. No cavities or disconnected-shell containment. The exact-number guard has controls and independent review, but no formal proof. The reducer is greedy; no global minimum. Repair search is finite and may find nothing. Equivalent surfaces with different triangulations can be refused. One solver call can exceed an inter-query search budget; the launcher enforces a separate process timeout. No cross-version backend support, general solver correctness, engineering tolerances, manufacturing suitability, downstream adoption or upstream acceptance is established by this one case.
