from __future__ import annotations

import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from PySide6.QtGui import QImage

from color_pipeline import build_file_processor, process_frame
from common import fail
from exr_io import prepare_display_image
from qt_viewer import play_sequence_qt


@dataclass(frozen=True)
class SequenceFrame:
    frame: int
    padding: int
    path: str


@dataclass
class SequenceCacheState:
    frames: List[SequenceFrame]
    display_cache: List[Optional[QImage]]
    ready_count: int = 0
    contiguous_count: int = 0
    last_progress_reported: int = 0
    error: Optional[str] = None
    done: bool = False


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
    with os.scandir(seq_dir) as entries:
        for entry in entries:
            if not entry.is_file():
                continue

            stem, ext = os.path.splitext(entry.name)
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
                    path=entry.path,
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


def cache_sequence_worker(
    state: SequenceCacheState,
    frame_queue: "queue.Queue[Tuple[int, SequenceFrame]]",
    in_lut: str,
    out_lut: str,
    flop_x: bool,
    flip_y: bool,
    half: bool,
    ccc_path: Optional[str],
    cdl_values: Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, float]],
    state_lock: threading.Lock,
    stop_event: threading.Event,
) -> None:
    try:
        in_proc = build_file_processor(in_lut)
        out_proc = build_file_processor(out_lut)
        total = len(state.frames)

        while not stop_event.is_set():
            try:
                index, item = frame_queue.get_nowait()
            except queue.Empty:
                break

            processed = process_frame(
                item.path,
                in_proc,
                out_proc,
                flop_x,
                flip_y,
                ccc_path=ccc_path,
                cdl_values=cdl_values,
                log_cdl=False,
            )
            display_ready = prepare_display_image(processed, half)

            progress_count = None
            with state_lock:
                if state.error is not None:
                    frame_queue.task_done()
                    return
                state.display_cache[index] = display_ready
                state.ready_count += 1
                while (
                    state.contiguous_count < total
                    and state.display_cache[state.contiguous_count] is not None
                ):
                    state.contiguous_count += 1

                ready_count = state.ready_count
                if (
                    ready_count == 1
                    or ready_count == total
                    or ready_count // 10 > state.last_progress_reported // 10
                ):
                    state.last_progress_reported = ready_count
                    progress_count = ready_count

            if progress_count is not None:
                print(f"Cached {progress_count}/{total} frames")
            frame_queue.task_done()
    except BaseException as exc:
        with state_lock:
            if state.error is None:
                state.error = str(exc) or exc.__class__.__name__
        stop_event.set()


def cache_sequence_frames(
    state: SequenceCacheState,
    in_lut: str,
    out_lut: str,
    flop_x: bool,
    flip_y: bool,
    half: bool,
    ccc_path: Optional[str],
    cdl_values: Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, float]],
    threads: int,
    state_lock: threading.Lock,
) -> None:
    frame_queue: "queue.Queue[Tuple[int, SequenceFrame]]" = queue.Queue()
    for index, item in enumerate(state.frames):
        frame_queue.put((index, item))

    stop_event = threading.Event()
    worker_count = min(max(1, threads), len(state.frames))
    workers = []
    for _ in range(worker_count):
        worker = threading.Thread(
            target=cache_sequence_worker,
            args=(
                state,
                frame_queue,
                in_lut,
                out_lut,
                flop_x,
                flip_y,
                half,
                ccc_path,
                cdl_values,
                state_lock,
                stop_event,
            ),
            daemon=True,
        )
        workers.append(worker)
        worker.start()

    for worker in workers:
        worker.join()

    with state_lock:
        state.done = True


def play_sequence(
    state: SequenceCacheState,
    fps: float,
    state_lock: threading.Lock,
) -> None:
    if fps <= 0:
        fail("FPS must be greater than 0")
    start_deadline = time.perf_counter() + 60.0
    while True:
        with state_lock:
            if state.error is not None:
                fail(state.error)
            first_frame = state.display_cache[0] if state.display_cache else None
            done = state.done
        if first_frame is not None:
            break
        if done:
            fail("Sequence cache did not produce any frames")
        if time.perf_counter() >= start_deadline:
            fail("Timed out waiting for the first sequence frame")
        time.sleep(0.05)

    try:
        play_sequence_qt(state, fps, state_lock)
    except RuntimeError as exc:
        fail(str(exc))
