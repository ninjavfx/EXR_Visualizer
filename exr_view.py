#!/usr/bin/env python3
"""Display EXR with LUT + optional CDL pipeline.

Pipeline order:
1) input LUT (.csp)
2) CDL from first discovered .ccc (optional)
3) output LUT (.cube)
"""

from __future__ import annotations

import os
import threading

from cli import parse_args
from color_pipeline import (
    build_file_processor,
    find_ccc,
    find_luts_config,
    parse_ccc,
    parse_luts_config,
    process_frame,
)
from common import fail
from exr_io import display_image, save_image
from sequence_playback import (
    SequenceCacheState,
    cache_sequence_frames,
    is_sequence_request,
    parse_frame_range,
    play_sequence,
    resolve_sequence_frames,
)


def main() -> None:
    args = parse_args()
    if args.fps <= 0:
        fail("FPS must be greater than 0")
    if args.threads <= 0:
        fail("Threads must be greater than 0")

    exr_path = os.path.abspath(args.exr_path)
    frame_range = parse_frame_range(args.frame_range)
    sequence_mode = is_sequence_request(args.exr_path)

    luts_path = find_luts_config(os.getcwd())
    in_lut, out_lut = parse_luts_config(luts_path)

    print(f"Using .luts: {luts_path}")
    print(f"Input LUT: {in_lut}")
    print(f"Output LUT: {out_lut}")

    if sequence_mode:
        if args.save:
            fail("Sequence playback does not support --save")
        if args.no_display:
            fail("Sequence playback requires display; --no-display is not supported")

        frames = resolve_sequence_frames(args.exr_path, frame_range)
        ccc_path = find_ccc(frames[0].path)
        cdl_values = parse_ccc(ccc_path) if ccc_path else None

        if ccc_path:
            print(f"Using CDL: {ccc_path}")
        else:
            print("CDL not found")

        print(
            f"Sequence frames: {frames[0].frame}..{frames[-1].frame} "
            f"({len(frames)} total, playing while caching at {args.fps:g} fps, "
            f"{args.threads} thread{'s' if args.threads != 1 else ''})"
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
                in_lut,
                out_lut,
                args.flop_x,
                args.flip_y,
                args.half,
                ccc_path,
                cdl_values,
                args.threads,
                state_lock,
            ),
            daemon=True,
        )
        loader.start()

        play_sequence(state, args.fps, state_lock)
        return

    in_proc = build_file_processor(in_lut)
    out_proc = build_file_processor(out_lut)

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
