# Tour source

The [19-second tour](../../docs/media/solidrift-tour.mp4) is a projection of the public recorded report at `tests/fixtures/native-report.json`. It samples 21 of the 61 stored input states, including the original and final witness, and displays native output geometry only at the baseline, final witness, accepted full-model repair and undo. The reduction's intermediate output surfaces were not stored and are never fabricated in this film.

The source uses only Python's standard library to build SVG plates and an editable HTML composition:

```sh
python3 tools/tour/generate-geometry.py
python3 tools/tour/make-composition.py
```

`generate-geometry.py` replays every accepted contraction and asserts that its final vertices and faces match the stored witness. The generated assets and `composition/index.html` live in the ignored `tools/tour/composition/` directory. Open the HTML to inspect the authored frames. The published MP4 was rendered at 1280 × 720, 30 fps with Hyperframes 0.8.33. A frame from the settled witness shot is the poster and is baked into video frame zero. The exported MP4 and JPEG are committed in `docs/media/`.

The video is a report-backed explanation of one recorded Blender run, not footage of a fresh native analysis or evidence for all Boolean failures. Demo operands retain Manifold's Apache-2.0 attribution in every frame; see [NOTICE](../../NOTICE).
