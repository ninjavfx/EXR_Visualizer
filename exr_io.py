from __future__ import annotations

import os
import sys

import numpy as np

from common import fail

# Helps OpenCV EXR IO on builds where this backend is opt-in.
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")


def configure_linux_qt_fontdir() -> None:
    """Avoid Qt font warnings with some OpenCV Linux wheels."""
    if not sys.platform.startswith("linux"):
        return
    if os.environ.get("QT_QPA_FONTDIR"):
        return

    candidates = [
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/TTF",
        "/usr/share/fonts/dejavu",
        "/usr/share/fonts/truetype/freefont",
        "/usr/share/fonts",
    ]
    for path in candidates:
        if os.path.isdir(path):
            os.environ["QT_QPA_FONTDIR"] = path
            break


configure_linux_qt_fontdir()


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


def bootstrap_opencv_qt_fonts() -> None:
    """Populate cv2/qt/fonts from system fonts when OpenCV wheel lacks bundled fonts."""
    if cv2 is None or not sys.platform.startswith("linux"):
        return

    cv2_dir = os.path.dirname(getattr(cv2, "__file__", ""))
    if not cv2_dir:
        return

    qt_fonts_dir = os.path.join(cv2_dir, "qt", "fonts")
    if os.path.isdir(qt_fonts_dir) and os.listdir(qt_fonts_dir):
        return

    source_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    src_font = next((p for p in source_fonts if os.path.isfile(p)), None)
    if not src_font:
        return

    try:
        os.makedirs(qt_fonts_dir, exist_ok=True)
        dst_font = os.path.join(qt_fonts_dir, "DejaVuSans.ttf")
        if not os.path.exists(dst_font):
            os.symlink(src_font, dst_font)
    except OSError:
        # Non-fatal; display may still work through system fontconfig.
        return


bootstrap_opencv_qt_fonts()


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


def prepare_display_image(img_rgb: np.ndarray, half: bool) -> np.ndarray:
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

    return (disp * 255.0 + 0.5).astype(np.uint8)[:, :, ::-1]


def display_image(img_rgb: np.ndarray, half: bool) -> None:
    disp_bgr = prepare_display_image(img_rgb, half)

    window_name = "EXR Visualizer"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.imshow(window_name, disp_bgr)

    while True:
        visible = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
        if visible < 1:
            break

        key = cv2.waitKeyEx(50)
        if key in (27, 13, ord("q"), ord("Q")):
            break

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
