# EXR_Visualizer

Tool to view EXR files with this pipeline:
1. Input LUT from `.luts` (`in_lut`, `.csp`)
2. Optional CDL from `.ccc` in EXR folder or its parent
3. Output LUT from `.luts` (`out_lut`, `.cube`)

## Install

Recommended deployment on another machine:

```bash
git clone <repo>
cd EXR_Visualizer
uv venv --python 3.11 .venv
uv pip install .
```

Run without activating the environment:

```bash
.venv/bin/exr-view /path/to/image.exr
```

Or activate it first:

```bash
source .venv/bin/activate
exr-view /path/to/image.exr
```

On first run, if no LUT config is found yet, the tool checks
`~/.config/exr_visualizer/.luts` first and can offer to copy the bundled default LUT
config and LUT assets into `~/.config/exr_visualizer/`.

Alternative install methods:

```bash
python3 -m pip install -r requirements.txt
```

Package install:

```bash
python3 -m pip install .
```

After package install, the CLI is available as:

```bash
exr-view /path/to/image.exr
```

Or isolate it with `pipx`:

```bash
pipx install .
```

Or with `uv`:

```bash
uv venv --python 3.11 .venv
uv pip install -r requirements.txt
uv pip install .
```

### Quick macOS install

```bash
cd /path/to/EXR_Visualizer
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv venv --python 3.11 .venv
~/.local/bin/uv pip install -r requirements.txt
```

If Finder blocks terminal GUI windows, run headless with:
```bash
.venv/bin/python exr_view.py /path/to/image.exr --save /tmp/output.png --no-display
```

### Display backend

Interactive display now uses Qt via `PySide6` instead of OpenCV HighGUI.
This removes the previous Linux-specific OpenCV Qt font bootstrap path and gives
more reliable window close and key handling for stills and sequence playback.
OpenCV is imported lazily now so display runs do not pull in `cv2` unless the
save path or the OpenCV EXR fallback loader is actually needed.
Sequence playback now uses the same Qt viewer on Linux and macOS.

## Run

```bash
.venv/bin/exr-view /path/to/image.exr
.venv/bin/exr-view /path/to/image.exr --half
.venv/bin/exr-view /path/to/image.exr --save output.png --no-display
.venv/bin/exr-view /path/to/image.exr -X -Y --save output.png --no-display
exr-view /path/to/image.exr
.venv/bin/exr-view /path/to/shot. --fps 24
.venv/bin/exr-view /path/to/shot. -range 1000..2000 -fps 24
.venv/bin/exr-view /path/to/shot. -threads 2
.venv/bin/exr-view /path/to/shot. -threads 4
```

Sequence mode is enabled when the input path ends with a trailing `.` and does not
name an existing file. For example, `/show/shot/render.` matches frames such as:

- `render.1.exr`
- `render.0001.exr`
- `render.000001.exr`

The player scans the directory, finds the first and last matching frame, starts
displaying as soon as the first processed frame is ready, and keeps caching the rest
of the sequence in memory in the background. Once cached, playback loops from memory
at the requested FPS. Default playback rate is `24`.

For sequence playback, CDL discovery/parsing is done once up front and reused for the
full cache pass. Cache logging is reduced to lightweight progress updates.

Notes:
- `-range START..END` is inclusive.
- `-threads` defaults to `1`; `2` or `4` are good starting points for local NVMe storage.
- Sequence playback currently requires display mode.
- `--save` remains single-image only.

## `.luts` location

The script looks for:
- `~/.config/exr_visualizer/.luts`
- `./.luts`
- fallback: `./LUT/.luts`

If no config is found and bundled defaults are available, the tool can prompt to
install them into `~/.config/exr_visualizer/` on first interactive run.

## Viewer controls

In display mode, the window closes on:
- `q`
- `Esc`
- Window close button
- `1` shows the image at 100% scale (1 image pixel = 1 screen pixel)
- `2` shows the image at 50% scale
- `3` shows the image at 25% scale
- `Shift+1` resizes the window to the current display scale

In sequence mode:
- `Space` toggles play/pause
- `,` steps back one frame
- `.` steps forward one frame
