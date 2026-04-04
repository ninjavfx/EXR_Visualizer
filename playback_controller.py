from __future__ import annotations

import time


class PlaybackController:
    def __init__(self, state, fps: float, state_lock) -> None:
        if fps <= 0:
            raise RuntimeError("FPS must be greater than 0")

        self._state = state
        self._state_lock = state_lock
        self.fps = fps
        self.frame_delay = 1.0 / fps
        self.index = 0
        self.is_playing = True
        self.next_deadline = time.perf_counter() + self.frame_delay
        self._first_frame = None

    def ensure_first_frame(self, timeout_seconds: float = 60.0) -> None:
        deadline = time.perf_counter() + timeout_seconds
        while True:
            frame = self.current_frame()
            with self._state_lock:
                done = self._state.done
            if frame is not None:
                return
            if done:
                raise RuntimeError("Sequence cache did not produce any frames")
            if time.perf_counter() >= deadline:
                raise RuntimeError("Timed out waiting for the first sequence frame")
            time.sleep(0.05)

    def current_frame(self):
        with self._state_lock:
            if self._state.error is not None:
                raise RuntimeError(self._state.error)
            current = self._state.display_cache[self.index]
            if current is None and self._state.contiguous_count > 0:
                fallback_index = min(self.index, self._state.contiguous_count - 1)
                self.index = fallback_index
                current = self._state.display_cache[fallback_index]
            if current is None and self._first_frame is not None:
                return self._first_frame
            if current is not None and self._first_frame is None:
                self._first_frame = current
            return current

    def title(self) -> str:
        with self._state_lock:
            if self._state.error is not None:
                raise RuntimeError(self._state.error)
            ready_count = self._state.ready_count
            done = self._state.done
            frame_number = self._state.frames[self.index].frame
            total = len(self._state.frames)

        suffix = "" if done else f" [{ready_count}/{total} cached]"
        status = "Playing" if self.is_playing else "Paused"
        return f"EXR Visualizer - {status} - frame {frame_number}{suffix}"

    def available_count(self) -> int:
        with self._state_lock:
            if self._state.error is not None:
                raise RuntimeError(self._state.error)
            if self._state.done:
                return len(self._state.frames)
            return self._state.contiguous_count

    def stop(self) -> None:
        self._state.stop_event.set()

    def toggle_playback(self) -> None:
        self.is_playing = not self.is_playing
        self.next_deadline = time.perf_counter() + self.frame_delay

    def step(self, delta: int) -> None:
        available_count = self.available_count()
        if available_count <= 0:
            return
        self.is_playing = False
        self.index = (self.index + delta) % available_count
        self.next_deadline = time.perf_counter() + self.frame_delay

    def jump_to_start(self) -> None:
        if self.available_count() <= 0:
            return
        self.is_playing = False
        self.index = 0
        self.next_deadline = time.perf_counter() + self.frame_delay

    def jump_to_end(self) -> None:
        available_count = self.available_count()
        if available_count <= 0:
            return
        self.is_playing = False
        self.index = available_count - 1
        self.next_deadline = time.perf_counter() + self.frame_delay

    def wait_ms(self) -> int:
        if not self.is_playing:
            return 50
        now = time.perf_counter()
        return max(1, int((self.next_deadline - now) * 1000.0))

    def advance_if_due(self) -> None:
        available_count = self.available_count()
        if not self.is_playing or available_count <= 0:
            return

        now = time.perf_counter()
        if now >= self.next_deadline + self.frame_delay:
            self.next_deadline = now + self.frame_delay
        else:
            self.next_deadline += self.frame_delay
        self.index = (self.index + 1) % available_count
