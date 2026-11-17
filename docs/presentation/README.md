# Carry the missing-region failure into Blender

This complete worked example was produced with Solidrift main `66bf422806891121d1fed7e5f08e7fa8aa89d3df`, version 0.1.2, and installed Blender **5.2.1 LTS**, build **9e2066aef7ef**. It complements the older 5.3 Alpha and 5.1.2 records without replacing them. It makes no claim about arbitrary Blender versions or arbitrary Boolean failures.

Extract `solidrift-native-reader.zip` into an empty directory. No Python dependency is needed to verify its recorded evidence:

```sh
python3 -B reopen.py
```

This verifies every content member's bytes, then runs the exact pinned Solidrift verifier from `reader-source`. It checks preserved source bytes, stored-coordinate guards, all 60 accepted input contractions, ancestry, the lifted patch, exact input undo and paired-surface bounds. It does not rerun Blender, authenticate the report's author or prove ideal union correctness. Native reruns are separate below. `reader-source` is an exact source snapshot with its original MIT notice and Apache-2.0 Manifold fixtures, not an independently implemented validator.

## Inspect the actual result

Open [case/report.html](case/report.html) in your browser. It is the actual self-contained CLI export, with its companion [favicon](case/favicon.svg), and works offline. Original, Witness, Repair and Undo select stored native states. The range input replays accepted **input** states; intermediate native output surfaces were not retained and are explicitly unavailable. Use the witness ancestry controls, orbit by dragging or arrow keys, and press R to reset. Downloaded JSON can be reopened through Open report. A malformed trace is refused while the previous valid report stays displayed.

The **[native scene](native/inspection.blend)** stores eight mesh objects, with raw mesh coordinates exactly matching original and reduced A, B, FLOAT and MANIFOLD meshes in the [full report](case/report.json). Its native [Blender Workbench render](native/native-inspection.png) is a supplementary inspection sheet, not an application screenshot. In the sheet, the upper row is original and lower row reduced; columns are inputs, FLOAT, MANIFOLD. A and B are teal and blue; the comparator column is yellow. Object translations separate the sheet panels and are recorded in `display_offset_only`; the underlying mesh coordinates are untouched. Units are **abstract model units**, not metres, millimetres or measured manufacturing dimensions.

The main [wide projection](witness.html) and [narrow projection](witness-mobile.html) use the same orthonormal camera basis and model-unit scale across all four panels within each composition. Their actual data, basis, centre, pixel scales and every polygon coordinate are in [projection.json](projection.json); all faces are shown as depth-sorted translucent x-ray surfaces. Yellow wire is the native MANIFOLD comparison, not an ideal-union construction. The PNGs are actual Chrome renders of the editable SVGs. No native intermediate surface is interpolated or invented.

## Reopen natively and repeat four decisive checks

Use your explicit compatible Blender executable. These commands use only a new process and the included public-source snapshot, with factory settings and automatic scripts disabled. They do not change global Blender preferences:

```sh
/path/to/blender --background --factory-startup --disable-autoexec \
  --python-exit-code 1 --python native-scene.py -- reader-source native reopen
```

This reopens `native/inspection.blend`, checks all eight mesh-coordinate/face identities and both witness OBJ exports, then evaluates four fresh FLOAT unions: original, reduced witness, repaired full inputs and restored full inputs. Expected failure-family flags are **true, true, false, true**. [native/reopened.json](native/reopened.json) is the author-run result. Reopen writes this one diagnostic file in your extracted copy. It does not repeat the 395-query search or claim those four queries prove every earlier backend step.

To construct an additional inspection scene rather than overwrite the bundled one, use a new directory:

```sh
/path/to/blender --background --factory-startup --disable-autoexec \
  --python-exit-code 1 --python native-scene.py -- reader-source NEW_NATIVE_DIRECTORY build
```

That route repeats the same four queries, writes fresh OBJ/native/PNG outputs, and refuses an existing directory. Native `.blend` serialization and render bytes can differ across runs or versions; matching scientific geometry and declared build are the criteria, not new `.blend` file hashes.

For the full current-source search, use the repository README's `python -m solidrift demo --blender /path/to/blender --out NEW_CASE` route. This run used default 1500-query/120-second outer limits; it used 395 queries, accepted 60 contractions, and completed in 17.372 seconds on this Mac. This single observed runtime is not a benchmark or promised speed. The two-query healthy fixture returned `no_failure`; an existing output and invalid query budget were refused before overwriting state. [controls.json](controls.json) records those checks.

## What the intervention means

Three witness vertices map to thirteen original A vertices through the stored ancestry clusters. [case/patch.json](case/patch.json) records exact before/after binary32 coordinates. B and all face indices stay unchanged. Full repaired FLOAT/MANIFOLD surfaces have an oriented triangle bijection and paired-point separation upper bound `4.2716200035021115e-6`, within the declared `6.5e-5` model-unit tolerance. This is comparator agreement, not error relative to the ideal Boolean union. Undo restores exact original input coordinates, not a promise of bit-identical native output serialization.

The detector is specific to FLOAT union signed integral following A while omitting a larger B. The original failed surface has degeneracy/intersection problems: its signed integral is not certified solid volume. Guards and reduction are conservative software, not formally verified; the search is greedy and budgeted. Valid alternative triangulations can be refused. The input intervention does not fix Blender. Every original source, input license, raw stage report, mesh export and recorded result is included rather than inferred from the pictures.

The fixtures are upstream Manifold regression data at `761661c15bacb6c8459d682c715de84591d51774`, Apache-2.0, with [complete original license/provenance](case/originals/FIXTURE_LICENSE). Solidrift's implementation and exact pinned replay source retain their MIT notice. The historical evidence, source architecture and original tour remain in the main repository.
