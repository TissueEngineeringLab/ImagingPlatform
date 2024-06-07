# coding: utf-8

from PyQt6.QtCore import QSize, QRectF, Qt
from PyQt6.QtGui import QPixmap, QPen, QColor, QBrush
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout,
                             QHBoxLayout, QWidget, QComboBox, QPushButton,
                             QGraphicsView, QProgressBar, QScrollArea,
                             QGraphicsScene, QGraphicsSceneMouseEvent,
                             QGraphicsSceneWheelEvent, QFileDialog)
import sys
from typing import Optional
from pathlib import Path
from PIL import Image
import numpy as np
from typing import List
from itertools import batched

from _tracking import detect_spot
from _structure import TimePoint, path_to_time


class CustomScene(QGraphicsScene):
  """"""

  def __init__(self, view: QGraphicsView) -> None:
    """"""

    super().__init__()

    self._view = view

    self._path: Optional[Path] = None
    self._img: Optional[Image] = None

    self._pixmap = QPixmap()
    self.addPixmap(self._pixmap)

    self._rect_pen = QPen(QColor(255, 0, 0, 255), 2, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.BevelJoin)
    self._select_rect = QRectF()
    self._rect_item = self.addRect(self._select_rect, self._rect_pen, QBrush())

    self._view_click_init: Optional[int] = None
    self._view_click_init_y: Optional[int] = None
    self._center_view: Optional[int] = None
    self._center_view_y: Optional[int] = None

    self._last_drag_event: Optional[QGraphicsSceneMouseEvent] = None
    self._zoom_factor: float = 1.3
    self._zoom_level: float = 1.0

  def wheelEvent(self, event: QGraphicsSceneWheelEvent):
    """"""

    if self._img is not None:

      if event.delta() > 0:
        self._view.scale(self._zoom_factor, self._zoom_factor)
        self._zoom_level *= self._zoom_factor
      elif event.delta() < 0:
        self._view.scale(1 / self._zoom_factor, 1 / self._zoom_factor)
        self._zoom_level /= self._zoom_factor

      self._rect_pen.setWidthF(2 / self._zoom_level)
      self._rect_item.setPen(self._rect_pen)

    event.accept()

  def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
    """"""

    if Qt.MouseButton.LeftButton & event.button():
      self._leftMousePressEvent(event)
    elif Qt.MouseButton.MiddleButton & event.button():
      self._middleMousePressEvent(event)
    else:
      super().mousePressEvent(event)

  def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
    """"""

    if Qt.MouseButton.LeftButton & event.buttons():
      self._leftMouseMoveEvent(event)
    elif Qt.MouseButton.MiddleButton & event.buttons():
      self._middleMouseMoveEvent(event)
    else:
      super().mousePressEvent(event)

  def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
    """"""

    if Qt.MouseButton.LeftButton & event.button():
      self._leftMouseReleaseEvent(event)
    elif Qt.MouseButton.MiddleButton & event.button():
      self._middleMouseReleaseEvent(event)
    else:
      super().mousePressEvent(event)

  def update_image(self, path: Path) -> None:
    """"""

    self._path = path
    self._img = Image.open(self._path)

    for item in self.items():
      self.removeItem(item)

    self._pixmap.load(str(self._path))
    self.addPixmap(self._pixmap)

    self._rect_item = self.addRect(self._select_rect, self._rect_pen, QBrush())

  def _leftMousePressEvent(self, event: QGraphicsSceneMouseEvent):
    """"""

    if self._img is not None:

      x, y = event.scenePos().x(), event.scenePos().y()
      x_min, y_min, x_max, y_max = self._pixmap.rect().getCoords()
      if x_min <= x <= x_max and y_min <= y <= y_max:
        self._rect_item.show()
        self._select_rect.setCoords(x, y, x, y)
        self._rect_item.setRect(self._select_rect.normalized())

    event.accept()

  def _leftMouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
    """"""

    if self._img is not None:

      x, y = event.scenePos().x(), event.scenePos().y()
      x_min, y_min, x_max, y_max = self._pixmap.rect().getCoords()
      if x_min <= x <= x_max and y_min <= y <= y_max:
        x1, y1, *_ = self._select_rect.getCoords()
        self._select_rect.setCoords(x1, y1, x, y)
        self._rect_item.setRect(self._select_rect.normalized())

    event.accept()

  def _leftMouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
    """"""

    if self._img is not None:

      print(detect_spot(np.array(self._img), *map(int, self._select_rect.getCoords())))

      self._rect_item.hide()
      self._select_rect.setCoords(0, 0, 0, 0)
      self._rect_item.setRect(self._select_rect.normalized())

    event.accept()

  def _middleMousePressEvent(self, event: QGraphicsSceneMouseEvent):
    """"""

    if self._img is not None:

      self._center_view = self._view.viewport().rect().center()
      self._view_click_init = event.screenPos()

    event.accept()

  def _middleMouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
    """"""

    if self._img is not None and self._last_drag_event is None:

      self._last_drag_event = event

      if all(item is not None for item in (self._center_view,
                                           self._view_click_init)):

        delta = event.screenPos() - self._view_click_init

        self._view.centerOn(self._view.mapToScene(self._center_view - delta))

        self._last_drag_event = None

        self._center_view = self._view.viewport().rect().center()
        self._view_click_init = event.screenPos()

      event.accept()

  def _middleMouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
    """"""

    if self._img is not None:

      self._center_view = None
      self._view_click_init = None
      self._last_drag_event = None

    event.accept()


class MainWindow(QMainWindow):
  """"""

  def __init__(self) -> None:
    """"""

    super().__init__()

    self.setWindowTitle('Spot selection')
    self.setMinimumSize(QSize(600, 300))

    self._set_layout()
    self.setCentralWidget(self._main_widget)

    self._img_folder: Optional[Path] = None
    self._timepoints: List[TimePoint] = list()

  def _set_layout(self) -> None:
    """"""

    self._main_layout = QHBoxLayout()
    self._left_panel_layout = QVBoxLayout()
    self._right_panel_layout = QVBoxLayout()
    self._left_title_bar = QHBoxLayout()

    # Title bar on left panel
    self._load_images_button = QPushButton('Load Images')
    self._load_images_button.clicked.connect(self._load_images)
    self._load_images_button.setFixedSize(QSize(130, 29))
    self._left_title_bar.addWidget(self._load_images_button)

    self._spacer_1 = QLabel()
    self._spacer_1.setMaximumWidth(50)
    self._spacer_1.setFixedHeight(29)
    self._left_title_bar.addWidget(self._spacer_1)

    self._time_label = QLabel('Image time:')
    self._time_label.setFixedSize(QSize(85, 29))
    self._left_title_bar.addWidget(self._time_label)

    self._time_combo = QComboBox()
    self._time_combo.setFixedSize(QSize(80, 29))
    self._left_title_bar.addWidget(self._time_combo)

    self._prev_time_button = QPushButton('<')
    self._prev_time_button.setFixedSize(QSize(29, 29))
    self._left_title_bar.addWidget(self._prev_time_button)

    self._next_time_button = QPushButton('>')
    self._next_time_button.setFixedSize(QSize(29, 29))
    self._left_title_bar.addWidget(self._next_time_button)

    self._spacer_2 = QLabel()
    self._spacer_2.setMaximumWidth(50)
    self._spacer_2.setFixedHeight(29)
    self._left_title_bar.addWidget(self._spacer_2)

    self._quadrant_label = QLabel('Image quadrant:')
    self._quadrant_label.setFixedSize(QSize(120, 29))
    self._left_title_bar.addWidget(self._quadrant_label)

    self._quadrant_combo = QComboBox()
    self._quadrant_combo.setFixedSize(QSize(80, 29))
    self._left_title_bar.addWidget(self._quadrant_combo)

    self._prev_quad_button = QPushButton('<')
    self._prev_quad_button.setFixedSize(QSize(29, 29))
    self._left_title_bar.addWidget(self._prev_quad_button)

    self._next_quad_button = QPushButton('>')
    self._next_quad_button.setFixedSize(QSize(29, 29))
    self._left_title_bar.addWidget(self._next_quad_button)

    self._spacer_3 = QLabel()
    self._spacer_3.setFixedHeight(29)
    self._left_title_bar.addWidget(self._spacer_3)

    # Rest of the left panel
    self._left_panel_layout.addLayout(self._left_title_bar, stretch=1)

    self._view = QGraphicsView()
    self._scene = CustomScene(self._view)
    self._view.setScene(self._scene)
    self._left_panel_layout.addWidget(self._view)

    self._progress_bar = QProgressBar()
    self._left_panel_layout.addWidget(self._progress_bar)

    # Right panel
    self._right_label = QLabel('Right panel')
    self._right_panel_layout.addWidget(self._right_label)

    self._posts_list = QScrollArea()
    self._right_panel_layout.addWidget(self._posts_list)

    # Process button
    self._process_button = QPushButton()
    self._right_panel_layout.addWidget(self._process_button)

    # Finalize main layout
    self._main_layout.addLayout(self._left_panel_layout, stretch=3)
    self._main_layout.addLayout(self._right_panel_layout, stretch=1)
    self._main_widget = QWidget()
    self._main_widget.setLayout(self._main_layout)

  def _load_images(self) -> None:
    """"""

    folder = QFileDialog.getExistingDirectory(self, "Select Image Directory")
    if not folder:
      return

    self._path = Path(folder)
    images = sorted(self._path.glob('*.jpg'), key=path_to_time)
    for path_1, path_2, path_3, path_4 in batched(images, 4):
      self._timepoints.append(TimePoint.parse_paths(path_1, path_2,
                                                    path_3, path_4))

    self._scene.update_image(self._timepoints[0].A.path)


if __name__ == "__main__":

  app = QApplication(sys.argv)

  window = MainWindow()
  window.show()

  sys.exit(app.exec())
