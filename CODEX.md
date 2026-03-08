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

## High-Level Architecture
### Main entry point
- `exr_view.py` -> `main()` orchestrates CLI, discovery, processing, save/display.

### Functional blocks
- `parse_args()`: CLI contract.
- `find_luts_config()`, `parse_luts_config()`: LUT config discovery and path resolution.
- `load_exr()`: EXR loading (OpenImageIO first, OpenCV fallback).
- `find_ccc()`, `parse_ccc()`, `apply_cdl()`: CDL discovery and application.
- `build_file_processor()`, `apply_ocio_processor()`: OCIO file transform processing.
- `save_image()`, `display_image()`: output operations.

## CLI Contract
Current arguments:
- `exr_path` (required): path to EXR file.
- `--half`: scale output dimensions to 50%.
- `--save OUTPUT_PATH`: save processed result (`.png`, `.jpg`, `.exr`, etc.).
- `--no-display`: skip OpenCV window display.

Behavior notes:
- If `--save` and display enabled, image is both saved and shown.
- `--half` affects both save and display outputs.
- For non-EXR save formats: output is clamped to `[0,1]` and written as 8-bit.
- For `.exr` save: output is written as float32.

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
```

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
- No EXR sequence/batch mode.
- No explicit OCIO config workflow (using file transforms only).
- No channel/layer selection for multichannel EXRs.
- Current error message in `build_file_processor()` references `pip install PyOpenColorIO`; package name should be `OpenColorIO` if you touch that area.

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

## Key Files
- `exr_view.py`
- `requirements.txt`
- `README.md`
- `CODEX.md`
- `LUT/.luts`
- `LUT/Linear_to_SLog3.csp`
- `LUT/RECS_Rec709.cube`
