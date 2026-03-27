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

## Done Recently (Not TODO)
- Added save/headless mode (`--save`, `--no-display`).
- Added orientation flags (`-X/-x`, `-Y/-y`).
- Added EXR sequence playback with `shot.` prefix detection, `-range`, `-fps`, and in-memory frame caching.
- Updated sequence playback to display while frames continue caching in the background.
- Added basic sequence transport controls for play/pause and frame stepping.
- Reduced sequence cache overhead by reusing parsed CDL data and trimming per-frame logging.
- Added optional threaded sequence caching with `-threads`.
- Split the implementation into focused modules while keeping `exr_view.py` as the entrypoint.
- Resolved the active EXR loader once and switched sequence discovery to `os.scandir()`.
- Fixed argparse help issue with `%` in help text.
- Added Linux Qt font handling and OpenCV `cv2/qt/fonts` bootstrap.
- Added Arch Linux font candidate `/usr/share/fonts/TTF`.
