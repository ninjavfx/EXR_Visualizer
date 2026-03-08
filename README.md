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

The script now auto-detects common Linux font directories, but this manual override is still available.

## Run

```bash
python3 exr_view.py /path/to/image.exr
python3 exr_view.py /path/to/image.exr --half
python3 exr_view.py /path/to/image.exr --save output.png --no-display
python3 exr_view.py /path/to/image.exr -X -Y --save output.png --no-display
```

## `.luts` location

The script looks for:
- `./.luts`
- fallback: `./LUT/.luts`
