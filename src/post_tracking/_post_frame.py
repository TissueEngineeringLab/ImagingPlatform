# coding: utf-8

from PyQt6.QtGui import QEnterEvent, QMouseEvent
from PyQt6.QtWidgets import (QFrame, QStyle, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton)
from PyQt6.QtCore import pyqtSignal, pyqtSlot

from ._structure import Quadrant


class SinglePostFrame(QFrame, QWidget):
  """"""

  clicked = pyqtSignal(int)
  switch_next = pyqtSignal()
  deleted = pyqtSignal(int)

  def __init__(self, label: str, index: int) -> None:
    """"""

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

    self._delete_button = QPushButton()
    self._delete_button.setIcon(self.style().standardIcon(
      QStyle.StandardPixmap.SP_TrashIcon))
    self._delete_button.clicked.connect(self.reset_text)
    self._delete_button.clicked.connect(self.delete_post)
    self._delete_button.setFixedHeight(30)
    self._delete_button.setFixedWidth(30)
    self._h_layout.addWidget(self._delete_button)

    self.clicked.connect(self.select_entry)

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

    self.clicked.emit(self.index)

  @pyqtSlot()
  def soft_select(self) -> None:
    """"""

    self.clicked.emit(self.index)

  @pyqtSlot(int)
  def select_entry(self, _: int) -> None:
    """"""

    self.selected = True
    self.setLineWidth(3)

  @pyqtSlot(int)
  def unselect_entry(self, _: int) -> None:
    """"""

    self.selected = False
    self.setLineWidth(1)

  @pyqtSlot(int, int, int, int)
  def update_text(self, index: int, x: int, y: int, r: int):
    """"""

    if index != self.index:
      return

    self._x_label.setText(f'X: {x}')
    self._y_label.setText(f'Y: {y}')
    if r > 0:
      self._r_label.setText(f'R: {r}')
    else:
      self._r_label.setText('R: N/A')

    self.switch_next.emit()

  @pyqtSlot()
  def reset_text(self) -> None:
    """"""

    self._x_label.setText('X: N/A')
    self._y_label.setText('Y: N/A')
    self._r_label.setText('R: N/A')

  @pyqtSlot()
  def delete_post(self) -> None:
    """"""

    self.deleted.emit(self.index)


class PostsParentFrame(QFrame):
  """"""

  post_selected_in_table = pyqtSignal(int)
  spot_params_updated = pyqtSignal(int, int, int, int)
  reset_text_requested = pyqtSignal()
  deleted_post = pyqtSignal(int)

  def __init__(self) -> None:
    """"""

    super().__init__()

    # Layout of the frames in the scrollable area
    self._posts_layout = QVBoxLayout()
    self.setLayout(self._posts_layout)

    # Each detectable spot gets its own frame
    self._post_1_l_frame = SinglePostFrame('Left Well, Left Post', 0)
    self._post_1_l_frame.clicked.connect(self.send_highlight_circle_to_scene)
    self._post_1_l_frame.deleted.connect(self.post_deleted)
    self._posts_layout.addWidget(self._post_1_l_frame)

    self._post_1_r_frame = SinglePostFrame('Left Well, Right Post', 1)
    self._post_1_r_frame.clicked.connect(self.send_highlight_circle_to_scene)
    self._post_1_r_frame.deleted.connect(self.post_deleted)
    self._posts_layout.addWidget(self._post_1_r_frame)

    self._post_2_l_frame = SinglePostFrame('Right Well, Left Post', 2)
    self._post_2_l_frame.clicked.connect(self.send_highlight_circle_to_scene)
    self._post_2_l_frame.deleted.connect(self.post_deleted)
    self._posts_layout.addWidget(self._post_2_l_frame)

    self._post_2_r_frame = SinglePostFrame('Right Well, Right Post', 3)
    self._post_2_r_frame.clicked.connect(self.send_highlight_circle_to_scene)
    self._post_2_r_frame.deleted.connect(self.post_deleted)
    self._posts_layout.addWidget(self._post_2_r_frame)

    self._spacer_frame = QFrame()
    self._spacer_frame.setMinimumHeight(10)
    self._posts_layout.addWidget(self._spacer_frame)

    self._frames = (self._post_1_l_frame, self._post_1_r_frame,
                    self._post_2_l_frame, self._post_2_r_frame)

    self._post_1_l_frame.selected = True
    self._post_1_l_frame.setLineWidth(3)

    self.spot_params_updated.connect(self._post_1_l_frame.update_text)
    self.spot_params_updated.connect(self._post_1_r_frame.update_text)
    self.spot_params_updated.connect(self._post_2_l_frame.update_text)
    self.spot_params_updated.connect(self._post_2_r_frame.update_text)

    self.reset_text_requested.connect(self._post_1_l_frame.reset_text)
    self.reset_text_requested.connect(self._post_1_r_frame.reset_text)
    self.reset_text_requested.connect(self._post_2_l_frame.reset_text)
    self.reset_text_requested.connect(self._post_2_r_frame.reset_text)

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

    self._post_1_l_frame.switch_next.connect(self._post_1_r_frame.soft_select)
    self._post_1_r_frame.switch_next.connect(self._post_2_l_frame.soft_select)
    self._post_2_l_frame.switch_next.connect(self._post_2_r_frame.soft_select)
    self._post_2_r_frame.switch_next.connect(self._post_1_l_frame.soft_select)

  @pyqtSlot(int)
  def send_highlight_circle_to_scene(self, value: int) -> None:
    """"""

    self.post_selected_in_table.emit(value)

  @pyqtSlot(int, int, int)
  def update_post_text(self, x: int, y: int, r: int) -> None:
    """"""

    self.spot_params_updated.emit(self.selected, x, y, r)

  @pyqtSlot(Quadrant)
  def load_text(self, quadrant: Quadrant) -> None:
    """"""

    if quadrant.well_1.spot_1 is not None:
      spot = quadrant.well_1.spot_1
      self.spot_params_updated.emit(0, spot.x, spot.y, spot.radius
                                    if spot.radius is not None else -1)

    if quadrant.well_1.spot_2 is not None:
      spot = quadrant.well_1.spot_2
      self.spot_params_updated.emit(1, spot.x, spot.y, spot.radius
                                    if spot.radius is not None else -1)

    if quadrant.well_2.spot_1 is not None:
      spot = quadrant.well_2.spot_1
      self.spot_params_updated.emit(2, spot.x, spot.y, spot.radius
                                    if spot.radius is not None else -1)

    if quadrant.well_2.spot_2 is not None:
      spot = quadrant.well_2.spot_2
      self.spot_params_updated.emit(3, spot.x, spot.y, spot.radius
                                    if spot.radius is not None else -1)

  @pyqtSlot()
  def reset_text(self) -> None:
    """"""

    self.reset_text_requested.emit()

  @pyqtSlot(int)
  def post_deleted(self, index: int) -> None:
    """"""

    self.deleted_post.emit(index)

  @property
  def selected(self) -> int:
    """"""

    for frame in self._frames:
      if frame.selected:
        return frame.index

  @selected.setter
  def selected(self, index: int) -> None:
    """"""

    if index not in range(4):
      raise ValueError

    self._frames[index].soft_select()
