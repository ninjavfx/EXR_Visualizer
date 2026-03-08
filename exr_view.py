#!/usr/bin/env python3
"""Display EXR with LUT + optional CDL pipeline.

Pipeline order:
1) input LUT (.csp)
2) CDL from first discovered .ccc (optional)
3) output LUT (.cube)
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import xml.etree.ElementTree as ET
from typing import Optional, Tuple

import numpy as np

# Helps OpenCV EXR IO on builds where this backend is opt-in.
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")


# Optional imports are checked at runtime with clear errors.
try:
    import PyOpenColorIO as ocio
except Exception:  # pragma: no cover - environment-dependent
    ocio = None


try:
    import cv2
except Exception:  # pragma: no cover - environment-dependent
    cv2 = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Display EXR with LUT/CDL pipeline")
    parser.add_argument("exr_path", help="Path to EXR image")
    parser.add_argument(
        "--half",
        action="store_true",
        help="Scale displayed image to 50%%",
    )
    parser.add_argument(
        "-X",
        "-x",
        dest="flop_x",
        action="store_true",
        help="Flop image horizontally",
    )
    parser.add_argument(
        "-Y",
        "-y",
        dest="flip_y",
        action="store_true",
        help="Flip image vertically",
    )
    parser.add_argument(
        "--save",
        metavar="OUTPUT_PATH",
        help="Save processed image to file (e.g. output.png, output.jpg, output.exr)",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Do not open a display window",
    )
    return parser.parse_args()


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def find_luts_config(cwd: str) -> str:
    candidates = [
        os.path.join(cwd, ".luts"),
        os.path.join(cwd, "LUT", ".luts"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    fail(".luts config not found in current directory or ./LUT/.luts")


def parse_luts_config(path: str) -> Tuple[str, str]:
    in_lut = None
    out_lut = None

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key == "in_lut":
                in_lut = value
            elif key == "out_lut":
                out_lut = value

    if not in_lut or not out_lut:
        fail(f"Invalid .luts file: expected 'in_lut' and 'out_lut' in {path}")

    base = os.path.dirname(path)
    cwd = os.getcwd()

    def resolve_lut(raw_value: str) -> str:
        if os.path.isabs(raw_value):
            return raw_value

        candidates = [
            os.path.abspath(os.path.join(cwd, raw_value)),
            os.path.abspath(os.path.join(base, raw_value)),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        # Return the first candidate for clearer error messaging below.
        return candidates[0]

    in_lut_abs = resolve_lut(in_lut)
    out_lut_abs = resolve_lut(out_lut)

    if not os.path.isfile(in_lut_abs):
        fail(f"Input LUT not found: {in_lut_abs}")
    if not os.path.isfile(out_lut_abs):
        fail(f"Output LUT not found: {out_lut_abs}")

    return in_lut_abs, out_lut_abs


def load_exr(path: str) -> np.ndarray:
    if not os.path.isfile(path):
        fail(f"EXR file not found: {path}")

    # Prefer OpenImageIO if available because EXR support is reliable.
    try:
        import OpenImageIO as oiio  # type: ignore

        inp = oiio.ImageInput.open(path)
        if not inp:
            fail(f"Failed to open EXR with OpenImageIO: {path}")
        spec = inp.spec()
        pixels = inp.read_image(format=oiio.FLOAT)
        inp.close()

        if pixels is None:
            fail(f"Failed to read EXR pixels: {path}")

        arr = np.array(pixels, dtype=np.float32)
        arr = arr.reshape(spec.height, spec.width, spec.nchannels)
        if arr.shape[2] < 3:
            fail("EXR has fewer than 3 channels; RGB required")
        return arr[:, :, :3].copy()
    except ImportError:
        pass

    # Fallback: OpenEXR python bindings (portable across many macOS/Linux setups).
    try:
        import Imath  # type: ignore
        import OpenEXR  # type: ignore

        exr = OpenEXR.InputFile(path)
        header = exr.header()
        data_window = header["dataWindow"]
        width = data_window.max.x - data_window.min.x + 1
        height = data_window.max.y - data_window.min.y + 1
        channels = header["channels"].keys()

        pix_type = Imath.PixelType(Imath.PixelType.FLOAT)

        def read_channel(channel_name: str) -> np.ndarray:
            raw = exr.channel(channel_name, pix_type)
            return np.frombuffer(raw, dtype=np.float32).reshape(height, width)

        if {"R", "G", "B"}.issubset(channels):
            r = read_channel("R")
            g = read_channel("G")
            b = read_channel("B")
        else:
            # If RGB labels are absent, use first 3 channels in header order.
            ordered = list(channels)
            if len(ordered) < 3:
                fail("EXR has fewer than 3 channels; RGB required")
            c0 = read_channel(ordered[0])
            c1 = read_channel(ordered[1])
            c2 = read_channel(ordered[2])
            r, g, b = c0, c1, c2

        return np.stack([r, g, b], axis=-1).astype(np.float32, copy=False)
    except ImportError:
        pass

    # Fallback: OpenCV with OpenEXR support enabled.
    if cv2 is not None:
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            if img.ndim == 2:
                img = np.stack([img, img, img], axis=-1)
            if img.shape[2] < 3:
                fail("EXR has fewer than 3 channels; RGB required")
            # OpenCV uses BGR channel order for color images.
            img = img[:, :, :3][:, :, ::-1]
            return img.astype(np.float32, copy=False)

    fail(
        "Could not read EXR. Install OpenImageIO, OpenEXR python bindings, "
        "or OpenCV with OpenEXR support."
    )


def find_ccc(exr_path: str) -> Optional[str]:
    exr_dir = os.path.dirname(os.path.abspath(exr_path))
    parent_dir = os.path.dirname(exr_dir)

    for folder in [exr_dir, parent_dir]:
        candidates = sorted(glob.glob(os.path.join(folder, "*.ccc")))
        if candidates:
            return candidates[0]
    return None


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_ccc(path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        fail(f"Failed to parse CCC file {path}: {exc}")

    slope = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    offset = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    power = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    saturation = 1.0

    color_correction = None
    for node in root.iter():
        if _local_name(node.tag) == "ColorCorrection":
            color_correction = node
            break

    if color_correction is None:
        fail(f"No ColorCorrection node found in {path}")

    for node in color_correction.iter():
        name = _local_name(node.tag)
        text = (node.text or "").strip()
        if not text:
            continue

        if name in {"Slope", "Offset", "Power"}:
            values = [float(x) for x in text.split()]
            if len(values) != 3:
                fail(f"Invalid {name} in {path}: expected 3 values")
            arr = np.array(values, dtype=np.float32)
            if name == "Slope":
                slope = arr
            elif name == "Offset":
                offset = arr
            else:
                power = arr
        elif name == "Saturation":
            saturation = float(text)

    return slope, offset, power, saturation


def apply_cdl(
    img: np.ndarray,
    slope: np.ndarray,
    offset: np.ndarray,
    power: np.ndarray,
    saturation: float,
) -> np.ndarray:
    out = img * slope + offset
    out = np.clip(out, 0.0, None)
    out = np.power(out, power)

    # ASC CDL luma coefficients.
    luma = (
        out[:, :, 0] * 0.2126
        + out[:, :, 1] * 0.7152
        + out[:, :, 2] * 0.0722
    )
    luma = luma[:, :, None]
    out = luma + saturation * (out - luma)
    return out.astype(np.float32, copy=False)


def build_file_processor(lut_path: str):
    if ocio is None:
        fail("PyOpenColorIO is required. Install with: pip install OpenColorIO")

    transform = ocio.FileTransform(src=lut_path)
    config = ocio.Config.CreateRaw()
    processor = config.getProcessor(transform)
    return processor.getDefaultCPUProcessor()


def apply_ocio_processor(img: np.ndarray, cpu_processor) -> np.ndarray:
    flat = np.ascontiguousarray(img.reshape(-1, 3), dtype=np.float32)
    cpu_processor.applyRGB(flat)
    return flat.reshape(img.shape)


def display_image(img_rgb: np.ndarray, half: bool) -> None:
    if cv2 is None:
        fail("OpenCV is required for display. Install with: pip install opencv-python")

    disp = np.clip(img_rgb, 0.0, 1.0)
    if half:
        h, w = disp.shape[:2]
        disp = cv2.resize(
            disp,
            (max(1, w // 2), max(1, h // 2)),
            interpolation=cv2.INTER_AREA,
        )

    disp_u8 = (disp * 255.0 + 0.5).astype(np.uint8)
    disp_bgr = disp_u8[:, :, ::-1]

    cv2.imshow("EXR Visualizer", disp_bgr)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def save_image(img_rgb: np.ndarray, output_path: str, half: bool) -> None:
    if cv2 is None:
        fail("OpenCV is required for saving. Install with: pip install opencv-python")

    out = img_rgb
    if half:
        h, w = out.shape[:2]
        out = cv2.resize(
            out,
            (max(1, w // 2), max(1, h // 2)),
            interpolation=cv2.INTER_AREA,
        )

    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".exr":
        bgr = out[:, :, ::-1].astype(np.float32, copy=False)
    else:
        bgr = (np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)[:, :, ::-1]

    if not cv2.imwrite(output_path, bgr):
        fail(f"Failed to save image: {output_path}")

    print(f"Saved image: {output_path}")


def apply_orientation(img_rgb: np.ndarray, flop_x: bool, flip_y: bool) -> np.ndarray:
    out = img_rgb
    if flop_x:
        out = out[:, ::-1, :]
    if flip_y:
        out = out[::-1, :, :]
    return np.ascontiguousarray(out)


def main() -> None:
    args = parse_args()
    exr_path = os.path.abspath(args.exr_path)

    luts_path = find_luts_config(os.getcwd())
    in_lut, out_lut = parse_luts_config(luts_path)

    print(f"Using .luts: {luts_path}")
    print(f"Input LUT: {in_lut}")
    print(f"Output LUT: {out_lut}")

    img = load_exr(exr_path)

    in_proc = build_file_processor(in_lut)
    out_proc = build_file_processor(out_lut)

    # 1) Linear -> target space (from in_lut)
    img = apply_ocio_processor(img, in_proc)

    # 2) Apply CDL if found
    ccc_path = find_ccc(exr_path)
    if ccc_path:
        print(f"Using CDL: {ccc_path}")
        slope, offset, power, saturation = parse_ccc(ccc_path)
        img = apply_cdl(img, slope, offset, power, saturation)
    else:
        print("CDL not found")

    # 3) Apply output LUT to display space
    img = apply_ocio_processor(img, out_proc)
    img = apply_orientation(img, args.flop_x, args.flip_y)

    if args.save:
        save_image(img, os.path.abspath(args.save), args.half)

    if not args.no_display:
        display_image(img, args.half)


if __name__ == "__main__":
    main()
