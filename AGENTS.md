# AGENTS.md

## Purpose
This repository contains a single Python CLI tool (`exr_view.py`) to visualize EXR files through a LUT/CDL pipeline and optionally save output.

## Start Here (Context Loading Order)
When starting a new Codex session in this repo, read files in this order:
1. `README.md` (user-facing usage and platform notes)
2. `CODEX.md` (architecture, conventions, current status)
3. `DECISIONS.md` (why key technical choices were made)
4. `TASKS.md` (remaining work by priority)
5. `exr_view.py` (actual implementation)

Then check git state:
- `git status --short`
- `git log --oneline -n 8`

## Project Conventions
- Keep the color pipeline order unchanged unless explicitly requested:
1. input LUT
2. optional CDL
3. output LUT
- Preserve existing CLI behavior and flags:
  - `--half`
  - `-X/-x` (horizontal flop)
  - `-Y/-y` (vertical flip)
  - `--save`
  - `--no-display`
- `-h/--help` must remain argparse help.
- Keep error messages explicit (no silent failures).
- Prefer headless verification with `--save ... --no-display` when GUI is unavailable.

## Code Style / Editing Rules
- Keep implementation in `exr_view.py` unless there is clear reason to split modules.
- Use float32 processing for image math.
- Avoid adding heavy dependencies unless needed.
- Update `requirements.txt` only when imports/code require it.
- If behavior changes, update `README.md` and `CODEX.md` in the same change.

## Platform Notes
- Linux font/Qt behavior is handled in code (`configure_linux_qt_fontdir`, `bootstrap_opencv_qt_fonts`).
- Arch Linux-specific font path `/usr/share/fonts/TTF` is intentionally included.
- Viewer window should close only on `q`, `Esc`, `Enter`, or window close button.

## Memory File Maintenance (Required)
After meaningful code/doc changes, update these files:
- `CODEX.md`: architecture, config, known issues, current status.
- `DECISIONS.md`: new technical decisions and rationale.
- `TASKS.md`: add/remove tasks based on latest status.
- `.codex/session.md`: summarize what changed this session and next steps.

Keep these files concise and factual. Do not record hypothetical features as completed work.
