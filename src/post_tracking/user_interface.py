# coding: utf-8

from PyQt6.QtCore import QSize, pyqtSignal, pyqtSlot, QThreadPool
from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout,
                             QWidget, QComboBox, QPushButton, QGraphicsView,
                             QProgressBar, QFileDialog)
from pyqtgraph import PlotWidget, DateAxisItem, mkPen
from typing import Optional, Union, List, Dict
from pathlib import Path
from itertools import batched, count
from csv import DictWriter

from ._structure import TimePoint, path_to_time, Quadrant, path_to_str
from ._custom_scene import CustomScene
from ._post_frame import PostsParentFrame
from ._tracking_worker import TrackingWorker


class MainWindow(QMainWindow):
  """"""

  image_loaded = pyqtSignal(Quadrant)
  quadrant_changed = pyqtSignal(int)
  time_changed = pyqtSignal(int)
  data_updated = pyqtSignal()

  def __init__(self) -> None:
    """"""

    super().__init__()

    self.setWindowTitle('Spot selection')
    self.setMinimumSize(QSize(1100, 430))

    self._set_layout()
    self.setCentralWidget(self._main_widget)

    self._img_folder: Optional[Path] = None
    self.timepoints: List[TimePoint] = list()
    self._time_idx: int = 0
    self.quadrant: str = 'A'
    self._time_to_index: Dict[str, int] = dict()

    self._thread_pool: QThreadPool = QThreadPool()
    self.stop_thread: bool = False
    self.min_radius: Optional[int] = None
    self.max_radius: Optional[int] = None

    self.image_loaded.connect(self.scene.reload_image_in_scene)
    self.image_loaded.connect(self.scene.reset_circles_in_scene)
    self.image_loaded.connect(self.posts_table.reset_text)
    self.image_loaded.connect(self.scene.draw_circles_in_scene)
    self.image_loaded.connect(self.posts_table.load_text)

    self.data_updated.connect(self.enable_process_button)
    self.data_updated.connect(self.update_graph)
    self.quadrant_changed.connect(self.update_graph)

  def _set_layout(self) -> None:
    """"""

    self._main_layout = QHBoxLayout()
    self._left_panel_layout = QVBoxLayout()
    self._right_panel_layout = QVBoxLayout()
    self._left_title_bar = QHBoxLayout()

    # Title bar on left panel
    self._load_images_button = QPushButton('Load Images')
    self._load_images_button.clicked.connect(self.load_images)
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

    self.time_combo = QComboBox()
    self.time_combo.setFixedSize(QSize(180, 29))
    self.time_combo.setEnabled(False)
    self.time_combo.currentTextChanged.connect(self.select_time)
    self.time_changed.connect(self.time_combo.setCurrentIndex)
    self._left_title_bar.addWidget(self.time_combo)

    self._prev_time_button = QPushButton('<')
    self._prev_time_button.clicked.connect(self.prev_time)
    self._prev_time_button.setFixedSize(QSize(29, 29))
    self._prev_time_button.setEnabled(False)
    self._left_title_bar.addWidget(self._prev_time_button)

    self._next_time_button = QPushButton('>')
    self._next_time_button.clicked.connect(self.next_time)
    self._next_time_button.setFixedSize(QSize(29, 29))
    self._next_time_button.setEnabled(False)
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
    self._quadrant_combo.insertItems(0, ('A', 'B', 'C', 'D'))
    self._quadrant_combo.setFixedSize(QSize(80, 29))
    self._quadrant_combo.setEnabled(False)
    self._quadrant_combo.currentTextChanged.connect(self.select_quadrant)
    self.quadrant_changed.connect(self._quadrant_combo.setCurrentIndex)
    self._left_title_bar.addWidget(self._quadrant_combo)

    self._prev_quad_button = QPushButton('<')
    self._prev_quad_button.clicked.connect(self.prev_quadrant)
    self._prev_quad_button.setFixedSize(QSize(29, 29))
    self._prev_quad_button.setEnabled(False)
    self._left_title_bar.addWidget(self._prev_quad_button)

    self._next_quad_button = QPushButton('>')
    self._next_quad_button.clicked.connect(self.next_quadrant)
    self._next_quad_button.setFixedSize(QSize(29, 29))
    self._next_quad_button.setEnabled(False)
    self._left_title_bar.addWidget(self._next_quad_button)

    self._spacer_3 = QLabel()
    self._spacer_3.setFixedHeight(29)
    self._spacer_3.setMinimumWidth(10)
    self._spacer_3.setMaximumWidth(50)
    self._left_title_bar.addWidget(self._spacer_3)

    self._export_button = QPushButton('Export')
    self._export_button.clicked.connect(self.export_results)
    self._export_button.setFixedSize(QSize(80, 29))
    self._export_button.setEnabled(False)
    self._left_title_bar.addWidget(self._export_button)

    self._spacer_5 = QLabel()
    self._spacer_5.setFixedHeight(29)
    self._spacer_5.setMinimumWidth(10)
    self._left_title_bar.addWidget(self._spacer_5)

    # Rest of the left panel
    self._left_panel_layout.addLayout(self._left_title_bar, stretch=1)

    self._view = QGraphicsView()
    self.scene = CustomScene(self._view)
    self._view.setScene(self.scene)
    self._left_panel_layout.addWidget(self._view)

    self.progress_bar = QProgressBar()
    self.progress_bar.setRange(0, 1000)
    self._left_panel_layout.addWidget(self.progress_bar)

    # Scrollable area containing the information on the detected spots
    self.posts_table = PostsParentFrame()
    self.posts_table.setMinimumHeight(350)
    self._right_panel_layout.addWidget(self.posts_table)
    self.posts_table.post_selected_in_table.connect(
      self.scene.highlight_selected_circle_in_scene)

    self.scene.post_detected_in_scene.connect(
      self.posts_table.update_post_text)
    self.posts_table.deleted_post.connect(self.scene.delete_circle_in_scene)

    self.posts_table.spot_params_updated.connect(self.update_data)
    self.posts_table.deleted_post.connect(self.delete_data)

    self._spacer_4 = QLabel('Post distance vs time')
    self._spacer_4.setFixedHeight(19)
    self._right_panel_layout.addWidget(self._spacer_4)

    # Graph integration
    self._graph = PlotWidget(background=None)
    self._graph.setMinimumHeight(200)
    self._graph.setLabel("left", "Distance (px)")
    axis = DateAxisItem()
    self._graph.setAxisItems({'bottom': axis})
    pen_left = mkPen(color=(255, 0, 0))
    pen_right = mkPen(color=(0, 0, 255))
    self._graph.addLegend()
    self._line_left = self._graph.plot(list(), list(), pen=pen_left,
                                       name='Left well')
    self._line_right = self._graph.plot(list(), list(), pen=pen_right,
                                        name='Right well')
    self._right_panel_layout.addWidget(self._graph)

    # Process button
    self._process_button = QPushButton('Process')
    self._process_button.clicked.connect(self.process_images)
    self._process_button.setEnabled(False)
    self._right_panel_layout.addWidget(self._process_button)

    # Finalize main layout
    self._main_layout.addLayout(self._left_panel_layout, stretch=3)
    self._main_layout.addLayout(self._right_panel_layout, stretch=1)
    self._main_widget = QWidget()
    self._main_widget.setLayout(self._main_layout)

  @pyqtSlot(int, int, int, int)
  def update_data(self, index: int, x: int, y: int, r: int) -> None:
    """"""

    well = index // 2
    spot = index % 2

    if self.timepoints[self._time_idx][self.quadrant][well][spot] is None:
      return

    if self.min_radius is None:
      self.min_radius = int(r / 2)
    if self.max_radius is None:
      self.max_radius = int(r * 1.5)

    self.timepoints[self._time_idx][self.quadrant][well][spot].x = x
    self.timepoints[self._time_idx][self.quadrant][well][spot].y = y
    self.timepoints[self._time_idx][self.quadrant][well][spot].radius = r

    self.data_updated.emit()

  @pyqtSlot(int)
  def delete_data(self, index: int) -> None:
    """"""

    well = index // 2
    spot = index % 2

    self.timepoints[self._time_idx][self.quadrant][well][spot] = None

    if not any(timepoint for timepoint in self.timepoints):
      self.min_radius = None
      self.max_radius = None

    self.data_updated.emit()

  @pyqtSlot()
  def update_graph(self) -> None:
    """"""

    valid = [quad for point in self.timepoints for quad in point
             if quad.id == self.quadrant and quad]
    left = (quad for quad in valid if quad.well_1.is_defined)
    right = (quad for quad in valid if quad.well_2.is_defined)

    to_plot_left = ((quad.acq_time, quad.well_1.distance) for quad in left)
    to_plot_right = ((quad.acq_time, quad.well_2.distance) for quad in right)

    self._line_left.setData(*zip(*to_plot_left))
    self._line_right.setData(*zip(*to_plot_right))

    self._graph.autoRange()

  @pyqtSlot(str)
  def select_time(self, value: str) -> None:
    """"""

    self._time_idx = self._time_to_index[value]
    self.image_loaded.emit(self.timepoints[self._time_idx][self.quadrant])

  @pyqtSlot()
  def prev_time(self) -> None:
    """"""

    if self._time_idx <= 0:
      return

    self._time_idx -= 1
    self.image_loaded.emit(self.timepoints[self._time_idx][self.quadrant])
    self.time_changed.emit(self._time_idx)

  @pyqtSlot()
  def next_time(self) -> None:
    """"""

    if self._time_idx >= len(self.timepoints) - 1:
      return

    self._time_idx += 1
    self.image_loaded.emit(self.timepoints[self._time_idx][self.quadrant])
    self.time_changed.emit(self._time_idx)

  @pyqtSlot(str)
  def select_quadrant(self, value: str) -> None:
    """"""

    self.quadrant = value
    self.image_loaded.emit(self.timepoints[self._time_idx][self.quadrant])

  @pyqtSlot()
  def prev_quadrant(self):
    """"""

    val = -1

    if self.quadrant == 'A':
      self.quadrant = 'D'
      val = 3
    elif self.quadrant == 'B':
      self.quadrant = 'A'
      val = 0
    elif self.quadrant == 'C':
      self.quadrant = 'B'
      val = 1
    elif self.quadrant == 'D':
      self.quadrant = 'C'
      val = 2

    self.image_loaded.emit(self.timepoints[self._time_idx][self.quadrant])
    self.quadrant_changed.emit(val)

  @pyqtSlot()
  def next_quadrant(self):
    """"""

    val = -1

    if self.quadrant == 'A':
      self.quadrant = 'B'
      val = 1
    elif self.quadrant == 'B':
      self.quadrant = 'C'
      val = 2
    elif self.quadrant == 'C':
      self.quadrant = 'D'
      val = 3
    elif self.quadrant == 'D':
      self.quadrant = 'A'
      val = 0

    self.image_loaded.emit(self.timepoints[self._time_idx][self.quadrant])
    self.quadrant_changed.emit(val)

  @pyqtSlot()
  def load_images(self) -> None:
    """"""

    folder = QFileDialog.getExistingDirectory(self, "Select Image Directory")
    if not folder:
      return

    self._img_folder = Path(folder)
    images = sorted(Path(folder).glob('*.jpg'), key=path_to_time)

    self.timepoints.clear()
    self._time_idx = 0
    self.quadrant = 'A'
    for path_1, path_2, path_3, path_4 in batched(images, 4):
      self.timepoints.append(TimePoint.parse_paths(path_1, path_2,
                                                   path_3, path_4))

    self.image_loaded.emit(self.timepoints[self._time_idx][self.quadrant])

    self._time_to_index = dict(zip((path_to_str(time_point.A.path) for
                                    time_point in self.timepoints),
                                   count()))
    self.time_combo.insertItems(0, self._time_to_index.keys())

    self._quadrant_combo.setEnabled(True)
    self._prev_quad_button.setEnabled(True)
    self._next_quad_button.setEnabled(True)
    self.time_combo.setEnabled(True)
    self._prev_time_button.setEnabled(True)
    self._next_time_button.setEnabled(True)
    self._export_button.setEnabled(True)

  @pyqtSlot()
  def export_results(self) -> None:
    """"""

    ret: List[Dict[str, Optional[Union[str, float, int]]]] = list()
    for point in self.timepoints:
      ret.extend(point.export())

    if not ret:
      return

    base_dir = (self._img_folder if self._img_folder is not None
                else Path.home())
    file, _ = QFileDialog.getSaveFileName(caption='File to save data to',
                                          directory=str(base_dir),
                                          filter='Text files (*.txt *.csv '
                                                 '*.dat)')
    if not file:
      return
    file = Path(file)
    if not file.suffix:
      file = file.with_suffix('.csv')

    with open(file, 'w') as csvfile:
      writer = DictWriter(csvfile, fieldnames=ret[0].keys())
      writer.writeheader()
      writer.writerows(ret)

  @pyqtSlot()
  def process_images(self) -> None:
    """"""

    worker = TrackingWorker(self)
    self._process_button.setText('Stop Processing')
    self._process_button.clicked.disconnect(self.process_images)
    self._process_button.clicked.connect(self.stop_processing)
    self._thread_pool.start(worker)

  @pyqtSlot()
  def stop_processing(self) -> None:
    """"""

    self.stop_thread = True
    if not self._thread_pool.waitForDone(3000):
      raise TimeoutError
    self._process_button.setText('Process')
    self._process_button.clicked.connect(self.process_images)
    self._process_button.clicked.disconnect(self.stop_processing)
    self.stop_thread = False

  @pyqtSlot()
  def enable_process_button(self) -> None:
    """"""

    if self.timepoints and any(self.timepoints):
      self._process_button.setEnabled(True)
    else:
      self._process_button.setEnabled(False)
