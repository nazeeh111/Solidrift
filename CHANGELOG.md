# Changes

## 0.1.2

Recompute retained output signed integrals from mesh coordinates during stored-report verification. Reject inconsistent serialized output volumes, bind mirrored failure-signature fields to replayed inputs and checked outputs, and use recomputed values in failure tests. Compare native floating accumulation with a relative tolerance of `1e-9`, with no absolute floor. Includes scalar-corruption, mirror-field, small-scale and malformed-output regressions. The authentic native report still verifies; baseline, witness and undo geometry/scalar corruptions that passed older verification are now refused. Native analysis and recorded evidence remain unchanged.

## 0.1.1

Fix the Witness viewer with its reference overlay enabled and no selected vertex. The overlay has no operand side; an absent selection must not match that absent side. Version 0.1.0 can throw before drawing the output in that interaction. The regression exercises Witness, Repair and Undo rendering paths. Native analysis, coordinate patches and recorded geometry are unchanged.

## 0.1.0

First release: bounded native FLOAT-union omission analysis; topology-checked failure-preserving reduction; source-cluster ancestry; near-planar boundary interventions lifted to original inputs; conservative paired-surface comparison; actual input undo and native rerun; immutable original bytes; machine-readable reports, OBJ and coordinate patch exports; offline interactive 3D viewer; stored-evidence verifier.

Includes one licensed, reproduced Manifold regression case and explicit scope and conventional controls. No universal repair or minimality claim.
