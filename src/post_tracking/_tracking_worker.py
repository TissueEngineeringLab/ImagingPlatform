# coding: utf-8

"""This file contains the classes used for managing the image processing
operations in threads separately from the main interface thread."""

from PyQt6.QtCore import QRunnable, QObject
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from itertools import pairwise
from time import sleep
import numpy as np

from ._tracking import track_spot


class WorkerSignal(QObject):
  """Class containing the signals emitted by the worker thread."""

  processing_done = pyqtSignal()
  """Signal emitted when the worker is done processing the images."""
  track_progress = pyqtSignal(int)
  """Signal emitted at each new processed image, indicating the current 
  progress of the processing."""


class TrackingWorker(QRunnable):
  """Worker performing the image processing steps in a thread separate from the
  main event loop."""

  def __init__(self, main_window) -> None:
    """Connects the signal and slots.

    Args:
      main_window: Instance of the MainWindow class that uses this worker.
    """

    # Initialize the parent class
    super().__init__()

    # Connect the signals and slots
    self._parent = main_window
    self._signals = WorkerSignal()
    self._signals.processing_done.connect(self._parent.stop_processing)
    self._signals.track_progress.connect(self._parent.progress_bar.setValue)

  @pyqtSlot()
  def run(self) -> None:
    """Iterates over all the timestamp to perform post tracking, for one
    quadrant at a time, based on the already manually selected spots."""

    # Number of processing operations to perform
    nb_iter = len(self._parent.timepoints) - 1

    # Iterating over all the timepoints
    for i, (prev, current) in enumerate(pairwise(self._parent.timepoints)):

      # Emitting signal indicating the progress of the processing
      self._signals.track_progress.emit(int((i + 1) / nb_iter * 1000))

      # Stopping if requested by the parent window
      if self._parent.stop_thread:
        return

      # Only start from the first fully defined timepoint
      if not prev:
        continue

      for prev_quad, current_quad in zip(prev, current):

        # Only process if there is data for the preceding timepoint
        if not prev_quad:
          continue

        # Only process one quadrant at a time
        if current_quad.id != self._parent.quadrant:
          continue

        for prev_well, current_well in zip(prev_quad, current_quad):

          # Only process if there is data for the preceding timepoint
          if not prev_well.is_defined:
            continue

          # Only process wells where at least one post is undefined
          if current_well.is_defined:
            continue

          # Load the image before processing it
          self._parent.time_combo.setCurrentIndex(i + 1)

          # Switching to the post to track in the interface
          self._parent.posts_table.selected = 2 * current_well.id

          # Performing the post tracking for the fist post
          ret = track_spot(np.array(self._parent.scene.img),
                           prev_well.spot_1, 10, self._parent.min_radius,
                           self._parent.max_radius)
          if ret is not None:
            # Save the detected spot
            current_well.spot_1 = ret
            self._parent.scene.post_detected_in_scene.emit(
                ret.x, ret.y, ret.radius if ret.radius is not None else -1)

          # Switching to the post to track in the interface
          self._parent.posts_table.selected = 2 * current_well.id + 1

          # Performing the post tracking for the second post
          ret = track_spot(np.array(self._parent.scene.img),
                           prev_well.spot_2, 10, self._parent.min_radius,
                           self._parent.max_radius)
          if ret is not None:
            # Save the detected spot
            current_well.spot_2 = ret
            self._parent.scene.post_detected_in_scene.emit(
                ret.x, ret.y, ret.radius if ret.radius is not None else -1)

          # Allow some time for the display to refresh
          sleep(0.02)

    # Indicate the main window when done processing
    self._signals.processing_done.emit()
