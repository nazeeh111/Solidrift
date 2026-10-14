# Recorded native compatibility case

`native-report.json` is the authentic public Solidrift demo report from the original395-query run on Blender5.3 Alpha bad8871dc58d. It contains stored geometry and schema1 metadata; testing it does not execute Blender or authenticate its provenance. The assertion checks compatibility with the real report, including predecessor signatures that have no separate geometry field.

Original geometry is independently authored Manifold Offset3/Offset4 regression data at761661c15bacb6c8459d682c715de84591d51774, with Apache-2.0 license retained in `solidrift/fixtures/LICENSE` and provenance in the report and root NOTICE. The generated meshes are derived from those inputs. These are not original models authored by Solidrift.
