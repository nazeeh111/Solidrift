# Contributing

Useful contributions include reproducible small Boolean failures, improvements to the conservative geometry checks, alternate failure detectors with explicit contracts, and accessibility improvements to the report viewer.

Include your Blender version/build, two licensed input meshes, the exact command and the report. Keep source provenance. Do not upload confidential geometry. A claim that a repair works should include a native rerun on the full inputs and an undo check, rather than only a screenshot or volume match.

Run `python -m unittest discover -s tests` for the Python checks. Native tests require an explicitly selected Blender installation; no installer runs automatically. The current supported detector and single-shell restrictions are deliberate. A new failure family needs its own valid-input and semantic controls.

AI-assisted work is welcome when disclosed and understood by the contributor. Do not invent human approval, omit third-party licenses or claim formal verification from tests. The maintainer reviews changes before integration.
