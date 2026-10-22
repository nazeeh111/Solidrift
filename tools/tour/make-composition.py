"""Build an editable Hyperframes film from report-backed geometry plates."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "composition/assets"
frames = json.loads((ASSETS / "frame-metrics.json").read_text())


def pane(label, image, legend, extra=""):
    return (f'<div class="pane {extra}"><div class="pane-head"><span>{label}</span><small>{legend}</small></div>'
            f'<img src="assets/{image}" alt="Stored Solidrift geometry"/></div>')


def scene(name, start, duration, phase, headline, detail, content, result, note=""):
    return f'''<section class="scene clip" id="{name}" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="0">
      <div class="topline"><span>SOLIDRIFT / GEOMETRY FAILURE MICROSCOPE</span><span>{phase}</span></div>
      <div class="story"><h1>{headline}</h1><p>{detail}</p></div>
      <div class="geometry">{content}</div>
      <div class="measurement"><strong>{result}</strong><span>{note}</span></div>
      <footer><span>RECORDED NATIVE CASE · BLENDER 5.3.0 ALPHA</span><span>Demo operands: Manifold project · Apache-2.0</span></footer>
    </section>'''


scenes = []
scenes.append(scene("original", 0, 3.4, "01 / ORIGINAL",
                    "A Boolean dropped a body.",
                    "Operand B exists in the input. FLOAT omits it; the comparison wire reveals where it should be.",
                    pane("INPUT / A + B", "original-input.svg", "A  •  B") + pane("FLOAT / B ABSENT", "original-output.svg", "FLOAT  ◌  MANIFOLD"),
                    "132 input triangles", "Recorded output, not a browser simulation."))
step_start, step_length = 3.4, 4.8 / len(frames)
for i, frame in enumerate(frames):
    progress = frame["step"] / 60 * 100
    content = pane(f'INPUT / ACCEPTED CUT {frame["step"]:02d} OF 60',
                   f'step-{frame["step"]:02d}.svg', 'A  •  B', 'wide')
    content += f'<div class="progress"><i style="width:{progress:.2f}%"></i></div>'
    scenes.append(scene(f'step-{i:02d}', step_start + i * step_length, step_length,
                        "02 / REDUCTION · STORED INPUT STATES",
                        "Remove geometry. Keep the failure.",
                        "Each accepted contraction kept valid solids and the declared omission in the recorded native run.",
                        content,
                        f'{frame["triangles"]} triangles',
                        "Intermediate output surfaces were not stored; selected input states shown."))
scenes.append(scene("witness", 8.2, 3.6, "03 / WITNESS",
                    "132 → 12. Same omission.",
                    "A valid 12-triangle witness carries the failure. This is the stored final native output.",
                    pane("INPUT / 12 TRIANGLES", "witness-input.svg", "A  •  B") + pane("FLOAT / B ABSENT", "witness-output.svg", "FLOAT  ◌  MANIFOLD"),
                    "60 accepted cuts", "One recorded case; not a global minimum."))
scenes.append(scene("repair", 11.8, 3.5, "04 / FULL-MODEL CHECK",
                    "13 vertices. Full model checked.",
                    "A witness intervention lifts to the original operands. Stored native comparison accepts the result.",
                    pane("REPAIRED INPUT / A + B", "repair-input.svg", "13 original vertices") + pane("FLOAT / MATCHED", "repair-output.svg", "FLOAT  ◌  MANIFOLD"),
                    "Input geometry changed", "This does not fix Blender's solver."))
scenes.append(scene("undo", 15.3, 3.9, "05 / UNDO",
                    "Undo it. The failure returns.",
                    "Original input coordinates are restored. The stored native output reproduces the omission.",
                    pane("RESTORED INPUT / A + B", "undo-input.svg", "Original coordinates") + pane("FLOAT / B ABSENT AGAIN", "undo-output.svg", "FLOAT  ◌  MANIFOLD"),
                    "Failure reproduced", "Open the interactive case at nazeeh111.github.io/Solidrift"))

html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=1280,height=720">
<title>Solidrift · Geometry failure microscope</title><style>
:root{--paper:#0b1420;--plate:#08121d;--surface:#111e2b;--line:#30465a;--ink:#edf6fb;--muted:#a6b9c7;--teal:#5de4d0;--blue:#93b9ff;--reference:#e6f58a}
*{box-sizing:border-box}html,body,#root{margin:0;width:1280px;height:720px;overflow:hidden;background:var(--paper)}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:var(--ink)}
.scene{position:absolute;inset:0;background:var(--paper);display:flex;flex-direction:column;padding:21px 25px 12px}
.topline{height:28px;display:flex;justify-content:space-between;color:var(--teal);font:700 11px ui-monospace,monospace;letter-spacing:1.25px}
.story{height:114px;display:flex;align-items:flex-end;justify-content:space-between;gap:20px;padding:0 0 13px}
h1{font-size:43px;line-height:1.04;letter-spacing:-1.8px;margin:0;font-weight:720;max-width:620px}
.story p{margin:0 0 3px;max-width:500px;color:var(--muted);font-size:16px;line-height:1.32}
.geometry{display:flex;gap:1px;position:relative;flex:1;min-height:0;border:1px solid var(--line);background:var(--line)}
.pane{min-width:0;flex:1;display:flex;flex-direction:column;background:var(--plate)}
.pane.wide{flex:1}
.pane-head{height:28px;padding:6px 10px;display:flex;justify-content:space-between;color:var(--ink);font:11px ui-monospace,monospace;letter-spacing:.6px}
.pane-head small{color:var(--muted);font-size:10px}
.pane img{width:100%;min-height:0;flex:1;object-fit:fill;display:block}
.progress{position:absolute;bottom:0;left:0;right:0;height:6px;background:var(--surface)}
.progress i{display:block;height:100%;background:var(--reference)}
.measurement{height:56px;display:flex;align-items:center;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line)}
.measurement strong{font-size:24px;letter-spacing:-.6px;color:var(--reference)}
.measurement span{font:11px ui-monospace,monospace;color:var(--muted);text-align:right}
footer{height:25px;display:flex;align-items:flex-end;justify-content:space-between;color:var(--muted);font:10px ui-monospace,monospace}
</style></head><body><div id="root" data-composition-id="main" data-no-timeline data-start="0" data-duration="19.2" data-width="1280" data-height="720">'''
html += "\n".join(scenes)
html += "</div></body></html>\n"
(HERE / "composition/index.html").write_text(html)
print(f"Built {len(scenes)} timed geometry scenes into composition/index.html")
