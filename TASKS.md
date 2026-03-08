# TASKS.md

## P0 (High Priority)
- Add automated tests for core behavior in `exr_view.py`:
  - `.luts` parsing and path resolution
  - `.ccc` discovery order (EXR dir, then parent)
  - pipeline order enforcement
  - orientation flags (`-X/-x`, `-Y/-y`)
  - help output sanity (`-h/--help`)

## P1 (Important)
- Add non-interactive regression test command(s) to README for Linux/macOS.
- Improve OpenEXR fallback robustness for channel naming edge cases beyond `R/G/B`.
- Add explicit return codes/messages for common dependency-missing scenarios.
- Add a small smoke-test script that validates Linux Qt font fallback behavior in display mode.

## P2 (Nice to Have)
- Add batch mode for image sequences/folders.
- Add optional output color metadata/report in stdout.
- Consider modularizing `exr_view.py` if functionality grows substantially.

## Done Recently (Not TODO)
- Added save/headless mode (`--save`, `--no-display`).
- Added orientation flags (`-X/-x`, `-Y/-y`).
- Fixed argparse help issue with `%` in help text.
- Added Linux Qt font handling and OpenCV `cv2/qt/fonts` bootstrap.
- Added Arch Linux font candidate `/usr/share/fonts/TTF`.
