# coding: utf-8

from PyQt6.QtCore import QRunnable, QObject
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from itertools import pairwise
from time import sleep
import numpy as np

from ._tracking import track_spot


class WorkerSignal(QObject):
  """"""

  processing_done = pyqtSignal()
  track_progress = pyqtSignal(int)


class TrackingWorker(QRunnable):
  """"""

  def __init__(self, main_window) -> None:
    """"""

    super().__init__()

    self._parent = main_window
    self._signals = WorkerSignal()
    self._signals.processing_done.connect(self._parent.stop_processing)
    self._signals.track_progress.connect(self._parent._progress_bar.setValue)

  @pyqtSlot()
  def run(self) -> None:
    """"""

    nb_iter = len(self._parent._timepoints) - 1

    for i, (prev, current) in enumerate(pairwise(self._parent._timepoints)):

      self._signals.track_progress.emit(int((i + 1) / nb_iter * 1000))

      if self._parent._stop_thread:
        return

      # Only start from the first fully defined timepoint
      if not prev:
        continue

      for prev_quad, current_quad in zip(prev, current):

        # Only process if there is data for the preceding timepoint
        if not prev_quad:
          continue

        # Only process one quadrant at a time
        if current_quad.id != self._parent._quadrant:
          continue

        for prev_well, current_well in zip(prev_quad, current_quad):

          # Only process if there is data for the preceding timepoint
          if not prev_well.is_defined:
            continue

          # Only process wells where at least one post is undefined
          if current_well.is_defined:
            continue

          # Load the image before processing it
          self._parent._time_combo.setCurrentIndex(i + 1)

          self._parent._posts_table.selected = 2 * current_well.id

          ret = track_spot(np.array(self._parent._scene._img),
                           prev_well.spot_1, 10, self._parent._min_radius,
                           self._parent._max_radius)
          if ret is not None:
            current_well.spot_1 = ret
            self._parent._scene.post_detected_in_scene.emit(
                ret.x, ret.y, ret.radius if ret.radius is not None else -1)

          self._parent._posts_table.selected = 2 * current_well.id + 1

          ret = track_spot(np.array(self._parent._scene._img),
                           prev_well.spot_2, 10, self._parent._min_radius,
                           self._parent._max_radius)
          if ret is not None:
            current_well.spot_2 = ret
            self._parent._scene.post_detected_in_scene.emit(
                ret.x, ret.y, ret.radius if ret.radius is not None else -1)

          sleep(0.05)

    self._signals.processing_done.emit()

