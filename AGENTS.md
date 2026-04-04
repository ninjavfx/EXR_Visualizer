# AGENTS.md

## Purpose
This repository contains a Python CLI tool (`exr_view.py`) to visualize EXR files through a LUT/CDL pipeline and optionally save output.

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
- `ls -la LUT && cat LUT/.luts` (confirm active LUT config/assets)

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
- Sequence transport shortcuts currently include:
  - `Space`
  - `,`
  - `.`
  - `Home`
  - `End`

## Code Style / Editing Rules
- Keep `exr_view.py` as the CLI entrypoint. Focused helper modules already exist and should be preserved unless there is a clear reason to refactor further.
- Use float32 processing for image math.
- Avoid adding heavy dependencies unless needed.
- Update `requirements.txt` only when imports/code require it.
- If behavior changes, update `README.md` and `CODEX.md` in the same change.

## Platform Notes
- Interactive display uses Qt via `PySide6` for stills and sequence playback.
- OpenCV is no longer part of the runtime dependency set.
- EXR reading now prefers OpenImageIO and falls back to the OpenEXR Python bindings.
- Viewer windows should close only on `q`, `Esc`, or the window close button.
- Prefer headless `--save ... --no-display` checks when no GUI environment is available.

## Memory File Maintenance (Required)
After meaningful code/doc changes, update these files:
- `AGENTS.md`: workflow conventions and current repo-specific instructions.
- `CODEX.md`: architecture, config, known issues, current status.
- `DECISIONS.md`: new technical decisions and rationale.
- `TASKS.md`: add/remove tasks based on latest status.
- `.codex/session.md`: summarize what changed this session and next steps.

Keep these files concise and factual. Do not record hypothetical features as completed work.
