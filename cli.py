from __future__ import annotations

import argparse


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
    parser.add_argument(
        "-threads",
        "--threads",
        type=int,
        default=1,
        help="Sequence cache worker threads (default: 1; try 2 or 4 on local NVMe)",
    )
    return parser.parse_args()
