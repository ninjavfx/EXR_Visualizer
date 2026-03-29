from __future__ import annotations

import sys
from typing import Callable, Optional

from PySide6.QtCore import QRect, QTimer, Qt
from PySide6.QtGui import QImage, QKeyEvent, QPainter
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from exr_io import qimage_from_rgb_u8


_APP: QApplication | None = None


def ensure_app() -> QApplication:
    global _APP

    app = QApplication.instance()
    if app is None:
        _APP = QApplication(sys.argv[:1])
        app = _APP
    return app


class ImageWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._image: QImage | None = None

    def set_image(self, image: QImage) -> None:
        self._image = image
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        if self._image is None:
            return

        image = self._image
        scaled_size = image.size()
        if (
            scaled_size.width() > self.width()
            or scaled_size.height() > self.height()
        ):
            scaled_size.scale(self.size(), Qt.KeepAspectRatio)
        x = (self.width() - scaled_size.width()) // 2
        y = (self.height() - scaled_size.height()) // 2
        target = QRect(x, y, scaled_size.width(), scaled_size.height())
        painter.drawImage(target, image)


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
        self._image_widget = ImageWidget()
        self.setCentralWidget(self._image_widget)
        self.resize(1280, 720)
        self.setWindowTitle(title)
        if image is not None:
            self.set_image(image)

    def set_image(self, image: QImage) -> None:
        self._image_widget.set_image(image)

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
        controller,
        *,
        title: str,
    ) -> None:
        super().__init__(title=title, on_key=self._handle_sequence_key)
        self._controller = controller

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(max(1, int(round(1000.0 / controller.fps))))
        self._tick()

    def _handle_sequence_key(self, key: int) -> bool:
        if key == Qt.Key_Space:
            self._controller.toggle_playback()
            self._update_title()
            return True

        if key in (Qt.Key_Comma, Qt.Key_Less):
            self._controller.step(-1)
            self._show_current_frame()
            return True

        if key in (Qt.Key_Period, Qt.Key_Greater):
            self._controller.step(1)
            self._show_current_frame()
            return True

        return False

    def _update_title(self) -> None:
        self.setWindowTitle(self._controller.title())

    def _show_current_frame(self) -> None:
        frame = self._controller.current_frame()
        if frame is not None:
            self.set_image(qimage_from_rgb_u8(frame))
        self._update_title()

    def _tick(self) -> None:
        frame = self._controller.current_frame()
        if frame is not None:
            self.set_image(qimage_from_rgb_u8(frame))
        self._update_title()
        self._controller.advance_if_due()


def play_sequence_qt(controller) -> None:
    app = ensure_app()
    window = SequenceWindow(controller, title="EXR Visualizer")
    window.show()
    app.exec()
