# coding: utf-8

from PyQt6.QtCore import QSize, QRectF, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap, QPen, QColor, QBrush, QEnterEvent, QMouseEvent
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout,
                             QHBoxLayout, QWidget, QComboBox, QPushButton,
                             QGraphicsView, QProgressBar, QGraphicsScene,
                             QGraphicsSceneMouseEvent,
                             QGraphicsSceneWheelEvent, QFileDialog, QFrame,
                             QGraphicsEllipseItem)
import sys
from typing import Optional
from pathlib import Path
from PIL import Image
import numpy as np
from typing import List
from itertools import batched

from _tracking import detect_spot
from _structure import TimePoint, path_to_time, Quadrant


class CustomScene(QGraphicsScene):
  """"""

  post_detected = pyqtSignal(int, int, int)

  def __init__(self, view: QGraphicsView) -> None:
    """"""

    super().__init__()

    self._view = view

    self._img: Optional[Image] = None
    self._quadrant: Optional[Quadrant] = None

    self._pixmap = QPixmap()
    self.addPixmap(self._pixmap)

    self._rect_pen = QPen(QColor(255, 0, 0, 255), 2, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.BevelJoin)
    self._select_rect = QRectF()
    self._rect_item = self.addRect(self._select_rect, self._rect_pen, QBrush())

    self._circle_brush_unselected = QBrush(QColor(0, 255, 0, 255),
                                           Qt.BrushStyle.SolidPattern)
    self._circle_brush_selected = QBrush(QColor(255, 255, 0, 255),
                                         Qt.BrushStyle.SolidPattern)
    self._circle_1_left = QRectF()
    self._circle_1_right = QRectF()
    self._circle_2_left = QRectF()
    self._circle_2_right = QRectF()
    self._circle_1_left_item = self.addEllipse(self._circle_1_left, QPen(),
                                               self._circle_brush_selected)
    self._circle_1_right_item = self.addEllipse(self._circle_1_right, QPen(),
                                                self._circle_brush_unselected)
    self._circle_2_left_item = self.addEllipse(self._circle_2_left, QPen(),
                                               self._circle_brush_unselected)
    self._circle_2_right_item = self.addEllipse(self._circle_2_right, QPen(),
                                                self._circle_brush_unselected)

    self._circles: List[QGraphicsEllipseItem] = [self._circle_1_left_item,
                                                 self._circle_1_right_item,
                                                 self._circle_2_left_item,
                                                 self._circle_2_right_item]
    self._selected_index: int = 0

    self._view_click_init: Optional[int] = None
    self._view_click_init_y: Optional[int] = None
    self._center_view: Optional[int] = None
    self._center_view_y: Optional[int] = None

    self._last_drag_event: Optional[QGraphicsSceneMouseEvent] = None
    self._zoom_factor: float = 1.3
    self._zoom_level: float = 1.0

    self.post_detected.connect(self.draw_circles)

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

  @pyqtSlot(Quadrant)
  def reload_image(self, quadrant: Quadrant) -> None:
    """"""

    self._quadrant = quadrant
    self._img = Image.open(self._quadrant.path)

    for item in self.items():
      self.removeItem(item)

    self._pixmap.load(str(self._quadrant.path))
    self.addPixmap(self._pixmap)

    self._rect_item = self.addRect(self._select_rect, self._rect_pen, QBrush())
    self._circle_1_left_item = self.addEllipse(
      self._circle_1_left, QPen(),
      self._circle_brush_selected if self._selected_index == 0
      else self._circle_brush_unselected)
    self._circle_1_right_item = self.addEllipse(
      self._circle_1_right, QPen(),
      self._circle_brush_selected if self._selected_index == 1
      else self._circle_brush_unselected)
    self._circle_2_left_item = self.addEllipse(
      self._circle_2_left, QPen(),
      self._circle_brush_selected if self._selected_index == 2
      else self._circle_brush_unselected)
    self._circle_2_right_item = self.addEllipse(
      self._circle_2_right, QPen(),
      self._circle_brush_selected if self._selected_index == 3
      else self._circle_brush_unselected)

    self._circles: List[QGraphicsEllipseItem] = [self._circle_1_left_item,
                                                 self._circle_1_right_item,
                                                 self._circle_2_left_item,
                                                 self._circle_2_right_item]

  @pyqtSlot()
  def draw_circles(self, *_, **__) -> None:
    """"""

    if (self._quadrant.well_1.spot_1 is not None
        and self._quadrant.well_1.spot_1.radius is not None):
      spot = self._quadrant.well_1.spot_1
      self._circle_1_left.setCoords(spot.x - spot.radius,
                                    spot.y - spot.radius,
                                    spot.x + spot.radius,
                                    spot.y + spot.radius)
      self._circle_1_left_item.setRect(self._circle_1_left.normalized())

    if (self._quadrant.well_1.spot_2 is not None
        and self._quadrant.well_1.spot_2.radius is not None):
      spot = self._quadrant.well_1.spot_2
      self._circle_1_right.setCoords(spot.x - spot.radius,
                                     spot.y - spot.radius,
                                     spot.x + spot.radius,
                                     spot.y + spot.radius)
      self._circle_1_right_item.setRect(self._circle_1_right.normalized())

    if (self._quadrant.well_2.spot_1 is not None
        and self._quadrant.well_2.spot_1.radius is not None):
      spot = self._quadrant.well_2.spot_1
      self._circle_2_left.setCoords(spot.x - spot.radius,
                                    spot.y - spot.radius,
                                    spot.x + spot.radius,
                                    spot.y + spot.radius)
      self._circle_2_left_item.setRect(self._circle_2_left.normalized())

    if (self._quadrant.well_2.spot_2 is not None
        and self._quadrant.well_2.spot_2.radius is not None):
      spot = self._quadrant.well_2.spot_2
      self._circle_2_right.setCoords(spot.x - spot.radius,
                                     spot.y - spot.radius,
                                     spot.x + spot.radius,
                                     spot.y + spot.radius)
      self._circle_2_right_item.setRect(self._circle_2_right.normalized())

  @pyqtSlot()
  def reset_circles(self) -> None:
    """"""

    self._circle_1_left.setCoords(0, 0, 0, 0)
    self._circle_1_left_item.setRect(self._circle_1_left.normalized())
    self._circle_1_right.setCoords(0, 0, 0, 0)
    self._circle_1_right_item.setRect(self._circle_1_right.normalized())
    self._circle_2_left.setCoords(0, 0, 0, 0)
    self._circle_2_left_item.setRect(self._circle_2_left.normalized())
    self._circle_2_right.setCoords(0, 0, 0, 0)
    self._circle_2_right_item.setRect(self._circle_2_right.normalized())

  @pyqtSlot(int)
  def highlight_selected_circle(self, value: int) -> None:
    """"""

    self._selected_index = value

    for circle in self._circles:
      circle.setBrush(self._circle_brush_unselected)

    self._circles[value].setBrush(self._circle_brush_selected)

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

      detected = detect_spot(np.array(self._img),
                             *map(int, self._select_rect.getCoords()))
      if detected is not None:
        if self._selected_index == 0:
          self._quadrant.well_1.spot_1 = detected
        elif self._selected_index == 1:
          self._quadrant.well_1.spot_2 = detected
        elif self._selected_index == 2:
          self._quadrant.well_2.spot_1 = detected
        elif self._selected_index == 3:
          self._quadrant.well_2.spot_2 = detected
        self.post_detected.emit(detected.x, detected.y,
                                detected.radius if detected.radius is not None
                                else -1)

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


class SinglePostFrame(QFrame, QWidget):
  """"""

  clicked = pyqtSignal(int)

  def __init__(self, label: str, index: int) -> None:
    """"""

    QFrame.__init__(self)
    QWidget.__init__(self)

    self.selected: bool = False
    self._index: int = index

    # Setting attributes of the main frame
    self.setLineWidth(1)
    self.setFixedHeight(75)
    self.setFrameShadow(QFrame.Shadow.Plain)
    self.setFrameShape(QFrame.Shape.Box)

    # Setting layout of the main frame
    self._v_layout = QVBoxLayout()
    self._h_layout = QHBoxLayout()
    self.setLayout(self._v_layout)

    # Label indicating which post is associated to the frame
    self._title_label = QLabel(label)
    self._title_label.setFixedHeight(30)
    self._v_layout.addWidget(self._title_label)

    self._v_layout.addLayout(self._h_layout)

    # Label displaying the x position of the detected post
    self._x_label = QLabel('X: N/A')
    self._x_label.setFixedHeight(30)
    self._x_label.setMinimumWidth(60)
    self._h_layout.addWidget(self._x_label)

    # Label displaying the y position of the detected post
    self._y_label = QLabel('Y: N/A')
    self._y_label.setFixedHeight(30)
    self._y_label.setMinimumWidth(60)
    self._h_layout.addWidget(self._y_label)

    # Label displaying the radius of the detected post
    self._r_label = QLabel('R: N/A')
    self._r_label.setFixedHeight(30)
    self._r_label.setMinimumWidth(60)
    self._h_layout.addWidget(self._r_label)

    self.clicked.connect(self.select)

  def enterEvent(self, event: QEnterEvent):
    """"""

    if not self.selected:
      self.setLineWidth(2)
    event.accept()

  def leaveEvent(self, event: QEnterEvent):
    """"""

    if not self.selected:
      self.setLineWidth(1)
    event.accept()

  def mouseReleaseEvent(self, event: QMouseEvent) -> None:
    """"""

    self.clicked.emit(self._index)

  @pyqtSlot(int)
  def select(self, _: int) -> None:
    """"""

    self.selected = True
    self.setLineWidth(3)

  @pyqtSlot(int)
  def unselect(self, _: int) -> None:
    """"""

    self.selected = False
    self.setLineWidth(1)

  @pyqtSlot(int, int, int)
  def update_selected_text(self, x: int, y: int, r: int):
    """"""

    if not self.selected:
      return

    self._x_label.setText(f'X: {x}')
    self._y_label.setText(f'Y: {y}')
    if r > 0:
      self._r_label.setText(f'R: {r}')
    else:
      self._r_label.setText('R: N/A')

  @pyqtSlot(int, int, int)
  def update_text(self, x: int, y: int, r: int):
    """"""

    self._x_label.setText(f'X: {x}')
    self._y_label.setText(f'Y: {y}')
    if r > 0:
      self._r_label.setText(f'R: {r}')
    else:
      self._r_label.setText('R: N/A')

  @pyqtSlot()
  def reset_text(self) -> None:
    """"""

    self._x_label.setText('X: N/A')
    self._y_label.setText('Y: N/A')
    self._r_label.setText('R: N/A')


class PostsParentFrame(QFrame):
  """"""

  post_selected = pyqtSignal(int)
  selected_circle_updated = pyqtSignal(int, int, int)
  text_reset = pyqtSignal()

  def __init__(self) -> None:
    """"""

    super().__init__()

    # Layout of the frames in the scrollable area
    self._posts_layout = QVBoxLayout()
    self.setLayout(self._posts_layout)

    # Each detectable spot gets its own frame
    self._post_1_left_frame = SinglePostFrame('Left Well, Left Post', 0)
    self._post_1_left_frame.clicked.connect(self.send_highlight_circle)
    self._posts_layout.addWidget(self._post_1_left_frame)

    self._post_1_right_frame = SinglePostFrame('Left Well, Right Post', 1)
    self._post_1_right_frame.clicked.connect(self.send_highlight_circle)
    self._posts_layout.addWidget(self._post_1_right_frame)

    self._post_2_left_frame = SinglePostFrame('Right Well, Left Post', 2)
    self._post_2_left_frame.clicked.connect(self.send_highlight_circle)
    self._posts_layout.addWidget(self._post_2_left_frame)

    self._post_2_right_frame = SinglePostFrame('Right Well, Right Post', 3)
    self._post_2_right_frame.clicked.connect(self.send_highlight_circle)
    self._posts_layout.addWidget(self._post_2_right_frame)

    self._spacer_frame = QFrame()
    self._spacer_frame.setMinimumHeight(10)
    self._posts_layout.addWidget(self._spacer_frame)

    self._frames = (self._post_1_left_frame, self._post_1_right_frame,
                    self._post_2_left_frame, self._post_2_right_frame)

    self._post_1_left_frame.selected = True
    self._post_1_left_frame.setLineWidth(3)

    self.selected_circle_updated.connect(
      self._post_1_left_frame.update_selected_text)
    self.selected_circle_updated.connect(
      self._post_1_right_frame.update_selected_text)
    self.selected_circle_updated.connect(
      self._post_2_left_frame.update_selected_text)
    self.selected_circle_updated.connect(
      self._post_2_right_frame.update_selected_text)
    self.text_reset.connect(self._post_1_left_frame.reset_text)
    self.text_reset.connect(self._post_1_right_frame.reset_text)
    self.text_reset.connect(self._post_2_left_frame.reset_text)
    self.text_reset.connect(self._post_2_right_frame.reset_text)

    self._post_1_left_frame.clicked.connect(self._post_1_right_frame.unselect)
    self._post_1_left_frame.clicked.connect(self._post_2_left_frame.unselect)
    self._post_1_left_frame.clicked.connect(self._post_2_right_frame.unselect)
    self._post_1_right_frame.clicked.connect(self._post_1_left_frame.unselect)
    self._post_1_right_frame.clicked.connect(self._post_2_left_frame.unselect)
    self._post_1_right_frame.clicked.connect(self._post_2_right_frame.unselect)
    self._post_2_left_frame.clicked.connect(self._post_1_left_frame.unselect)
    self._post_2_left_frame.clicked.connect(self._post_1_right_frame.unselect)
    self._post_2_left_frame.clicked.connect(self._post_2_right_frame.unselect)
    self._post_2_right_frame.clicked.connect(self._post_1_left_frame.unselect)
    self._post_2_right_frame.clicked.connect(self._post_1_right_frame.unselect)
    self._post_2_right_frame.clicked.connect(self._post_2_left_frame.unselect)

  @pyqtSlot(int)
  def send_highlight_circle(self, value: int) -> None:
    """"""

    self.post_selected.emit(value)

  @pyqtSlot(int, int, int)
  def update_selected_text(self, x: int, y: int, r: int) -> None:
    """"""

    self.selected_circle_updated.emit(x, y, r)

  @pyqtSlot()
  def reset_text(self) -> None:
    """"""

    self.text_reset.emit()


class MainWindow(QMainWindow):
  """"""

  images_loaded = pyqtSignal(Quadrant)

  def __init__(self) -> None:
    """"""

    super().__init__()

    self.setWindowTitle('Spot selection')
    self.setMinimumSize(QSize(950, 430))

    self._set_layout()
    self.setCentralWidget(self._main_widget)

    self._img_folder: Optional[Path] = None
    self._timepoints: List[TimePoint] = list()

    self.images_loaded.connect(self._scene.reload_image)
    self.images_loaded.connect(self._scene.reset_circles)
    self.images_loaded.connect(self._posts_list.reset_text)
    self.images_loaded.connect(self._scene.draw_circles)

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
    self._spacer_1.setMinimumWidth(10)
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
    self._spacer_2.setMinimumWidth(10)
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
    self._spacer_3.setMinimumWidth(10)
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
    self._right_label.setFixedSize(QSize(200, 29))
    self._right_panel_layout.addWidget(self._right_label)

    # Scrollable area containing the information on the detected spots
    self._posts_list = PostsParentFrame()
    self._posts_list.setMinimumHeight(350)
    self._right_panel_layout.addWidget(self._posts_list)
    self._posts_list.post_selected.connect(
      self._scene.highlight_selected_circle)
    self._scene.post_detected.connect(self._posts_list.update_selected_text)

    # Process button
    self._process_button = QPushButton()
    self._right_panel_layout.addWidget(self._process_button)

    # Finalize main layout
    self._main_layout.addLayout(self._left_panel_layout, stretch=3)
    self._main_layout.addLayout(self._right_panel_layout, stretch=1)
    self._main_widget = QWidget()
    self._main_widget.setLayout(self._main_layout)

  @pyqtSlot()
  def _load_images(self) -> None:
    """"""

    folder = QFileDialog.getExistingDirectory(self, "Select Image Directory")
    if not folder:
      return

    self._path = Path(folder)
    images = sorted(self._path.glob('*.jpg'), key=path_to_time)

    self._timepoints.clear()
    for path_1, path_2, path_3, path_4 in batched(images, 4):
      self._timepoints.append(TimePoint.parse_paths(path_1, path_2,
                                                    path_3, path_4))

    self.images_loaded.emit(self._timepoints[0].A)


if __name__ == "__main__":

  app = QApplication(sys.argv)

  window = MainWindow()
  window.show()

  sys.exit(app.exec())
