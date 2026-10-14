# From failure to reversible intervention

The ordinary Python launcher parses two bounded triangular OBJ files, creates a new output directory, preserves source bytes, and starts a fresh Blender process using factory settings. Input is mesh data, never imported Python or a user scene. No remote computation or dependency download occurs.

Inside Blender, the worker imports binary32 coordinates and compares the actual import with the requested arrays. Each operand must pass the conservative single-shell guard. It evaluates FLOAT and MANIFOLD, retaining exported mesh arrays and the backend identity.

The supported failure signature is a gross union omission: B's signed integral is at least 1.1 times A's, the positive FLOAT result is within `1e-5 * max(A,B)` of A, and it is below `0.9 * max(A,B)`. For malformed output surfaces these are signed surface integrals, not certified physical volumes. A matching scalar signature is a detector, not a general geometric equivalence proof.

The reducer contracts existing edges using the full simplicial link condition, including edge simplices. It tries midpoint and endpoint positions, guards winding and degenerate faces, rounds candidates to native coordinates, checks actual solid validity, and calls the native solver again. Only a candidate preserving the declared failure is accepted. Source clusters partition the original vertices; weighted supports describe contraction history, with an explicit rounding qualification.

The repair search identifies near-planar boundary groups in the witness and tries small translations along their normals. A promising change must pass on the witness and again after lifting the same translation to the original vertices consumed by those witness vertices. Both output solvers must pass solid validity and volume comparison. A unique vertex mapping and matching oriented triangle multiset provide a conservative bound between their exported surfaces. Unsupported correspondence is refused, never replaced by volume-only approval.

The patch stores actual full-input before/after coordinate triples. Undo checks the expected after-state, restores the before-state and runs the native failure test again. No original source file is overwritten.

The report viewer operates on stored JSON. It reconstructs accepted input states, draws actual exported meshes, and displays source clusters. It runs no native geometry backend and makes no fresh solidity claim just because a report opens. Its offline export uses inline assets and escaped embedded JSON. Mesh and report exports are data.

Single connected outward shells are supported. Nested shells, cavities, general OBJ polygon triangulation, arbitrary failure predicates and alternate-remeshing surface comparison are outside this release. Input size and backend budgets keep the intended small-reproducer workflow bounded.
