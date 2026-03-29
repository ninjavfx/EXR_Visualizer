# CODEX.md

## Purpose
`EXR_Visualizer` is a Python CLI for previewing EXR images through a fixed color pipeline:
1. Input LUT (`in_lut`, typically `.csp`) from linear camera/render space to target log space.
2. Optional ASC CDL from `.ccc`.
3. Output LUT (`out_lut`, typically `.cube`) to display space (Rec.709 in current setup).

This project currently prioritizes practical viewing/output over framework complexity.

## Repository Status
- Git repo initialized and connected to GitHub via SSH remote.
- `exr_view.py` remains the CLI entrypoint, with implementation split across focused modules.
- Packaging metadata is provided through `pyproject.toml` with an `exr-view` console script.
- Tested end-to-end on 2026-03-08 with a production EXR and discovered CDL.
- Interactive display now uses Qt (`PySide6`) instead of OpenCV HighGUI.
- Sequence playback was added for EXR file patterns addressed by trailing-dot prefixes.
- Project memory files are present: `AGENTS.md`, `TASKS.md`, `DECISIONS.md`, `.codex/session.md`.

## High-Level Architecture
### Main entry point
- `exr_view.py` -> `main()` orchestrates CLI, discovery, processing, save/display.
- In sequence mode, non-macOS runs initialize `QApplication` before cache worker threads start.

### Functional blocks
- `cli.py`: CLI argument parsing.
- `common.py`: shared failure helper.
- `exr_io.py`: EXR loading, save conversion, Qt display-image preparation.
- `color_pipeline.py`: LUT config, CDL parsing/application, OCIO processing, per-frame processing.
- `playback_controller.py`: shared sequence transport/timing/title logic used by all display backends.
- `qt_viewer.py`: Qt still-image window and sequence playback window/event loop.
- `sequence_playback.py`: sequence discovery, threaded cache state, playback loop.

### EXR loading strategy
- EXR backend preference is resolved in `exr_io.py` without importing OpenCV on the normal display path.
- Active loader preference remains: OpenImageIO, then OpenEXR bindings, then OpenCV.
- OpenCV is imported lazily so Qt display mode avoids macOS Qt/OpenCV conflicts unless save or the OpenCV EXR fallback is actually used.
- Sequence cache workers keep display frames as plain RGB `uint8` NumPy arrays; `QImage` creation now happens on the main Qt thread.
- The Qt viewer paints `QImage` directly instead of converting frames to `QPixmap`.
- macOS sequence playback uses an OpenCV HighGUI fallback instead of the Qt playback loop.
- Sequence playback transport state is centralized in `playback_controller.py` so Qt and OpenCV backends share the same stepping/timing/title behavior.
- The Qt viewer centers images at their prepared pixel size and only scales down when the window is smaller, so `--half` remains visually meaningful.
- The Qt viewer also tracks an interactive display scale separate from the processed image data, with `1`/`2`/`3` presets for 100%/50%/25% and `Shift+1` to resize the top-level window to the current scaled image size.
- `QApplication` is created on the initial main thread before starting sequence cache workers.
- Sequence discovery now uses `os.scandir()` instead of `os.listdir()` for lower directory-scan overhead.

## CLI Contract
Current arguments:
- `exr_path` (required): path to EXR file.
- `--half`: scale output dimensions to 50%.
- `-X` or `-x`: flop image horizontally.
- `-Y` or `-y`: flip image vertically.
- `--save OUTPUT_PATH`: save processed result (`.png`, `.jpg`, `.exr`, etc.).
- `--no-display`: skip OpenCV window display.
- `-range/--range START..END`: inclusive frame filter for sequence playback.
- `-fps/--fps`: sequence playback rate, default `24`.
- `-threads/--threads`: sequence cache worker threads, default `1`.

Behavior notes:
- If `--save` and display enabled, image is both saved and shown.
- `--half` affects both save and display outputs.
- `-X/-x` and `-Y/-y` affect both save and display outputs.
- Viewer closes on `q`, `Esc`, `Enter`, or window close button (not on arbitrary keypresses).
- In the Qt viewer, `1` sets 100% scale, `2` sets 50% scale, `3` sets 25% scale, and `Shift+1` resizes the window to the current scaled image size.
- In sequence mode, `Space` toggles play/pause, `,` steps back one frame, and `.` steps forward one frame.
- For non-EXR save formats: output is clamped to `[0,1]` and written as 8-bit.
- For `.exr` save: output is written as float32.
- Sequence mode is triggered when `exr_path` ends with `.` and does not point to an existing file.
- Sequence matching expects `.exr` files whose basename is `<prefix><digits>`, such as
  `shot.1.exr`, `shot.0001.exr`, or `shot.000001.exr`.
- Sequence playback starts once the first processed frame is ready, while the remaining
  frames continue caching in memory in the background.
- Once all sequence frames are cached, playback loops from memory to maintain
  real-time playback as closely as possible at the requested FPS.
- Sequence caching resolves and parses the sequence CDL once, then reuses that data for
  each frame instead of re-reading the `.ccc` file per frame.
- Sequence caching prints coarse progress updates instead of one log line per frame.
- Sequence caching can run with multiple worker threads; use `1` by default and try `2`
  or `4` on local NVMe storage.
- Sequence mode currently requires display and does not support `--save`.

## Color Pipeline Contract (Do Not Reorder)
Required operation order:
1. Apply `in_lut`.
2. Apply `.ccc` (if found).
3. Apply `out_lut`.

If `.ccc` is not found, processing continues and prints exactly:
- `CDL not found`

## Configuration Conventions
### `.luts` discovery
Checked in this order from current working directory:
1. `~/.config/exr_visualizer/.luts`
2. `./.luts`
3. `./LUT/.luts`

### `.luts` format
Expected keys:
- `in_lut = <path>`
- `out_lut = <path>`

Path resolution behavior:
- Absolute paths are used directly.
- Relative paths are resolved against:
1. current working directory
2. directory containing `.luts`

This dual resolution exists because current project config is `LUT/.luts` with values like `./LUT/...`.

Default config bootstrap:
- If no `.luts` config is found and bundled default LUT assets are available, an
  interactive run can prompt the user to copy defaults into `~/.config/exr_visualizer/`.
- Installed package defaults are bundled under the package data install path and copied
  into the user config directory on demand.

### `.ccc` discovery
Given `exr_path`, search for `*.ccc` in order:
1. EXR directory
2. Parent of EXR directory

If multiple are present, first alphabetical match is used.

## Dependencies and Environment
Packages in `requirements.txt`:
- `numpy`
- `opencv-python`
- `PySide6`
- `OpenColorIO`
- `OpenImageIO`
- `OpenEXR`

Packaging metadata:
- `pyproject.toml` uses `setuptools`.
- Installed console entry point: `exr-view = "exr_view:main"`.
- Bundled default LUT assets are installed as package data under `share/exr_visualizer/LUT`.

Important packaging detail:
- Import name is `PyOpenColorIO`, but pip package name is `OpenColorIO`.

Preferred setup:
```bash
uv venv --python 3.11 .venv
uv pip install .
```

Package install examples:
```bash
python3 -m pip install .
pipx install .
uv pip install .
```

Recommended deployed run command:
```bash
.venv/bin/exr-view /path/to/image.exr
```

Run examples:
```bash
.venv/bin/python exr_view.py /path/to/image.exr
.venv/bin/python exr_view.py /path/to/image.exr --half
.venv/bin/python exr_view.py /path/to/image.exr --save /tmp/output.png --no-display
.venv/bin/python exr_view.py /path/to/image.exr -X -Y --save /tmp/output.png --no-display
```

Display note:
- Interactive display uses `PySide6` windows for both still frames and sequence playback.
- OpenCV remains in use for image saving and as the final EXR-loading fallback, but it is imported lazily.
- On macOS, sequence display avoids constructing Qt image objects in worker threads.
- The viewer avoids `QPixmap` in the hot playback path to reduce native Cocoa-backed image handling.
- On macOS, sequence playback uses an OpenCV window instead of the Qt sequence viewer.

## Verified Runtime Example
Validated command:
```bash
.venv/bin/python exr_view.py \
  /mnt/work/00_RESEVIL/TNL_0090/4552x2400/TNL_0090_MP01_v001.001040.exr \
  --save /tmp/TNL_0090_MP01_v001.001040_preview.png \
  --no-display
```

Observed behavior:
- `.luts` discovered at `LUT/.luts`
- Input LUT and output LUT loaded successfully
- CDL auto-detected at `/mnt/work/00_RESEVIL/TNL_0090/TNL_0090_MP01_v001.ccc`
- Output written successfully

Also validated `--half` save dimensions:
- Full: `2400x4552`
- Half: `1200x2276`

## Known Limitations
- No automated tests yet.
- No explicit OCIO config workflow (using file transforms only).
- No channel/layer selection for multichannel EXRs.
- OpenEXR fallback currently expects `Imath` + `OpenEXR` Python bindings.
- GUI display still depends on a working Qt-capable environment.
- Sequence playback can consume substantial RAM because frames are cached after processing.
- Sequence playback currently loops continuously until closed and does not save image sequences.

## Change Guidelines for Future Sessions
- Preserve CLI backwards compatibility unless user requests changes.
- Preserve color operation order.
- Keep explicit errors; avoid silent behavior changes.
- Validate with real EXR before declaring color-path changes done.
- For non-interactive/headless validation, prefer `--save ... --no-display`.

## Suggested Test Matrix After Changes
1. `.luts` in project root.
2. `.luts` in `LUT/`.
3. `.ccc` found in EXR folder.
4. `.ccc` found in parent folder.
5. No `.ccc` case prints `CDL not found` and still renders.
6. `--half` on/off with save output dimension checks.
7. Display path (without `--no-display`) on a GUI-capable machine.
8. Linux/Wayland/X11 display smoke test for Qt window creation and key handling.
9. Linux interactive move/resize with Super/Win key while viewer stays open.
10. Sequence prefix detection with `shot.` style input.
11. Sequence range filtering (`-range 1000..2000`).
12. Mixed frame padding (`1`, `0001`, `000001`) in the same directory.

## Key Files
- `exr_view.py`
- `cli.py`
- `common.py`
- `exr_io.py`
- `qt_viewer.py`
- `playback_controller.py`
- `color_pipeline.py`
- `sequence_playback.py`
- `requirements.txt`
- `pyproject.toml`
- `README.md`
- `CODEX.md`
- `AGENTS.md`
- `TASKS.md`
- `DECISIONS.md`
- `.codex/session.md`
- `LUT/.luts`
- `LUT/Linear_to_SLog3.csp`
- `LUT/RECS_Rec709.cube`
