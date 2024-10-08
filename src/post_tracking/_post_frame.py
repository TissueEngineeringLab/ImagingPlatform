# coding: utf-8

"""This file contains the classes used for managing the display of information
on the detected spots in the right section of the interface."""

from PyQt6.QtGui import QEnterEvent, QMouseEvent
from PyQt6.QtWidgets import (QFrame, QStyle, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton)
from PyQt6.QtCore import pyqtSignal, pyqtSlot

from ._structure import Quadrant


class SinglePostFrame(QFrame, QWidget):
  """Child of QFrame displaying information about a single post."""

  clicked = pyqtSignal(int)
  """Signal emitted when the frame is clicked in the interface."""
  switch_next = pyqtSignal()
  """Signal emitted when the frame is selected and considers that the next 
  frame should be selected instead."""
  deleted = pyqtSignal(int)
  """Signal emitted when the delete button of the frame is clicked."""

  def __init__(self, label: str, index: int) -> None:
    """Sets the layout of the frame and handles the passed arguments.

    Args:
      label: Label displayed at the top of the frame for identifying it.
      index: The index of the spot the frame is displaying information about.
    """

    # Initializing the parent classes
    QFrame.__init__(self)
    QWidget.__init__(self)

    self.selected: bool = False
    self.index: int = index

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

    # Button for deleting a detected spot and all the associated information
    self._delete_button = QPushButton()
    self._delete_button.setIcon(self.style().standardIcon(
      QStyle.StandardPixmap.SP_TrashIcon))
    self._delete_button.clicked.connect(self.reset_text)
    self._delete_button.clicked.connect(self.delete_post)
    self._delete_button.setFixedHeight(30)
    self._delete_button.setFixedWidth(30)
    self._h_layout.addWidget(self._delete_button)

    # Upon clicking on the frame, make it the new selected one
    self.clicked.connect(self.select_entry)

  def enterEvent(self, event: QEnterEvent) -> None:
    """Called when the mouse hovers the frame area.

    Thickens the edges of the frame to highlight it.

    Args:
      event: The event emitted when the mouse enters the frame area.
    """

    if not self.selected:
      self.setLineWidth(2)
    # Accept event to make sure it's not handled elsewhere
    event.accept()

  def leaveEvent(self, event: QEnterEvent) -> None:
    """Called when the mouse exits the frame area.

    Puts the edges of the frame back to normal thickness to remove the
    highlighting.

    Args:
      event: The event emitted when the mouse leaves the frame area.
    """

    if not self.selected:
      self.setLineWidth(1)
    # Accept event to make sure it's not handled elsewhere
    event.accept()

  def mouseReleaseEvent(self, event: QMouseEvent) -> None:
    """Called when clicking on the frame.

    Triggers a clicked signal.

    Args:
      event: Event emitted when clicking on the frame.
    """

    self.clicked.emit(self.index)

  @pyqtSlot()
  def soft_select(self) -> None:
    """Alternative to mouseReleaseEvent, for selecting the frame from the
    software rather than using the mouse."""

    self.clicked.emit(self.index)

  @pyqtSlot()
  def select_entry(self) -> None:
    """Sets the selected status of the frame, and highlights its edges to
    signal it."""

    self.selected = True
    self.setLineWidth(3)

  @pyqtSlot()
  def unselect_entry(self) -> None:
    """Withdraws the selected status of the frame, and puts its edges back to
    normal width to signal it."""

    self.selected = False
    self.setLineWidth(1)

  @pyqtSlot(int, int, int, int)
  def update_text(self, index: int, x: int, y: int, r: int) -> None:
    """Updates the text displayed in the frame after a spot is detected in the
    scene, or a new image is loaded.

    Args:
      index: The index of the spot whose text to update.
      x: The x position of the detected spot.
      y: The y position of the detected spot.
      r: The radius of the detected spot.
    """

    # Proceed only if the frame index and the post index match
    if index != self.index:
      return

    # Update the displayed text
    self._x_label.setText(f'X: {x}')
    self._y_label.setText(f'Y: {y}')
    if r > 0:
      self._r_label.setText(f'R: {r}')
    else:
      self._r_label.setText('R: N/A')

    # Switch to the next frame because we're done with this post
    self.switch_next.emit()

  @pyqtSlot()
  def reset_text(self) -> None:
    """Resets the displayed text."""

    self._x_label.setText('X: N/A')
    self._y_label.setText('Y: N/A')
    self._r_label.setText('R: N/A')

  @pyqtSlot()
  def delete_post(self) -> None:
    """Emits a deleted signal when the delete button is clicked."""

    self.deleted.emit(self.index)


class PostsParentFrame(QFrame):
  """Child of QFrame managing four SinglePostFrame representing each a possible
  detected spot."""

  post_selected_in_table = pyqtSignal(int)
  """Signal emitted when a post is selected in the table by clicking with the 
  mouse."""
  spot_params_updated = pyqtSignal(int, int, int, int)
  """Signal emitted when a spot is detected in the scene."""
  reset_text_requested = pyqtSignal()
  """Signal emitted when the displayed text should be reset for all posts."""
  deleted_post = pyqtSignal(int)
  """Signal emitted when a post is reset by clicking on its delete button."""

  def __init__(self) -> None:
    """Sets the layout, and connects the slots to the signals."""

    # Initialize the parent class
    super().__init__()

    # Layout of the frames in the scrollable area
    self._posts_layout = QVBoxLayout()
    self.setLayout(self._posts_layout)

    # Each detectable spot gets its own frame
    # Left post of the left well
    self._post_1_l_frame = SinglePostFrame('Left Well, Left Post', 0)
    self._post_1_l_frame.clicked.connect(self.send_highlight_circle_to_scene)
    self._post_1_l_frame.deleted.connect(self.post_deleted)
    self._posts_layout.addWidget(self._post_1_l_frame)

    # Right post of the left well
    self._post_1_r_frame = SinglePostFrame('Left Well, Right Post', 1)
    self._post_1_r_frame.clicked.connect(self.send_highlight_circle_to_scene)
    self._post_1_r_frame.deleted.connect(self.post_deleted)
    self._posts_layout.addWidget(self._post_1_r_frame)

    # Left post of the right well
    self._post_2_l_frame = SinglePostFrame('Right Well, Left Post', 2)
    self._post_2_l_frame.clicked.connect(self.send_highlight_circle_to_scene)
    self._post_2_l_frame.deleted.connect(self.post_deleted)
    self._posts_layout.addWidget(self._post_2_l_frame)

    # Right post of the right well
    self._post_2_r_frame = SinglePostFrame('Right Well, Right Post', 3)
    self._post_2_r_frame.clicked.connect(self.send_highlight_circle_to_scene)
    self._post_2_r_frame.deleted.connect(self.post_deleted)
    self._posts_layout.addWidget(self._post_2_r_frame)

    # Tuple used for convenience later
    self._frames = (self._post_1_l_frame, self._post_1_r_frame,
                    self._post_2_l_frame, self._post_2_r_frame)

    # Spacer at the end of the frame for layout purpose
    self._spacer_frame = QFrame()
    self._spacer_frame.setMinimumHeight(10)
    self._posts_layout.addWidget(self._spacer_frame)

    # By default, the left spot of the left well is selected
    self._post_1_l_frame.selected = True
    self._post_1_l_frame.setLineWidth(3)

    # Connecting the signals and slots for updating text
    self.spot_params_updated.connect(self._post_1_l_frame.update_text)
    self.spot_params_updated.connect(self._post_1_r_frame.update_text)
    self.spot_params_updated.connect(self._post_2_l_frame.update_text)
    self.spot_params_updated.connect(self._post_2_r_frame.update_text)

    # Connecting the signals and slots for resetting text
    self.reset_text_requested.connect(self._post_1_l_frame.reset_text)
    self.reset_text_requested.connect(self._post_1_r_frame.reset_text)
    self.reset_text_requested.connect(self._post_2_l_frame.reset_text)
    self.reset_text_requested.connect(self._post_2_r_frame.reset_text)

    # Connecting the signals and slots for collaboratively managing entry
    # selection
    self._post_1_l_frame.clicked.connect(self._post_1_r_frame.unselect_entry)
    self._post_1_l_frame.clicked.connect(self._post_2_l_frame.unselect_entry)
    self._post_1_l_frame.clicked.connect(self._post_2_r_frame.unselect_entry)
    self._post_1_r_frame.clicked.connect(self._post_1_l_frame.unselect_entry)
    self._post_1_r_frame.clicked.connect(self._post_2_l_frame.unselect_entry)
    self._post_1_r_frame.clicked.connect(self._post_2_r_frame.unselect_entry)
    self._post_2_l_frame.clicked.connect(self._post_1_l_frame.unselect_entry)
    self._post_2_l_frame.clicked.connect(self._post_1_r_frame.unselect_entry)
    self._post_2_l_frame.clicked.connect(self._post_2_r_frame.unselect_entry)
    self._post_2_r_frame.clicked.connect(self._post_1_l_frame.unselect_entry)
    self._post_2_r_frame.clicked.connect(self._post_1_r_frame.unselect_entry)
    self._post_2_r_frame.clicked.connect(self._post_2_l_frame.unselect_entry)

    # Still managing entry selection collaboratively
    self._post_1_l_frame.switch_next.connect(self._post_1_r_frame.soft_select)
    self._post_1_r_frame.switch_next.connect(self._post_2_l_frame.soft_select)
    self._post_2_l_frame.switch_next.connect(self._post_2_r_frame.soft_select)
    self._post_2_r_frame.switch_next.connect(self._post_1_l_frame.soft_select)

  @pyqtSlot(int)
  def send_highlight_circle_to_scene(self, value: int) -> None:
    """Called when a frame is clicked, to signal the scene that a new post was
    selected and should be highlighted accordingly.

    Args:
      value: Index of the circle to highlight.
    """

    self.post_selected_in_table.emit(value)

  @pyqtSlot(int, int, int)
  def update_post_text(self, x: int, y: int, r: int) -> None:
    """Called when a spot is detected in the scene, to pass the information
    forward to the frame displaying it.

    Args:
      x: The x position of the detected spot.
      y: The y position of the detected spot.
      r: The radius of the detected spot.
    """

    self.spot_params_updated.emit(self.selected, x, y, r)

  @pyqtSlot(Quadrant)
  def load_text(self, quadrant: Quadrant) -> None:
    """Called when a new image is loaded, for displaying all the associated
    information at once.

    Args:
      quadrant: The Quadrant object containing all the relevant information to
        display.
    """

    # Left post of the left well
    if quadrant.well_1.spot_1 is not None:
      spot = quadrant.well_1.spot_1
      self.spot_params_updated.emit(0, spot.x, spot.y, spot.radius
                                    if spot.radius is not None else -1)

    # Right post of the left well
    if quadrant.well_1.spot_2 is not None:
      spot = quadrant.well_1.spot_2
      self.spot_params_updated.emit(1, spot.x, spot.y, spot.radius
                                    if spot.radius is not None else -1)

    # Left post of the right well
    if quadrant.well_2.spot_1 is not None:
      spot = quadrant.well_2.spot_1
      self.spot_params_updated.emit(2, spot.x, spot.y, spot.radius
                                    if spot.radius is not None else -1)

    # Right post of the right well
    if quadrant.well_2.spot_2 is not None:
      spot = quadrant.well_2.spot_2
      self.spot_params_updated.emit(3, spot.x, spot.y, spot.radius
                                    if spot.radius is not None else -1)

  @pyqtSlot()
  def reset_text(self) -> None:
    """Called for cleaning up the whole table when a new image is loaded.

    Passes on the reset command to the individual frames.
    """

    self.reset_text_requested.emit()

  @pyqtSlot(int)
  def post_deleted(self, index: int) -> None:
    """Called when the delete button is hit on one of the individual frames.

    Passes on the information to the scene for deleting the circle, and to the
    main window for updating the saved data.

    Args:
      index: The index of the frame on which the delete button was hit.
    """

    self.deleted_post.emit(index)

  @property
  def selected(self) -> int:
    """Contains the index of the currently selected post.

    Also allows to modify the selected post programmatically from the main
    window, without using the mouse.
    """

    for frame in self._frames:
      if frame.selected:
        return frame.index

  @selected.setter
  def selected(self, index: int) -> None:
    if index not in range(4):
      raise ValueError
    self._frames[index].soft_select()
