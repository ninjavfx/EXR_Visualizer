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
- Add a small smoke-test script that validates Qt display startup and key handling in still and sequence modes.
- Validate the lazy-`cv2` display path on macOS with and without `--save`.
- Validate macOS sequence playback after moving `QImage` construction to the main thread.
- Validate macOS sequence playback after removing `QPixmap` from the display path.
- Validate macOS sequence playback after creating `QApplication` before starting worker threads.
- Decide whether the macOS OpenCV sequence fallback should remain permanent or be replaced with a different native viewer backend.
- If the backend split persists, add tests around the shared playback controller so both backends inherit the same transport behavior.
- Add a regression test or manual smoke-test note for `--half` display behavior in the Qt viewer.
- Decide whether sequence mode should gain image-sequence export and/or headless validation behavior.
- Validate the documented `uv pip install .` deployment flow on a clean machine.
- Decide whether default LUT bootstrap should also expose a non-interactive install flag for setup automation.

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
- Added setuptools packaging metadata and an `exr-view` console script entry point.
- Updated the README to make `uv pip install .` and `.venv/bin/exr-view` the primary deployment workflow.
- Added shared config lookup at `~/.config/exr_visualizer/.luts` with first-run default LUT bootstrap.
- Fixed argparse help issue with `%` in help text.
- Replaced OpenCV HighGUI display with a PySide6 viewer for stills and sequence playback.
