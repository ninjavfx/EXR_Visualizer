from __future__ import annotations

import sys
from typing import Callable, Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QKeyEvent, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow


_APP: QApplication | None = None


def ensure_app() -> QApplication:
    global _APP

    app = QApplication.instance()
    if app is None:
        _APP = QApplication(sys.argv[:1])
        app = _APP
    return app


class ImageWindow(QMainWindow):
    def __init__(
        self,
        image: Optional[QImage] = None,
        *,
        title: str,
        on_key: Optional[Callable[[int], bool]] = None,
    ) -> None:
        super().__init__()
        self._on_key = on_key
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(self._label)
        self.resize(1280, 720)
        self.setWindowTitle(title)
        if image is not None:
            self.set_image(image)

    def set_image(self, image: QImage) -> None:
        self._label.setPixmap(QPixmap.fromImage(image))
        self._label.adjustSize()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key in (Qt.Key_Q, Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter):
            self.close()
            return
        if self._on_key is not None and self._on_key(key):
            return
        super().keyPressEvent(event)


def display_qimage(image: QImage, *, title: str) -> None:
    app = ensure_app()
    window = ImageWindow(image, title=title)
    window.show()
    app.exec()


class SequenceWindow(ImageWindow):
    def __init__(
        self,
        state,
        fps: float,
        state_lock,
        *,
        title: str,
    ) -> None:
        super().__init__(title=title, on_key=self._handle_sequence_key)
        self._state = state
        self._state_lock = state_lock
        self._index = 0
        self._playing = True
        self._first_image: QImage | None = None
        self._runtime_error: str | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(max(1, int(round(1000.0 / fps))))
        self._tick()

    def _handle_sequence_key(self, key: int) -> bool:
        if key == Qt.Key_Space:
            self._playing = not self._playing
            self._update_title()
            return True

        available_count = self._available_count()
        if available_count <= 0:
            return False

        if key in (Qt.Key_Comma, Qt.Key_Less):
            self._playing = False
            self._index = (self._index - 1) % available_count
            self._show_current_frame()
            return True

        if key in (Qt.Key_Period, Qt.Key_Greater):
            self._playing = False
            self._index = (self._index + 1) % available_count
            self._show_current_frame()
            return True

        return False

    def _available_count(self) -> int:
        with self._state_lock:
            if self._state.error is not None:
                raise RuntimeError(self._state.error)
            if self._state.done:
                return len(self._state.frames)
            return self._state.contiguous_count

    def _current_image(self) -> QImage | None:
        with self._state_lock:
            if self._state.error is not None:
                raise RuntimeError(self._state.error)
            current = self._state.display_cache[self._index]
            if current is None and self._state.contiguous_count > 0:
                fallback_index = min(self._index, self._state.contiguous_count - 1)
                self._index = fallback_index
                current = self._state.display_cache[fallback_index]
            if current is None and self._first_image is not None:
                current = self._first_image
            elif current is not None and self._first_image is None:
                self._first_image = current
            return current

    def _update_title(self) -> None:
        with self._state_lock:
            ready_count = self._state.ready_count
            done = self._state.done
            frame_number = self._state.frames[self._index].frame
            total = len(self._state.frames)

        suffix = "" if done else f" [{ready_count}/{total} cached]"
        status = "Playing" if self._playing else "Paused"
        self.setWindowTitle(f"EXR Visualizer - {status} - frame {frame_number}{suffix}")

    def _show_current_frame(self) -> None:
        image = self._current_image()
        if image is not None:
            self.set_image(image)
        self._update_title()

    def _tick(self) -> None:
        try:
            image = self._current_image()
            with self._state_lock:
                done = self._state.done
                contiguous_count = self._state.contiguous_count
                total = len(self._state.frames)

            if image is not None:
                self.set_image(image)
            self._update_title()

            available_count = total if done else contiguous_count
            if self._playing and available_count > 0:
                self._index = (self._index + 1) % available_count
        except RuntimeError as exc:
            self._runtime_error = str(exc)
            self.close()


def play_sequence_qt(state, fps: float, state_lock) -> None:
    app = ensure_app()
    window = SequenceWindow(state, fps, state_lock, title="EXR Visualizer")
    window.show()
    app.exec()
    if window._runtime_error is not None:
        raise RuntimeError(window._runtime_error)
