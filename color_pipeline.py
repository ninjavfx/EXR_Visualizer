from __future__ import annotations

import glob
import os
import shutil
import sys
import sysconfig
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from common import fail
from exr_io import load_exr

try:
    import PyOpenColorIO as ocio
except Exception:  # pragma: no cover - environment-dependent
    ocio = None


def find_luts_config(cwd: str) -> str:
    config_path = get_config_luts_path()
    candidates = [
        str(config_path),
        os.path.join(cwd, ".luts"),
        os.path.join(cwd, "LUT", ".luts"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path

    installed = maybe_install_default_luts(config_path)
    if installed is not None:
        return installed

    fail(
        ".luts config not found in "
        f"{config_path}, current directory, or ./LUT/.luts"
    )


def get_config_dir() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home).expanduser() / "exr_visualizer"
    return Path.home() / ".config" / "exr_visualizer"


def get_config_luts_path() -> Path:
    return get_config_dir() / ".luts"


def get_bundled_lut_dir() -> Optional[Path]:
    module_dir = Path(__file__).resolve().parent
    repo_lut_dir = module_dir / "LUT"
    if repo_lut_dir.is_dir():
        return repo_lut_dir

    data_root = Path(sysconfig.get_path("data"))
    installed_lut_dir = data_root / "share" / "exr_visualizer" / "LUT"
    if installed_lut_dir.is_dir():
        return installed_lut_dir

    return None


def install_default_luts(config_path: Path, bundled_lut_dir: Path) -> str:
    config_dir = config_path.parent
    target_lut_dir = config_dir / "LUT"
    source_luts = bundled_lut_dir / ".luts"
    if not source_luts.is_file():
        fail(f"Bundled default .luts not found: {source_luts}")

    config_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundled_lut_dir, target_lut_dir, dirs_exist_ok=True)
    shutil.copy2(source_luts, config_path)
    print(f"Installed default LUT config: {config_path}")
    return str(config_path)


def maybe_install_default_luts(config_path: Path) -> Optional[str]:
    bundled_lut_dir = get_bundled_lut_dir()
    if bundled_lut_dir is None:
        return None
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return None

    prompt = (
        f"Default LUT config not found at {config_path}.\n"
        f"Copy bundled defaults from {bundled_lut_dir} now? [Y/n]: "
    )
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return None

    if answer not in ("", "y", "yes"):
        return None

    return install_default_luts(config_path, bundled_lut_dir)


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
        return candidates[0]

    in_lut_abs = resolve_lut(in_lut)
    out_lut_abs = resolve_lut(out_lut)

    if not os.path.isfile(in_lut_abs):
        fail(f"Input LUT not found: {in_lut_abs}")
    if not os.path.isfile(out_lut_abs):
        fail(f"Output LUT not found: {out_lut_abs}")

    return in_lut_abs, out_lut_abs


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
    ccc_path: Optional[str] = None,
    cdl_values: Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, float]] = None,
    log_cdl: bool = True,
) -> np.ndarray:
    img = load_exr(exr_path)
    img = apply_ocio_processor(img, in_proc)

    if ccc_path is None and cdl_values is None:
        ccc_path = find_ccc(exr_path)
        if ccc_path:
            cdl_values = parse_ccc(ccc_path)

    if ccc_path and cdl_values is not None:
        if log_cdl:
            print(f"Using CDL: {ccc_path}")
        slope, offset, power, saturation = cdl_values
        img = apply_cdl(img, slope, offset, power, saturation)
    else:
        if log_cdl:
            print("CDL not found")

    img = apply_ocio_processor(img, out_proc)
    return apply_orientation(img, flop_x, flip_y)
