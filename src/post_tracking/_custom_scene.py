# coding: utf-8

from PyQt6.QtWidgets import (QGraphicsScene, QGraphicsSceneMouseEvent,
                             QGraphicsSceneWheelEvent, QGraphicsEllipseItem,
                             QGraphicsView)
from PyQt6.QtGui import QPixmap, QPen, QColor, QBrush
from PyQt6.QtCore import QRectF, Qt, pyqtSignal, pyqtSlot
from typing import List, Optional
from PIL import Image
import numpy as np

from ._tracking import detect_spot
from ._structure import Quadrant


class CustomScene(QGraphicsScene):
  """"""

  post_detected_in_scene = pyqtSignal(int, int, int)

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
    self._zoom_index: int = 0

    self.post_detected_in_scene.connect(self.draw_circles_in_scene)

  def wheelEvent(self, event: QGraphicsSceneWheelEvent):
    """"""

    if self._img is not None:

      if event.delta() > 0 and self._zoom_index < 10:
        self._view.scale(self._zoom_factor, self._zoom_factor)
        self._zoom_level *= self._zoom_factor
        self._zoom_index += 1
      elif event.delta() < 0 and self._zoom_index > -10:
        self._view.scale(1 / self._zoom_factor, 1 / self._zoom_factor)
        self._zoom_level /= self._zoom_factor
        self._zoom_index -= 1

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
  def reload_image_in_scene(self, quadrant: Quadrant) -> None:
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
  def draw_circles_in_scene(self, *_, **__) -> None:
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
  def reset_circles_in_scene(self) -> None:
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
  def highlight_selected_circle_in_scene(self, value: int) -> None:
    """"""

    self._selected_index = value

    for circle in self._circles:
      circle.setBrush(self._circle_brush_unselected)

    self._circles[value].setBrush(self._circle_brush_selected)

  @pyqtSlot(int)
  def delete_circle_in_scene(self, index: int) -> None:
    """"""

    if index == 0:
      self._circle_1_left.setCoords(0, 0, 0, 0)
      self._circle_1_left_item.setRect(self._circle_1_left.normalized())
    elif index == 1:
      self._circle_1_right.setCoords(0, 0, 0, 0)
      self._circle_1_right_item.setRect(self._circle_1_right.normalized())
    elif index == 2:
      self._circle_2_left.setCoords(0, 0, 0, 0)
      self._circle_2_left_item.setRect(self._circle_2_left.normalized())
    elif index == 3:
      self._circle_2_right.setCoords(0, 0, 0, 0)
      self._circle_2_right_item.setRect(self._circle_2_right.normalized())

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
        self.post_detected_in_scene.emit(detected.x, detected.y,
                                         detected.radius if detected.radius
                                         is not None else -1)

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
