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
