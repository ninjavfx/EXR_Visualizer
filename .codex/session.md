# Session Summary

## What Was Done
- Added Qt still/sequence viewer scale shortcuts: `1` = 100%, `2` = 50%, `3` = 25%, and `Shift+1` resizes the window to the current scaled image size.
- Kept the new scale controls in the viewer layer so they do not affect processing, save output, or the existing `--half` CLI behavior.
- Replaced OpenCV HighGUI display with a `PySide6`-based Qt viewer for still-image display and sequence playback.
- Added `qt_viewer.py` to host the Qt application, still-image window, and timer-driven sequence viewer.
- Kept OpenCV for image save output and as the final EXR loading fallback.
- Changed `cv2` import to be lazy so normal Qt display runs avoid importing OpenCV unless save or the OpenCV EXR fallback is actually needed.
- Changed sequence caching to store plain RGB `uint8` arrays instead of `QImage` objects, and moved `QImage` construction back onto the main Qt thread.
- Replaced the Qt `QLabel`/`QPixmap` display path with direct `QImage` painting in a custom widget.
- Changed sequence mode to create `QApplication` before starting cache worker threads.
- Added a macOS-specific OpenCV fallback for sequence playback while keeping Qt for still-image display.
- Added `playback_controller.py` so sequence timing, stepping, and title/status logic are shared across the Qt and OpenCV backends.
- Fixed a Qt viewer regression where the custom paint path upscaled frames, making `--half` appear ineffective.
- Updated packaging/dependencies to include `PySide6`.
- Initialized and connected git repo to GitHub (`origin` via SSH).
- Implemented `exr_view.py` end-to-end EXR LUT/CDL viewer pipeline.
- Added CLI features:
  - `--half`
  - `--save OUTPUT_PATH`
  - `--no-display`
  - `-X/-x` horizontal flop
  - `-Y/-y` vertical flip
  - `-range/--range START..END` for sequence filtering
  - `-fps/--fps` with default `24` for sequence playback
- Added EXR sequence playback triggered by trailing-dot prefixes such as `shot.`.
- Added sequence frame discovery for `.exr` files with numeric suffixes like `1`, `0001`, or `000001`.
- Added per-frame processing cache so playback uses preprocessed frames held in memory.
- Updated sequence playback to start displaying as soon as the first frame is ready while the rest of the cache fills in the background.
- Added sequence transport controls: `Space` play/pause and `,` / `.` frame stepping.
- Reduced sequence cache overhead by reusing parsed CDL data and replacing per-frame cache logs with coarse progress updates.
- Added optional threaded sequence caching with `-threads`, defaulting to `1` and targeting `2` or `4` for local NVMe reads.
- Split the implementation into `cli.py`, `common.py`, `exr_io.py`, `color_pipeline.py`, and `sequence_playback.py` while keeping `exr_view.py` as the entrypoint.
- Resolved the EXR loader backend once at import time and changed sequence discovery to `os.scandir()`.
- Added `pyproject.toml` packaging metadata and exposed `exr-view` as a console-script entry point.
- Updated deployment docs to prefer `uv pip install .` and `.venv/bin/exr-view` on target machines.
- Added shared config lookup at `~/.config/exr_visualizer/.luts` and interactive first-run copying of bundled default LUT assets into the user config directory.
- Fixed help behavior (`-h/--help`) while keeping flop flags unchanged.
- Added OpenEXR fallback loading and corrected dependency packaging details.
- Updated README and CODEX documentation accordingly.

## Files Changed in This Session
- `exr_view.py`
- `cli.py`
- `common.py`
- `exr_io.py`
- `color_pipeline.py`
- `qt_viewer.py`
- `sequence_playback.py`
- `pyproject.toml`
- `README.md`
- `CODEX.md`
- `DECISIONS.md`
- `TASKS.md`
- `.codex/session.md`

## Current Status
- Tool runs and has been validated with a real EXR path in this workspace.
- Sequence discovery/range parsing was validated locally with temporary `.exr` filenames.
- Qt display backend was refactored in code, but no live GUI validation was run in this environment.
- A follow-up fix now avoids eager `cv2` import to reduce likely macOS Qt/OpenCV conflicts on display runs.
- A second follow-up fix now avoids constructing `QImage` objects in worker threads during sequence playback.
- A third follow-up fix now avoids `QPixmap` in the playback path to reduce Cocoa-backed image handling on macOS.
- A fourth follow-up fix now creates `QApplication` before worker-thread startup to match macOS Qt requirements.
- A fifth follow-up change now bypasses the unstable macOS Qt sequence path entirely and uses the existing OpenCV playback loop there.
- A short-term refactor now centralizes playback transport logic behind a shared controller to keep the backend split maintainable.
- A follow-up fix now prevents Qt from upscaling images by default so `--half` remains visually correct.
- A follow-up viewer change now adds interactive Qt scale presets and a resize-to-current-scale shortcut.
- Remote `main` has recent fixes pushed.
- No automated test suite yet.

## Recommended Next Steps
1. Add automated tests for parser/discovery/pipeline/orientation behavior.
2. Add tests for sequence discovery, range parsing, and FPS validation.
3. Decide whether sequence mode should support save/headless workflows.
4. Add display smoke tests that cover the Qt still-image path, non-macOS Qt sequence path, macOS OpenCV sequence fallback, the shared playback controller behavior, visible `--half` scaling, and the new still-viewer scale shortcuts.
## 2026-03-30
- Updated viewer close-key handling so only `q` and `Esc` close still-image and sequence windows.
- Removed `Enter`/`Return` as a close key from the Qt viewer and the macOS OpenCV sequence fallback.
- Updated `README.md`, `CODEX.md`, and `DECISIONS.md` to match the new close-key behavior.
- Next steps: run a GUI smoke test for still-image and sequence display key handling when a display-capable environment is available.
- Removed the macOS OpenCV sequence fallback and restored a single Qt playback path for Linux and macOS.
- Hardened Qt sequence playback by keeping `QApplication` startup ahead of worker threads, converting controller failures into caught runtime errors inside the Qt event loop, avoiding repeated `QImage` rebuilds for unchanged frames, and signaling cache workers to stop when the window closes.
- Remaining follow-up: interactive macOS sequence smoke testing is still needed.
