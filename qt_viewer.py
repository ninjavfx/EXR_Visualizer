from __future__ import annotations

import sys
from typing import Callable, Optional

from PySide6.QtCore import QRect, QSize, QTimer, Qt
from PySide6.QtGui import QCloseEvent, QImage, QKeyEvent, QPainter
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
        self._scale = 1.0

    def set_image(self, image: QImage) -> None:
        self._image = image
        self.update()

    def set_scale(self, scale: float) -> None:
        self._scale = max(0.01, float(scale))
        self.update()

    def scaled_image_size(self) -> QSize:
        if self._image is None:
            return QSize()
        width = max(1, int(round(self._image.width() * self._scale)))
        height = max(1, int(round(self._image.height() * self._scale)))
        return QSize(width, height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        if self._image is None:
            return

        image = self._image
        scaled_size = self.scaled_image_size()
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
        on_key: Optional[Callable[[QKeyEvent], bool]] = None,
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

    def set_scale(self, scale: float) -> None:
        self._image_widget.set_scale(scale)

    def resize_to_current_scale(self) -> None:
        target = self._image_widget.scaled_image_size()
        if target.isEmpty():
            return
        chrome = self.size() - self.centralWidget().size()
        self.resize(target + chrome)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        modifiers = event.modifiers()
        if key in (Qt.Key_Q, Qt.Key_Escape):
            self.close()
            return
        if modifiers & Qt.ShiftModifier and key in (Qt.Key_1, Qt.Key_Exclam):
            self.resize_to_current_scale()
            return
        if key == Qt.Key_1:
            self.set_scale(1.0)
            return
        if key == Qt.Key_2:
            self.set_scale(0.5)
            return
        if key == Qt.Key_3:
            self.set_scale(0.25)
            return
        if self._on_key is not None and self._on_key(event):
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
        self._runtime_error: str | None = None
        self._last_frame = None
        self._last_title: str | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(max(1, int(round(1000.0 / controller.fps))))
        self._tick()

    def _handle_sequence_key(self, key: int) -> bool:
        key = key.key()
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
        title = self._controller.title()
        if title != self._last_title:
            self.setWindowTitle(title)
            self._last_title = title

    def _refresh_frame(self) -> None:
        frame = self._controller.current_frame()
        if frame is not None and frame is not self._last_frame:
            self.set_image(qimage_from_rgb_u8(frame))
            self._last_frame = frame
        self._update_title()

    def _show_current_frame(self) -> None:
        self._refresh_frame()

    def _tick(self) -> None:
        try:
            self._refresh_frame()
            self._controller.advance_if_due()
        except BaseException as exc:
            self._runtime_error = str(exc) or exc.__class__.__name__
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._timer.stop()
        self._controller.stop()
        super().closeEvent(event)


def play_sequence_qt(controller) -> None:
    app = ensure_app()
    window = SequenceWindow(controller, title="EXR Visualizer")
    window.show()
    app.exec()
    if window._runtime_error is not None:
        raise RuntimeError(window._runtime_error)
