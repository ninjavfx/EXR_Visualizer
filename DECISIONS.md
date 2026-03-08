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
