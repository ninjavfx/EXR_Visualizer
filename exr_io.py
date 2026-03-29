from __future__ import annotations

import os

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from common import fail

# Helps OpenCV EXR IO on builds where this backend is opt-in.
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")


try:
    import cv2
except Exception:  # pragma: no cover - environment-dependent
    cv2 = None

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


def _load_exr_cv2(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        fail(f"Failed to open EXR with OpenCV: {path}")
    if img.ndim == 2:
        img = np.stack([img, img, img], axis=-1)
    if img.shape[2] < 3:
        fail("EXR has fewer than 3 channels; RGB required")
    img = img[:, :, :3][:, :, ::-1]
    return img.astype(np.float32, copy=False)


if oiio is not None:
    _ACTIVE_EXR_LOADER = _load_exr_oiio
elif OpenEXR is not None and Imath is not None:
    _ACTIVE_EXR_LOADER = _load_exr_openexr
elif cv2 is not None:
    _ACTIVE_EXR_LOADER = _load_exr_cv2
else:
    _ACTIVE_EXR_LOADER = None


def load_exr(path: str) -> np.ndarray:
    if not os.path.isfile(path):
        fail(f"EXR file not found: {path}")
    if _ACTIVE_EXR_LOADER is None:
        fail(
            "Could not read EXR. Install OpenImageIO, OpenEXR python bindings, "
            "or OpenCV with OpenEXR support."
        )
    return _ACTIVE_EXR_LOADER(path)


def prepare_display_image(img_rgb: np.ndarray, half: bool) -> QImage:
    disp = np.clip(img_rgb, 0.0, 1.0)
    disp = np.ascontiguousarray((disp * 255.0 + 0.5).astype(np.uint8))
    height, width = disp.shape[:2]
    image = QImage(disp.data, width, height, width * 3, QImage.Format_RGB888).copy()
    if half:
        image = image.scaled(
            max(1, width // 2),
            max(1, height // 2),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
    return image


def display_image(img_rgb: np.ndarray, half: bool) -> None:
    from qt_viewer import display_qimage

    display_qimage(prepare_display_image(img_rgb, half), title="EXR Visualizer")


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
