# CODEX.md

## Purpose
`EXR_Visualizer` is a Python CLI for previewing EXR images through a fixed color pipeline:
1. Input LUT (`in_lut`, typically `.csp`) from linear camera/render space to target log space.
2. Optional ASC CDL from `.ccc`.
3. Output LUT (`out_lut`, typically `.cube`) to display space (Rec.709 in current setup).

This project currently prioritizes practical viewing/output over framework complexity.

## Repository Status
- Git repo initialized and connected to GitHub via SSH remote.
- Primary implementation is in a single script: `exr_view.py`.
- Tested end-to-end on 2026-03-08 with a production EXR and discovered CDL.
- Linux viewer/font issues encountered in this session were addressed in code.
- Sequence playback was added for EXR file patterns addressed by trailing-dot prefixes.
- Project memory files are present: `AGENTS.md`, `TASKS.md`, `DECISIONS.md`, `.codex/session.md`.

## High-Level Architecture
### Main entry point
- `exr_view.py` -> `main()` orchestrates CLI, discovery, processing, save/display.

### Functional blocks
- `parse_args()`: CLI contract.
- `configure_linux_qt_fontdir()`, `bootstrap_opencv_qt_fonts()`: Linux Qt/OpenCV font compatibility.
- `find_luts_config()`, `parse_luts_config()`: LUT config discovery and path resolution.
- `load_exr()`: EXR loading (OpenImageIO first, OpenEXR fallback, OpenCV fallback).
- `parse_frame_range()`, `resolve_sequence_frames()`: sequence CLI parsing and frame discovery.
- `find_ccc()`, `parse_ccc()`, `apply_cdl()`: CDL discovery and application.
- `build_file_processor()`, `apply_ocio_processor()`: OCIO file transform processing.
- `process_frame()`: per-frame LUT/CDL/orientation processing.
- `save_image()`, `display_image()`, `play_sequence()`: output operations.

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

Behavior notes:
- If `--save` and display enabled, image is both saved and shown.
- `--half` affects both save and display outputs.
- `-X/-x` and `-Y/-y` affect both save and display outputs.
- Viewer closes on `q`, `Esc`, `Enter`, or window close button (not on arbitrary keypresses).
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
1. `./.luts`
2. `./LUT/.luts`

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

### `.ccc` discovery
Given `exr_path`, search for `*.ccc` in order:
1. EXR directory
2. Parent of EXR directory

If multiple are present, first alphabetical match is used.

## Dependencies and Environment
Packages in `requirements.txt`:
- `numpy`
- `opencv-python`
- `OpenColorIO`
- `OpenImageIO`
- `OpenEXR`

Important packaging detail:
- Import name is `PyOpenColorIO`, but pip package name is `OpenColorIO`.

Preferred setup:
```bash
uv venv --python 3.11 .venv
uv pip install -r requirements.txt
```

Run examples:
```bash
.venv/bin/python exr_view.py /path/to/image.exr
.venv/bin/python exr_view.py /path/to/image.exr --half
.venv/bin/python exr_view.py /path/to/image.exr --save /tmp/output.png --no-display
.venv/bin/python exr_view.py /path/to/image.exr -X -Y --save /tmp/output.png --no-display
```

Linux note:
- The script auto-configures Qt font dirs (`QT_QPA_FONTDIR`) and tries to bootstrap
  `cv2/qt/fonts` from system DejaVu fonts.
- Candidate font directories include:
  `/usr/share/fonts/truetype/dejavu`, `/usr/share/fonts/TTF`, `/usr/share/fonts/dejavu`,
  `/usr/share/fonts/truetype/freefont`, `/usr/share/fonts`.
- If `site-packages/cv2/qt/fonts` is not writable, bootstrap may be skipped; use manual
  `QT_QPA_FONTDIR` override in that case.

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
- Linux Qt font bootstrap depends on write access to the installed `cv2` package path.
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
8. Linux Qt font path behavior with missing `cv2/qt/fonts`.
9. Linux interactive move/resize with Super/Win key while viewer stays open.
10. Sequence prefix detection with `shot.` style input.
11. Sequence range filtering (`-range 1000..2000`).
12. Mixed frame padding (`1`, `0001`, `000001`) in the same directory.

## Key Files
- `exr_view.py`
- `requirements.txt`
- `README.md`
- `CODEX.md`
- `AGENTS.md`
- `TASKS.md`
- `DECISIONS.md`
- `.codex/session.md`
- `LUT/.luts`
- `LUT/Linear_to_SLog3.csp`
- `LUT/RECS_Rec709.cube`
