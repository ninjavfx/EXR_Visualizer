# TASKS.md

## P0 (High Priority)
- Add automated tests for core behavior in `exr_view.py`:
  - `.luts` parsing and path resolution
  - `.ccc` discovery order (EXR dir, then parent)
  - pipeline order enforcement
  - orientation flags (`-X/-x`, `-Y/-y`)
  - help output sanity (`-h/--help`)
  - sequence prefix discovery and numeric frame parsing
  - `-range/--range` validation and inclusive filtering
  - `-fps/--fps` validation

## P1 (Important)
- Add non-interactive regression test command(s) to README for Linux/macOS.
- Improve OpenEXR fallback robustness for channel naming edge cases beyond `R/G/B`.
- Add explicit return codes/messages for common dependency-missing scenarios.
- Add a small smoke-test script that validates Linux Qt font fallback behavior in display mode.
- Decide whether sequence mode should gain image-sequence export and/or headless validation behavior.

## P2 (Nice to Have)
- Add optional output color metadata/report in stdout.
- Consider modularizing `exr_view.py` if functionality grows substantially.

## Done Recently (Not TODO)
- Added save/headless mode (`--save`, `--no-display`).
- Added orientation flags (`-X/-x`, `-Y/-y`).
- Added EXR sequence playback with `shot.` prefix detection, `-range`, `-fps`, and in-memory frame caching.
- Updated sequence playback to display while frames continue caching in the background.
- Fixed argparse help issue with `%` in help text.
- Added Linux Qt font handling and OpenCV `cv2/qt/fonts` bootstrap.
- Added Arch Linux font candidate `/usr/share/fonts/TTF`.
