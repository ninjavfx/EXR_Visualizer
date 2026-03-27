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

### 2026-03-08: Linux Qt font mitigation
- Decision: auto-set `QT_QPA_FONTDIR`, bootstrap `cv2/qt/fonts`, include Arch path `/usr/share/fonts/TTF`.
- Why: address OpenCV Qt font warnings/errors on Linux distros.
- Note: bootstrap is best-effort; manual `QT_QPA_FONTDIR` remains the fallback when package paths are read-only.

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
