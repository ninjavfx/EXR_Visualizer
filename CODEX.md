# CODEX.md

## Project Overview
`EXR_Visualizer` is a Python CLI tool that loads an EXR image, applies a color pipeline using LUTs and optional CDL, then displays and/or saves the result.

Primary use case in current setup:
- Input EXR is linear camera render data.
- Convert linear to Sony SLog3 via input LUT (`.csp`).
- Apply ASC CDL from `.ccc` when available.
- Convert SLog3 to Rec.709 via output LUT (`.cube`).

## Current Architecture
Single-script architecture (for now):
- `exr_view.py`: CLI, config discovery, EXR I/O, LUT/CDL processing, display/save output.

Core flow in `main()`:
1. Parse args (`exr_path`, `--half`, `--save`, `--no-display`).
2. Find `.luts` config.
3. Resolve `in_lut` and `out_lut` file paths.
4. Load EXR pixels as float RGB.
5. Apply input LUT (OCIO `FileTransform`).
6. Locate and apply CDL from `.ccc` if found.
7. Apply output LUT (OCIO `FileTransform`).
8. Save and/or display result.

## Color Pipeline Contract
Order of operations is intentional and must remain:
1. `linear -> target space` via `in_lut` (`.csp`)
2. `.ccc` (ASC CDL slope/offset/power/saturation)
3. `target space -> display` via `out_lut` (`.cube`)

If no `.ccc` is found, tool must continue and print:
- `CDL not found`

## Config and Asset Conventions
### `.luts` discovery
The tool checks, in order:
1. `./.luts`
2. `./LUT/.luts`

### `.luts` format
Expected keys:
- `in_lut = <path-to-input-lut>`
- `out_lut = <path-to-output-lut>`

Paths may be absolute or relative.
Relative paths are resolved robustly against:
1. current working directory
2. `.luts` file directory

### CDL discovery
Given `exr_path`, search for `*.ccc` in order:
1. EXR file directory
2. Parent directory of EXR directory

First alphabetical match is used.

## Dependencies
Runtime Python packages:
- `numpy`
- `opencv-python`
- `OpenColorIO` (imported as `PyOpenColorIO`)
- `OpenImageIO`

Tracked in `requirements.txt`.

## Environment Setup
Preferred (current project setup): `uv`

```bash
uv venv --python 3.11 .venv
uv pip install -r requirements.txt
```

Run examples:
```bash
.venv/bin/python exr_view.py /path/to/image.exr
.venv/bin/python exr_view.py /path/to/image.exr --half
.venv/bin/python exr_view.py /path/to/image.exr --save output.png --no-display
```

## Display and Save Behavior
- Display path uses OpenCV window (`cv2.imshow`) unless `--no-display`.
- Save path (`--save`) writes:
  - float EXR if extension is `.exr`
  - 8-bit clamped output for non-EXR formats (e.g. `.png`, `.jpg`)
- `--half` affects both display and save output dimensions.

## Implementation Notes
- EXR loading prefers `OpenImageIO`, with OpenCV fallback.
- Processing is float32 RGB throughout.
- OCIO is used directly via `Config.CreateRaw()` + `FileTransform` processors.
- CDL parsing reads first `ColorCorrection` block in `.ccc` XML.

## Current Progress (as of 2026-03-08)
Completed:
- Git repository initialized and linked to GitHub remote via SSH.
- Initial EXR visualizer tool implemented.
- Added `--save` and `--no-display`.
- Fixed LUT path resolution bug when using `LUT/.luts` with `./LUT/...` paths.
- End-to-end tested with real EXR:
  - `/mnt/work/00_RESEVIL/TNL_0090/4552x2400/TNL_0090_MP01_v001.001040.exr`
  - Detected CDL at `/mnt/work/00_RESEVIL/TNL_0090/TNL_0090_MP01_v001.ccc`
  - Verified full-size and `--half` saves.

## Known Limitations / Next Improvements
- No unit tests yet (pipeline and parser behavior should be covered).
- No multi-view/multi-layer EXR channel selection yet.
- No explicit OCIO config support (currently file transforms only).
- No batch mode over folders/sequences yet.

## Working Conventions for Future Sessions
- Preserve exact color pipeline order unless user explicitly requests changes.
- Keep CLI flags backward-compatible.
- Prefer explicit error messages over silent fallbacks.
- When changing LUT/CDL logic, validate with a real EXR and both cases:
  - with `.ccc`
  - without `.ccc`

## Key Files
- `exr_view.py`
- `requirements.txt`
- `README.md`
- `LUT/.luts`
- `LUT/Linear_to_SLog3.csp`
- `LUT/RECS_Rec709.cube`
