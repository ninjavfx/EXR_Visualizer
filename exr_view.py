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
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

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


# Optional imports are checked at runtime with clear errors.
try:
    import PyOpenColorIO as ocio
except Exception:  # pragma: no cover - environment-dependent
    ocio = None


try:
    import cv2
except Exception:  # pragma: no cover - environment-dependent
    cv2 = None


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


@dataclass(frozen=True)
class SequenceFrame:
    frame: int
    padding: int
    path: str


@dataclass
class SequenceCacheState:
    frames: List[SequenceFrame]
    display_cache: List[Optional[np.ndarray]]
    loaded_count: int = 0
    error: Optional[str] = None
    done: bool = False


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
    parser.add_argument(
        "-range",
        "--range",
        dest="frame_range",
        metavar="START..END",
        help="Limit sequence playback to an inclusive frame range, e.g. 1000..2000",
    )
    parser.add_argument(
        "-fps",
        "--fps",
        type=float,
        default=24.0,
        help="Sequence playback rate in frames per second (default: 24)",
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


def parse_frame_range(raw_range: Optional[str]) -> Optional[Tuple[int, int]]:
    if raw_range is None:
        return None

    parts = raw_range.split("..", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        fail(f"Invalid range '{raw_range}'; expected START..END")

    try:
        start = int(parts[0])
        end = int(parts[1])
    except ValueError:
        fail(f"Invalid range '{raw_range}'; frame values must be integers")

    if start > end:
        fail(f"Invalid range '{raw_range}'; START must be <= END")

    return start, end


def is_sequence_request(path: str) -> bool:
    return path.endswith(".") and not os.path.isfile(path)


def resolve_sequence_frames(
    requested_path: str, frame_range: Optional[Tuple[int, int]]
) -> List[SequenceFrame]:
    abs_requested = os.path.abspath(requested_path)
    seq_dir = os.path.dirname(abs_requested) or os.getcwd()
    seq_prefix = os.path.basename(abs_requested)

    if not os.path.isdir(seq_dir):
        fail(f"Sequence directory not found: {seq_dir}")

    matches: List[SequenceFrame] = []
    for entry in sorted(os.listdir(seq_dir)):
        full_path = os.path.join(seq_dir, entry)
        if not os.path.isfile(full_path):
            continue

        stem, ext = os.path.splitext(entry)
        if ext.lower() != ".exr":
            continue
        if not stem.startswith(seq_prefix):
            continue

        frame_text = stem[len(seq_prefix) :]
        if not frame_text or not frame_text.isdigit():
            continue

        frame = int(frame_text)
        if frame_range is not None:
            start, end = frame_range
            if frame < start or frame > end:
                continue

        matches.append(
            SequenceFrame(
                frame=frame,
                padding=len(frame_text),
                path=full_path,
            )
        )

    if not matches:
        if frame_range is None:
            fail(
                f"No EXR sequence frames found for prefix '{requested_path}'. "
                "Expected files like prefix0001.exr or prefix1.exr"
            )
        fail(
            f"No EXR sequence frames found for prefix '{requested_path}' "
            f"in range {frame_range[0]}..{frame_range[1]}"
        )

    matches.sort(key=lambda item: (item.frame, item.padding, item.path))
    return matches


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

    # Ignore unrelated key presses (e.g. Linux Super/Win key combos).
    # Exit only on explicit close keys or if the window is closed.
    while True:
        visible = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
        if visible < 1:
            break

        key = cv2.waitKeyEx(50)
        if key in (27, 13, ord("q"), ord("Q")):  # Esc, Enter, q, Q
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


def apply_orientation(img_rgb: np.ndarray, flop_x: bool, flip_y: bool) -> np.ndarray:
    out = img_rgb
    if flop_x:
        out = out[:, ::-1, :]
    if flip_y:
        out = out[::-1, :, :]
    return np.ascontiguousarray(out)


def process_frame(
    exr_path: str,
    in_proc,
    out_proc,
    flop_x: bool,
    flip_y: bool,
) -> np.ndarray:
    img = load_exr(exr_path)
    img = apply_ocio_processor(img, in_proc)

    ccc_path = find_ccc(exr_path)
    if ccc_path:
        print(f"Using CDL: {ccc_path}")
        slope, offset, power, saturation = parse_ccc(ccc_path)
        img = apply_cdl(img, slope, offset, power, saturation)
    else:
        print("CDL not found")

    img = apply_ocio_processor(img, out_proc)
    return apply_orientation(img, flop_x, flip_y)


def cache_sequence_frames(
    state: SequenceCacheState,
    in_proc,
    out_proc,
    flop_x: bool,
    flip_y: bool,
    half: bool,
    state_lock: threading.Lock,
) -> None:
    try:
        for index, item in enumerate(state.frames):
            print(f"Caching frame {item.frame}: {item.path}")
            processed = process_frame(
                item.path,
                in_proc,
                out_proc,
                flop_x,
                flip_y,
            )
            display_ready = prepare_display_image(processed, half)
            with state_lock:
                state.display_cache[index] = display_ready
                state.loaded_count += 1
    except BaseException as exc:
        with state_lock:
            state.error = str(exc) or exc.__class__.__name__
    finally:
        with state_lock:
            state.done = True


def play_sequence(
    state: SequenceCacheState,
    fps: float,
    state_lock: threading.Lock,
) -> None:
    if cv2 is None:
        fail("OpenCV is required for display. Install with: pip install opencv-python")
    if fps <= 0:
        fail("FPS must be greater than 0")

    window_name = "EXR Visualizer"
    frame_delay = 1.0 / fps

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    index = 0
    is_playing = True

    step_back_keys = {ord(","), ord("<")}
    step_forward_keys = {ord("."), ord(">")}

    while True:
        with state_lock:
            if state.error is not None:
                fail(state.error)
            first_frame = state.display_cache[0] if state.display_cache else None
            loaded_count = state.loaded_count
            done = state.done
        if first_frame is not None:
            break
        if done:
            fail("Sequence cache did not produce any frames")

        visible = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
        if visible < 1:
            cv2.destroyAllWindows()
            return
        cv2.waitKeyEx(50)

    index = 0
    next_deadline = time.perf_counter() + frame_delay

    while True:
        visible = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
        if visible < 1:
            break

        with state_lock:
            if state.error is not None:
                fail(state.error)
            loaded_count = state.loaded_count
            done = state.done
            current = state.display_cache[index]
            if current is None and loaded_count > 0:
                fallback_index = min(index, loaded_count - 1)
                current = state.display_cache[fallback_index]
                index = fallback_index
            frame_info = state.frames[index]

        if current is None:
            current = first_frame
            index = 0
            frame_info = state.frames[0]

        cv2.imshow(window_name, current)
        if hasattr(cv2, "setWindowTitle"):
            suffix = ""
            if not done:
                suffix = f" [{loaded_count}/{len(state.frames)} cached]"
            status = "Playing" if is_playing else "Paused"
            cv2.setWindowTitle(
                window_name,
                f"EXR Visualizer - {status} - frame {frame_info.frame}{suffix}",
            )

        now = time.perf_counter()
        if is_playing:
            wait_ms = max(1, int((next_deadline - now) * 1000.0))
        else:
            wait_ms = 50
        key = cv2.waitKeyEx(wait_ms)
        if key in (27, 13, ord("q"), ord("Q")):
            break
        if key == 32:
            is_playing = not is_playing
            next_deadline = time.perf_counter() + frame_delay
            continue

        with state_lock:
            loaded_count = state.loaded_count
            done = state.done

        available_count = len(state.frames) if done else loaded_count
        if key in step_back_keys and available_count > 0:
            index = (index - 1) % available_count
            next_deadline = time.perf_counter() + frame_delay
            continue
        if key in step_forward_keys and available_count > 0:
            index = (index + 1) % available_count
            next_deadline = time.perf_counter() + frame_delay
            continue

        if not is_playing:
            continue

        with state_lock:
            loaded_count = state.loaded_count
            done = state.done

        now = time.perf_counter()
        if now >= next_deadline + frame_delay:
            next_deadline = now + frame_delay
        else:
            next_deadline += frame_delay

        if loaded_count <= 0:
            index = 0
        elif done:
            index = (index + 1) % len(state.frames)
        else:
            index = (index + 1) % loaded_count

    cv2.destroyAllWindows()


def main() -> None:
    args = parse_args()
    if args.fps <= 0:
        fail("FPS must be greater than 0")

    exr_path = os.path.abspath(args.exr_path)
    frame_range = parse_frame_range(args.frame_range)
    sequence_mode = is_sequence_request(args.exr_path)

    luts_path = find_luts_config(os.getcwd())
    in_lut, out_lut = parse_luts_config(luts_path)

    print(f"Using .luts: {luts_path}")
    print(f"Input LUT: {in_lut}")
    print(f"Output LUT: {out_lut}")

    in_proc = build_file_processor(in_lut)
    out_proc = build_file_processor(out_lut)

    if sequence_mode:
        if args.save:
            fail("Sequence playback does not support --save")
        if args.no_display:
            fail("Sequence playback requires display; --no-display is not supported")

        frames = resolve_sequence_frames(args.exr_path, frame_range)
        print(
            f"Sequence frames: {frames[0].frame}..{frames[-1].frame} "
            f"({len(frames)} total, playing while caching at {args.fps:g} fps)"
        )

        state = SequenceCacheState(
            frames=frames,
            display_cache=[None] * len(frames),
        )
        state_lock = threading.Lock()
        loader = threading.Thread(
            target=cache_sequence_frames,
            args=(
                state,
                in_proc,
                out_proc,
                args.flop_x,
                args.flip_y,
                args.half,
                state_lock,
            ),
            daemon=True,
        )
        loader.start()

        play_sequence(state, args.fps, state_lock)
        return

    img = process_frame(
        exr_path,
        in_proc,
        out_proc,
        args.flop_x,
        args.flip_y,
    )

    if args.save:
        save_image(img, os.path.abspath(args.save), args.half)

    if not args.no_display:
        display_image(img, args.half)


if __name__ == "__main__":
    main()
