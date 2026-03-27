# EXR_Visualizer

Tool to view EXR files with this pipeline:
1. Input LUT from `.luts` (`in_lut`, `.csp`)
2. Optional CDL from `.ccc` in EXR folder or its parent
3. Output LUT from `.luts` (`out_lut`, `.cube`)

## Install

```bash
python3 -m pip install -r requirements.txt
```

Or with `uv`:

```bash
uv venv --python 3.11 .venv
uv pip install -r requirements.txt
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

### Linux Qt font warning (OpenCV window mode)

If you see:
`QFontDatabase: Cannot find font directory .../cv2/qt/fonts`

run with a system font dir:
```bash
QT_QPA_FONTDIR=/usr/share/fonts/truetype/dejavu python3 exr_view.py /path/to/image.exr
```

The script now auto-detects common Linux font directories and also tries to bootstrap
`cv2/qt/fonts` from system DejaVu fonts automatically. The manual override is still available.

## Run

```bash
python3 exr_view.py /path/to/image.exr
python3 exr_view.py /path/to/image.exr --half
python3 exr_view.py /path/to/image.exr --save output.png --no-display
python3 exr_view.py /path/to/image.exr -X -Y --save output.png --no-display
python3 exr_view.py /path/to/shot. --fps 24
python3 exr_view.py /path/to/shot. -range 1000..2000 -fps 24
python3 exr_view.py /path/to/shot. -threads 2
python3 exr_view.py /path/to/shot. -threads 4
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
- `./.luts`
- fallback: `./LUT/.luts`

## Viewer controls

In display mode, the window closes on:
- `q`
- `Esc`
- `Enter`
- Window close button

In sequence mode:
- `Space` toggles play/pause
- `,` steps back one frame
- `.` steps forward one frame
