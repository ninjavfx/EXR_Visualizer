# DECISIONS.md

## Decision Log

### 2026-03-08: Keep single-file architecture (`exr_view.py`)
- Decision: maintain one-script implementation for now.
- Why: scope is still small; faster iteration and simpler onboarding.

### 2026-03-08: Use OCIO file transforms directly
- Decision: apply LUTs with `PyOpenColorIO` `FileTransform` + raw config processors.
- Why: reliable handling of `.csp` and `.cube` with minimal custom logic.

### 2026-03-08: Apply CDL manually after input LUT
- Decision: parse `.ccc` XML and apply ASC CDL math in NumPy.
- Why: explicit control of pipeline order and behavior.

### 2026-03-08: `.luts` discovery and path resolution
- Decision: search `./.luts`, then `./LUT/.luts`; resolve relative LUT paths against both CWD and `.luts` directory.
- Why: supports current project layout and avoids double-prefix path bugs.

### 2026-03-08: EXR load fallback order
- Decision: load EXR via OpenImageIO first, then OpenEXR bindings, then OpenCV.
- Why: maximize portability and reliability across Linux/macOS setups.

### 2026-03-08: Keep `-h/--help` as help
- Decision: do not repurpose `-h`; horizontal flop stays `-X/-x`.
- Why: standard CLI convention and user request.

### 2026-03-08: Display-close key policy
- Decision: viewer exits only on `q`, `Esc`, `Enter`, or window close button.
- Why: prevents accidental close on Linux Super/Win key interactions.

### 2026-03-29: Replace OpenCV HighGUI display with PySide6
- Decision: use `PySide6` for still-image and sequence playback windows, while keeping OpenCV for file save and as the last EXR-loading fallback.
- Why: removes OpenCV HighGUI/Linux font issues, gives cleaner window lifecycle and key handling, and provides a better base for future viewer controls without changing the CLI contract.

### 2026-03-29: Import OpenCV lazily after the Qt display switch
- Decision: avoid importing `cv2` on startup and only import it when saving or when the OpenCV EXR fallback loader is actually used.
- Why: reduces the chance of macOS crashes from mixing `opencv-python` and `PySide6` Qt stacks in the same process during normal display runs.

### 2026-03-29: Keep Qt image-object creation on the main thread
- Decision: sequence worker threads cache plain RGB `uint8` NumPy arrays and the Qt viewer converts them to `QImage` on the GUI thread.
- Why: reduces the chance of macOS Cocoa/Qt crashes during sequence playback from creating Qt image objects off the main thread.

### 2026-03-29: Paint sequence frames from QImage instead of QPixmap
- Decision: render viewer frames by painting `QImage` directly in a widget rather than converting each frame to `QPixmap`.
- Why: `QPixmap` is more tightly coupled to native window-system resources; avoiding it reduces the macOS-specific native GUI risk in the playback path.

### 2026-03-29: Create QApplication before starting sequence worker threads
- Decision: in sequence mode, initialize `QApplication` on the main thread before launching cache worker threads.
- Why: macOS Qt warns and can segfault if `QApplication` is first created after other threads have already started.

### 2026-03-29: Use OpenCV fallback for sequence playback on macOS
- Decision: keep Qt for still-image display, but route macOS sequence playback through the OpenCV HighGUI loop.
- Why: repeated crashes remained in the macOS Qt/Cocoa sequence event path even after fixing worker-thread `QImage` creation, removing `QPixmap`, and correcting `QApplication` startup ordering.

### 2026-03-29: Centralize playback transport logic behind a shared controller
- Decision: move sequence transport state and timing logic into a backend-agnostic playback controller shared by the Qt and OpenCV sequence viewers.
- Why: keeps the short-term platform split maintainable and lets future playback features land once instead of being duplicated per backend.

### 2026-03-29: Do not upscale Qt display images by default
- Decision: have the Qt image widget center frames at their prepared pixel size and only scale them down when the window is too small.
- Why: preserves the intended visible effect of `--half`, which regressed when the custom Qt widget started scaling all images up to fill the window.

### 2026-03-29: Add interactive Qt display scale presets instead of reprocessing images
- Decision: implement `1`/`2`/`3` as Qt viewer display-scale presets for 100%, 50%, and 25%, and use `Shift+1` to resize the outer window to the current scaled image size.
- Why: the request is about inspection ergonomics, not color/output changes, so the shortcut behavior should stay in the viewer layer and avoid touching the processed pixel pipeline or CLI flags such as `--half`.

### 2026-03-08: Standardize on `uv` + Python 3.11
- Decision: recommend `uv venv --python 3.11` for environment setup.
- Why: reproducible installs with working wheels for current dependency set.

### 2026-03-27: Sequence playback uses trailing-dot prefix discovery and progressive memory caching
- Decision: treat an input ending with `.` as a sequence prefix, match `.exr` files with trailing digits before the extension, support inclusive `-range START..END`, begin display as soon as the first processed frame is ready, and keep caching the rest of the processed sequence in memory during playback.
- Why: matches common VFX naming patterns (`shot.0001.exr` etc.), keeps single-file CLI compatibility, reduces startup delay, and still prioritizes smooth real-time playback once frames are cached.
- Note: sequence mode currently requires display and does not support `--save`.

### 2026-03-27: Sequence playback gets basic transport controls
- Decision: support `Space` for play/pause and `,` / `.` for single-frame stepping in sequence mode.
- Why: basic transport controls are needed to inspect frames without leaving the playback view, and punctuation keys are more reliable than OpenCV arrow-key codes across platforms.

### 2026-03-27: Reuse sequence CDL data and reduce cache logging
- Decision: resolve and parse the sequence `.ccc` once before cache loading, then reuse the parsed CDL values for all frames; replace per-frame cache logging with coarse progress output.
- Why: removes repeated XML I/O/parsing work and cuts terminal overhead during long cache passes without changing image results.

### 2026-03-27: Add optional threaded sequence caching
- Decision: add `-threads/--threads` for sequence caching with a default of `1`, and recommend `2` or `4` for local NVMe-backed sequences.
- Why: parallel EXR read and processing can reduce cache time on fast local storage while preserving deterministic frame order in playback.
- Note: each worker builds its own OCIO processors to avoid sharing processor instances across threads.

### 2026-03-27: Split implementation into focused modules and resolve EXR loader once
- Decision: keep `exr_view.py` as the entrypoint but move CLI, shared failure handling, EXR I/O, color pipeline logic, and sequence playback into separate modules.
- Why: the single script had grown large enough that sequence state, playback logic, I/O, and color processing were becoming harder to reason about and extend safely.
- Decision: resolve the active EXR loading backend once at import time instead of checking loader availability on every frame.
- Why: removes repeated per-frame backend selection overhead, especially during sequence caching.

### 2026-03-27: Add setuptools packaging and console-script entry point
- Decision: add `pyproject.toml` with setuptools metadata and expose `exr-view` as the installed command via `exr_view:main`.
- Why: allows standard `pip install .`, `uv pip install .`, and `pipx install .` workflows without changing the existing CLI entry function.

### 2026-03-27: Document `uv` package install as the default deployment path
- Decision: prefer `uv venv --python 3.11 .venv` plus `uv pip install .`, and document `.venv/bin/exr-view` as the primary run command.
- Why: matches the current environment management approach and avoids depending on `python -m pip` inside the target environment.

### 2026-03-27: Support shared user LUT config bootstrap
- Decision: check `~/.config/exr_visualizer/.luts` before working-directory configs and, when no config is found, offer to copy bundled default LUT assets into `~/.config/exr_visualizer/` during interactive runs.
- Why: makes the tool runnable from anywhere after first-time setup without forcing users to stay in the repo directory.
