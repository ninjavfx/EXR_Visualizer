from __future__ import annotations

import os

import numpy as np
from PySide6.QtGui import QImage

from common import fail


try:
    import OpenImageIO as oiio  # type: ignore
except Exception:  # pragma: no cover - environment-dependent
    oiio = None

try:
    import Imath  # type: ignore
    import OpenEXR  # type: ignore
except Exception:  # pragma: no cover - environment-dependent
    Imath = None
    OpenEXR = None


def _load_exr_oiio(path: str) -> np.ndarray:
    inp = oiio.ImageInput.open(path)
    if not inp:
        fail(f"Failed to open EXR with OpenImageIO: {path}")
    try:
        spec = inp.spec()
        pixels = inp.read_image(format=oiio.FLOAT)
    finally:
        inp.close()

    if pixels is None:
        fail(f"Failed to read EXR pixels: {path}")

    arr = np.array(pixels, dtype=np.float32)
    arr = arr.reshape(spec.height, spec.width, spec.nchannels)
    if arr.shape[2] < 3:
        fail("EXR has fewer than 3 channels; RGB required")
    return arr[:, :, :3].copy()


def _load_exr_openexr(path: str) -> np.ndarray:
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
        ordered = list(channels)
        if len(ordered) < 3:
            fail("EXR has fewer than 3 channels; RGB required")
        r = read_channel(ordered[0])
        g = read_channel(ordered[1])
        b = read_channel(ordered[2])

    return np.stack([r, g, b], axis=-1).astype(np.float32, copy=False)


if oiio is not None:
    _ACTIVE_EXR_LOADER = _load_exr_oiio
elif OpenEXR is not None and Imath is not None:
    _ACTIVE_EXR_LOADER = _load_exr_openexr
else:
    _ACTIVE_EXR_LOADER = None


def load_exr(path: str) -> np.ndarray:
    if not os.path.isfile(path):
        fail(f"EXR file not found: {path}")
    if _ACTIVE_EXR_LOADER is None:
        fail(
            "No EXR reader backend is available. Install OpenImageIO or the "
            "OpenEXR Python bindings."
        )
    try:
        return _ACTIVE_EXR_LOADER(path)
    except SystemExit:
        raise
    except Exception as exc:
        fail(str(exc) or "Failed to read EXR")


def prepare_display_array(img_rgb: np.ndarray, half: bool) -> np.ndarray:
    disp = np.clip(img_rgb, 0.0, 1.0)
    if half:
        disp = disp[::2, ::2]
    return np.ascontiguousarray((disp * 255.0 + 0.5).astype(np.uint8))


def qimage_from_rgb_u8(img_rgb_u8: np.ndarray) -> QImage:
    height, width = img_rgb_u8.shape[:2]
    return QImage(
        img_rgb_u8.data,
        width,
        height,
        width * 3,
        QImage.Format_RGB888,
    ).copy()


def prepare_display_image(img_rgb: np.ndarray, half: bool) -> QImage:
    return qimage_from_rgb_u8(prepare_display_array(img_rgb, half))


def display_image(img_rgb: np.ndarray, half: bool) -> None:
    from qt_viewer import display_qimage

    display_qimage(prepare_display_image(img_rgb, half), title="EXR Visualizer")


def _half_scale_axis(img: np.ndarray, axis: int) -> np.ndarray:
    size = img.shape[axis]
    target = max(1, size // 2)
    if target == size:
        return img
    if target == 1:
        return img.mean(axis=axis, keepdims=True, dtype=np.float32)

    trim = target * 2
    slices = [slice(None)] * img.ndim
    slices[axis] = slice(0, trim)
    trimmed = img[tuple(slices)]

    shape = list(trimmed.shape)
    shape[axis] = target
    shape.insert(axis + 1, 2)
    reshaped = trimmed.reshape(shape)
    return reshaped.mean(axis=axis + 1, dtype=np.float32)


def half_scale_image(img_rgb: np.ndarray) -> np.ndarray:
    return _half_scale_axis(_half_scale_axis(img_rgb, 0), 1)


def _save_with_oiio(img_rgb: np.ndarray, output_path: str) -> None:
    if oiio is None:
        fail("OpenImageIO is required for saving. Install with: pip install OpenImageIO")

    height, width = img_rgb.shape[:2]
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".exr":
        data = np.ascontiguousarray(img_rgb.astype(np.float32, copy=False))
        spec = oiio.ImageSpec(width, height, 3, oiio.FLOAT)
    else:
        data = np.ascontiguousarray(
            (np.clip(img_rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        )
        spec = oiio.ImageSpec(width, height, 3, oiio.UINT8)

    out = oiio.ImageOutput.create(output_path)
    if out is None:
        fail(f"Failed to create output writer: {output_path}")

    try:
        if not out.open(output_path, spec):
            fail(f"Failed to open output path for writing: {output_path}")
        if not out.write_image(data):
            fail(f"Failed to save image: {output_path}")
    finally:
        out.close()


def save_image(img_rgb: np.ndarray, output_path: str, half: bool) -> None:
    out = img_rgb
    if half:
        out = half_scale_image(out)
    _save_with_oiio(out, output_path)
    print(f"Saved image: {output_path}")
