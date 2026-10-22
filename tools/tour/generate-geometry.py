"""Draw report-backed Solidrift geometry frames for the short tour.

These are projections of stored meshes, not new native solver outputs.
"""
from __future__ import annotations

import copy
import html
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1] if (HERE.parents[1] / "tests/fixtures/native-report.json").exists() else HERE.parent / "Solidrift"
REPORT = json.loads((REPO / "tests/fixtures/native-report.json").read_text())
ASSETS = HERE / "composition/assets"
ASSETS.mkdir(parents=True, exist_ok=True)
W, H = 560, 390
ORIGINAL = list(REPORT["baseline"]["inputs"].values())
POINTS = [v for mesh in ORIGINAL for v in mesh["vertices"]]
LOW = [min(v[k] for v in POINTS) for k in range(3)]
HIGH = [max(v[k] for v in POINTS) for k in range(3)]
CENTER = [(a + b) / 2 for a, b in zip(LOW, HIGH)]
SPAN = max(b - a for a, b in zip(LOW, HIGH))


def project(point):
    x, y, z = [(point[k] - CENTER[k]) / SPAN for k in range(3)]
    yaw, pitch = 0.55, -0.30
    xx = math.cos(yaw) * x + math.sin(yaw) * z
    zz = -math.sin(yaw) * x + math.cos(yaw) * z
    yy = math.cos(pitch) * y - math.sin(pitch) * zz
    depth = math.sin(pitch) * y + math.cos(pitch) * zz
    scale = min(W * 0.96, H * 0.94)
    return W / 2 + xx * scale, H / 2 - yy * scale, depth


def svg(meshes, output_name, markers=()):
    shapes = []
    grid = []
    for i in range(-5, 6):
        q = i / 10
        for ends in (((-.5, -.55, q), (.5, -.55, q)), ((q, -.55, -.5), (q, -.55, .5))):
            a, b = [project(tuple(p[k] * SPAN + CENTER[k] for k in range(3))) for p in ends]
            grid.append(f'<path d="M{a[0]:.2f} {a[1]:.2f}L{b[0]:.2f} {b[1]:.2f}"/>')
    for mesh, color, wire in meshes:
        points = [project(p) for p in mesh["vertices"]]
        for face in mesh["faces"]:
            p = [points[i] for i in face]
            a, b, c = p
            u = [b[k] - a[k] for k in range(3)]
            v = [c[k] - a[k] for k in range(3)]
            nz = u[0] * v[1] - u[1] * v[0]
            light = min(abs(nz) / 18000, 1)
            coords = " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in p)
            shapes.append((sum(x[2] for x in p) / 3, coords, color, wire, light))
    shapes.sort(key=lambda item: item[0])
    polygons = []
    for _, coords, color, wire, light in shapes:
        if wire:
            polygons.append(f'<polygon points="{html.escape(coords)}" fill="none" stroke="{color}" stroke-opacity=".76" stroke-width="1.1"/>')
        else:
            opacity = 0.20 + 0.19 * light
            polygons.append(f'<polygon points="{html.escape(coords)}" fill="{color}" fill-opacity="{opacity:.2f}" stroke="{color}" stroke-opacity=".34" stroke-width=".75"/>')
    rings = ''.join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.2" fill="#08121d" stroke="#e6f58a" stroke-width="1.6"/>'
                    for x, y in markers)
    body = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">'
            f'<rect width="{W}" height="{H}" fill="#08121d"/>'
            f'<g fill="none" stroke="#263a4b" stroke-width=".65">{"".join(grid)}</g>'
            f'{"".join(polygons)}{rings}</svg>')
    (ASSETS / output_name).write_text(body)


def pair(pair_value, name, marker_side=None, marker_ids=()):
    markers = () if marker_side is None else [project(pair_value[marker_side]["vertices"][i])[:2] for i in marker_ids]
    svg([(pair_value[0], "#5de4d0", False), (pair_value[1], "#93b9ff", False)], name, markers)


def native(result, name):
    svg([(result["FLOAT"], "#93b9ff", False), (result["MANIFOLD"], "#e6f58a", True)], name)


pair(ORIGINAL, "original-input.svg")
native(REPORT["baseline"]["outputs"], "original-output.svg")
pair(REPORT["reduction"]["operands"], "witness-input.svg")
native(REPORT["reduction"]["final_outputs"], "witness-output.svg")
accepted = REPORT["repair"]["accepted"]
pair(accepted["full_repaired"], "repair-input.svg", accepted["intervention"]["side"], accepted["cluster"])
native({"FLOAT": accepted["full_check"]["output_geometry"],
        "MANIFOLD": accepted["full_check"]["reference_geometry"]}, "repair-output.svg")
pair(accepted["undo_inputs"], "undo-input.svg")
native({"FLOAT": accepted["undo_signature"]["geometry"],
        "MANIFOLD": REPORT["baseline"]["outputs"]["MANIFOLD"]}, "undo-output.svg")

state = copy.deepcopy(REPORT["reduction"]["original_operands"])
pair(state, "step-00.svg")
frame_metrics = [{"step": 0, "triangles": sum(len(mesh["faces"]) for mesh in state)}]
for index, step in enumerate(REPORT["reduction"]["accepted_steps"], 1):
    mesh = state[step["operand"]]
    u, v = sorted(step["edge"])
    mesh["vertices"][u] = step["vertex_after"]
    mesh["vertices"].pop(v)
    mesh["faces"] = [
        [((u if point == v else point) - (1 if (u if point == v else point) > v else 0)) for point in face]
        for face in mesh["faces"] if not (u in face and v in face)
    ]
    if index % 3 == 0:
        pair(state, f"step-{index:02d}.svg")
        frame_metrics.append({"step": index, "triangles": sum(len(mesh["faces"]) for mesh in state)})

for side in (0, 1):
    assert state[side]["vertices"] == REPORT["reduction"]["operands"][side]["vertices"]
    assert state[side]["faces"] == REPORT["reduction"]["operands"][side]["faces"]
(ASSETS / "frame-metrics.json").write_text(json.dumps(frame_metrics, indent=2) + "\n")
print("Generated 29 report-backed SVG frames; replay matches stored final witness.")
