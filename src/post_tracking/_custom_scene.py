# coding: utf-8

from PyQt6.QtWidgets import (QGraphicsScene, QGraphicsSceneMouseEvent,
                             QGraphicsSceneWheelEvent, QGraphicsEllipseItem,
                             QGraphicsView)
from PyQt6.QtGui import QPixmap, QPen, QColor, QBrush
from PyQt6.QtCore import QRectF, Qt, pyqtSignal, pyqtSlot, QPoint
from typing import List, Optional
from PIL import Image
import numpy as np

from ._tracking import detect_spot
from ._structure import Quadrant


class CustomScene(QGraphicsScene):
  """Subclass of QGraphicsScene implementing spot drawing and detection, and
  overriding mouse-related events for more interactivity."""

  post_detected_in_scene = pyqtSignal(int, int, int)
  """Signal emitted whenever a post is detected after manual selection of an 
  area to search by the user"""

  def __init__(self, view: QGraphicsView) -> None:
    """Sets the attributes used in this class.

    Args:
      view: The parent QGraphicsView in which the scene is included.
    """

    # Initialize the parent class and handle the argument
    super().__init__()
    self._view = view

    # These attributes are dynamically set
    self._img: Optional[Image] = None
    self._quadrant: Optional[Quadrant] = None
    self._selected_index: int = 0
    self._view_click_init: Optional[QPoint] = None
    self._center_view: Optional[QPoint] = None
    self._last_drag_event: Optional[QGraphicsSceneMouseEvent] = None

    # Create a QPixmap containing the image to display
    self._pixmap = QPixmap()
    self.addPixmap(self._pixmap)

    # Define color and style for the detection box
    self._rect_pen = QPen(QColor(255, 0, 0, 255), 2, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.BevelJoin)
    self._select_rect = QRectF()
    self._rect_item = self.addRect(self._select_rect, self._rect_pen, QBrush())

    # Define color and style for the detected spots
    self._circle_brush_unselected = QBrush(QColor(0, 255, 0, 255),
                                           Qt.BrushStyle.SolidPattern)
    self._circle_brush_selected = QBrush(QColor(255, 255, 0, 255),
                                         Qt.BrushStyle.SolidPattern)

    # Create rectangles containing the circles to draw
    self._circle_1_left = QRectF()
    self._circle_1_right = QRectF()
    self._circle_2_left = QRectF()
    self._circle_2_right = QRectF()

    # Create the ellipses representing the circles to draw
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

    # Constants driving the initial state and dynamic behavior when zooming
    self._zoom_factor: float = 1.3
    self._zoom_level: float = 1.0
    self._zoom_index: int = 0

    # Draw a circle whenever it is detected
    self.post_detected_in_scene.connect(self.draw_circles_in_scene)

  def wheelEvent(self, event: QGraphicsSceneWheelEvent) -> None:
    """Overriding the default wheel event to make it zoom in or out instead of
    scrolling.

    Args:
      event: The event generated whenever the wheel is being scrolled.
    """

    if self._img is not None:

      # Case when the wheel is being scrolled upwards
      if event.delta() > 0 and self._zoom_index < 10:
        self._view.scale(self._zoom_factor, self._zoom_factor)
        self._zoom_level *= self._zoom_factor
        self._zoom_index += 1
      # Case when the wheel is being scrolled downwards
      elif event.delta() < 0 and self._zoom_index > -10:
        self._view.scale(1 / self._zoom_factor, 1 / self._zoom_factor)
        self._zoom_level /= self._zoom_factor
        self._zoom_index -= 1

      # Adjust the size of the detection box according to the zoom level
      self._rect_pen.setWidthF(2 / self._zoom_level)
      self._rect_item.setPen(self._rect_pen)

    # Accept event to prevent normal handling of it
    event.accept()

  def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
    """Triage the incoming mouse press events, so that some of them are
    affected custom actions.

    Args:
      event: The event generated whenever a mouse button is being pressed over
        the scene.
    """

    # Handle left mouse button press
    if Qt.MouseButton.LeftButton & event.button():
      self._leftMousePressEvent(event)
    # Handle middle mouse button press
    elif Qt.MouseButton.MiddleButton & event.button():
      self._middleMousePressEvent(event)
    # Use default behavior for any other button pressed
    else:
      super().mousePressEvent(event)

  def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
    """Triage the incoming mouse move events, so that some of them are
    affected custom actions.

    Args:
      event: The event generated whenever the mouse is being moved over the
        scene.
    """

    # Handle mouse moved while left button pressed
    if Qt.MouseButton.LeftButton & event.buttons():
      self._leftMouseMoveEvent(event)
    # Handle mouse moved while middle button pressed
    elif Qt.MouseButton.MiddleButton & event.buttons():
      self._middleMouseMoveEvent(event)
    # Use default behavior for any other movement
    else:
      super().mousePressEvent(event)

  def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
    """Triage the incoming mouse release events, so that some of them are
    affected custom actions.

    Args:
      event: The event generated whenever a mouse button is being released over
        the scene.
    """

    # Handle left mouse button release
    if Qt.MouseButton.LeftButton & event.button():
      self._leftMouseReleaseEvent(event)
    # Handle middle mouse button release
    elif Qt.MouseButton.MiddleButton & event.button():
      self._middleMouseReleaseEvent(event)
    # Use default behavior for any other button released
    else:
      super().mousePressEvent(event)

  @pyqtSlot(Quadrant)
  def reload_image_in_scene(self, quadrant: Quadrant) -> None:
    """Called whenever a new image is loaded.

    Displays the image in the scene, and draws any spots previously detected.

    Args:
      quadrant: The Quadrant object containing all the necessary information
        for loading the image and the detected spots.
    """

    # Set the current quadrant and image
    self._quadrant = quadrant
    self._img = Image.open(self._quadrant.path)

    # Delete all the previously drawn objects
    for item in self.items():
      self.removeItem(item)

    # Draw the new image on the scene
    self._pixmap.load(str(self._quadrant.path))
    self.addPixmap(self._pixmap)

    # Re-draw the selection rectangle on the scene, empty for now
    self._rect_item = self.addRect(self._select_rect, self._rect_pen, QBrush())

    # Re-draw the detected circles on the scene, empty for now
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
  def draw_circles_in_scene(self) -> None:
    """Re-draws all the detected circles on top of the displayed image."""

    # Left spot of the left well
    if (self._quadrant.well_1.spot_1 is not None
        and self._quadrant.well_1.spot_1.radius is not None):
      spot = self._quadrant.well_1.spot_1
      self._circle_1_left.setCoords(spot.x - spot.radius,
                                    spot.y - spot.radius,
                                    spot.x + spot.radius,
                                    spot.y + spot.radius)
      self._circle_1_left_item.setRect(self._circle_1_left.normalized())

    # Right spot of the left well
    if (self._quadrant.well_1.spot_2 is not None
        and self._quadrant.well_1.spot_2.radius is not None):
      spot = self._quadrant.well_1.spot_2
      self._circle_1_right.setCoords(spot.x - spot.radius,
                                     spot.y - spot.radius,
                                     spot.x + spot.radius,
                                     spot.y + spot.radius)
      self._circle_1_right_item.setRect(self._circle_1_right.normalized())

    # Left spot of the right well
    if (self._quadrant.well_2.spot_1 is not None
        and self._quadrant.well_2.spot_1.radius is not None):
      spot = self._quadrant.well_2.spot_1
      self._circle_2_left.setCoords(spot.x - spot.radius,
                                    spot.y - spot.radius,
                                    spot.x + spot.radius,
                                    spot.y + spot.radius)
      self._circle_2_left_item.setRect(self._circle_2_left.normalized())

    # Right spot of the right well
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
    """Deletes and resets all the circles draw on top of the image."""

    # Left spot of the left well
    self._circle_1_left.setCoords(0, 0, 0, 0)
    self._circle_1_left_item.setRect(self._circle_1_left.normalized())
    # Right spot of the left well
    self._circle_1_right.setCoords(0, 0, 0, 0)
    self._circle_1_right_item.setRect(self._circle_1_right.normalized())
    # Left spot of the right well
    self._circle_2_left.setCoords(0, 0, 0, 0)
    self._circle_2_left_item.setRect(self._circle_2_left.normalized())
    # Right spot of the right well
    self._circle_2_right.setCoords(0, 0, 0, 0)
    self._circle_2_right_item.setRect(self._circle_2_right.normalized())

  @pyqtSlot(int)
  def highlight_selected_circle_in_scene(self, value: int) -> None:
    """Highlights the selected circle, by changing its color.

    Args:
      value: The index of the circle to highlight.
    """

    self._selected_index = value

    # First unselects all the circles
    for circle in self._circles:
      circle.setBrush(self._circle_brush_unselected)

    # Then only highlights the selected one
    self._circles[value].setBrush(self._circle_brush_selected)

  @pyqtSlot(int)
  def delete_circle_in_scene(self, index: int) -> None:
    """Deletes and resets one specified circle in the scene.

    Args:
      index: The index of the circle to delete.
    """

    # Left spot of the left well
    if index == 0:
      self._circle_1_left.setCoords(0, 0, 0, 0)
      self._circle_1_left_item.setRect(self._circle_1_left.normalized())
    # Right spot of the left well
    elif index == 1:
      self._circle_1_right.setCoords(0, 0, 0, 0)
      self._circle_1_right_item.setRect(self._circle_1_right.normalized())
    # Left spot of the right well
    elif index == 2:
      self._circle_2_left.setCoords(0, 0, 0, 0)
      self._circle_2_left_item.setRect(self._circle_2_left.normalized())
    # Right spot of the right well
    elif index == 3:
      self._circle_2_right.setCoords(0, 0, 0, 0)
      self._circle_2_right_item.setRect(self._circle_2_right.normalized())

  def _leftMousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
    """Called when the left mouse button is pressed over the scene.

    Enables and draws the selection rectangle on top of the displayed image.

    Args:
      event: The event emitted by the mouse button press.
    """

    if self._img is not None:

      # Get the mouse and overall image coordinates
      x, y = event.scenePos().x(), event.scenePos().y()
      x_min, y_min, x_max, y_max = self._pixmap.rect().getCoords()
      # Check that the click happened within the image
      if x_min <= x <= x_max and y_min <= y <= y_max:
        # Enable and draw the selection rectangle
        self._rect_item.show()
        self._select_rect.setCoords(x, y, x, y)
        self._rect_item.setRect(self._select_rect.normalized())

    # Accept event to make sure it's not handled elsewhere
    event.accept()

  def _leftMouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
    """Called when the mouse is being moved over the scene with the left button
    pressed.

    Updates the coordinates of the selection rectangle to follow the moving
    mouse.

    Args:
      event: The event emitted by the mouse button movement.
    """

    if self._img is not None:

      # Get the mouse and overall image coordinates
      x, y = event.scenePos().x(), event.scenePos().y()
      x_min, y_min, x_max, y_max = self._pixmap.rect().getCoords()
      # Check that the mouse is still within the image
      if x_min <= x <= x_max and y_min <= y <= y_max:
        # Update the selection rectangle coordinates
        x1, y1, *_ = self._select_rect.getCoords()
        self._select_rect.setCoords(x1, y1, x, y)
        self._rect_item.setRect(self._select_rect.normalized())

    # Accept event to make sure it's not handled elsewhere
    event.accept()

  def _leftMouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
    """Called when the left mouse button is released, after moving the mouse
    on the scene with the left button pressed.

    Triggers spot detection in the selected subframe of the image, saves the
    detected spot, and sends a signal to display it.

    Args:
      event: The event emitted by the mouse button release.
    """

    if self._img is not None:

      # Performing spot detection in the selected subframe
      detected = detect_spot(np.array(self._img),
                             *map(int, self._select_rect.getCoords()))

      # Affect the detected spot to the correct well and position
      if detected is not None:
        if self._selected_index == 0:
          self._quadrant.well_1.spot_1 = detected
        elif self._selected_index == 1:
          self._quadrant.well_1.spot_2 = detected
        elif self._selected_index == 2:
          self._quadrant.well_2.spot_1 = detected
        elif self._selected_index == 3:
          self._quadrant.well_2.spot_2 = detected

        # Emit signal to indicate that a spot was detected
        self.post_detected_in_scene.emit(detected.x, detected.y,
                                         detected.radius if detected.radius
                                         is not None else -1)

      # Reset and hide the selection rectangle
      self._rect_item.hide()
      self._select_rect.setCoords(0, 0, 0, 0)
      self._rect_item.setRect(self._select_rect.normalized())

    # Accept event to make sure it's not handled elsewhere
    event.accept()

  def _middleMousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
    """Called when the middle mouse button is pressed over the scene.

    Saves the coordinates of the click for later dragging the image.

    Args:
      event: The event emitted by the mouse button press.
    """

    if self._img is not None:

      self._center_view = self._view.viewport().rect().center()
      self._view_click_init = event.screenPos()

    # Accept event to make sure it's not handled elsewhere
    event.accept()

  def _middleMouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
    """Called when the mouse is being moved over the scene with the middle
    button pressed.

    Re-centers the scene so that the image moves along with the mouse movement.

    Args:
      event: The event emitted by the mouse button movement.
    """

    if self._img is not None and self._last_drag_event is None:

      # Workaround to avoid infinite recursion, as re-centering the image will
      # cause mouse movement
      self._last_drag_event = event

      # Make sure the drag operation was properly initialized
      if self._center_view is not None and self._view_click_init is not None:

        # Calculate position delta and re-center scene accordingly
        delta = event.screenPos() - self._view_click_init
        self._view.centerOn(self._view.mapToScene(self._center_view - delta))

        self._last_drag_event = None

        # Update the saved information for the next mouse movement
        self._center_view = self._view.viewport().rect().center()
        self._view_click_init = event.screenPos()

      # Accept event to make sure it's not handled elsewhere
      event.accept()

  def _middleMouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
    """Called when the middle mouse button is released, after moving the mouse
    on the scene with the middle button pressed.

    Stops the drag operation and resets the associated attributes.

    Args:
      event: The event emitted by the mouse button release.
    """

    if self._img is not None:

      self._center_view = None
      self._view_click_init = None
      self._last_drag_event = None

    # Accept event to make sure it's not handled elsewhere
    event.accept()
