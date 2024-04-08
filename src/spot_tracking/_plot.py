# coding: utf-8

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import patches, ticker
from pathlib import Path
from typing import Optional
from functools import partial

from . import Quadrant


def draw_img(image: np.ndarray, detected: Quadrant):
  """"""

  fig, ax = plt.subplots()
  ax.imshow(image)

  for well in detected:
    for spot in well:
      if not spot.lost:
        rect = patches.Rectangle((spot.x_offset + spot.x_min,
                                  spot.y_offset + spot.y_min),
                                 spot.x_max - spot.x_min,
                                 spot.y_max - spot.y_min,
                                 fill=False, linewidth=2)
        ax.add_patch(rect)
  plt.show()


def save_overlay(image: np.ndarray,
                 detected: Quadrant,
                 img_path: Path) -> None:
  """"""

  fig, ax = plt.subplots()
  ax = fig.add_axes([0, 0, 1, 1])
  ax.axis('off')
  ax.imshow(image)

  for well in detected:
    for spot in well:
      if not spot.lost:
        rect = patches.Rectangle((spot.x_offset + spot.x_min,
                                  spot.y_offset + spot.y_min),
                                 spot.x_max - spot.x_min,
                                 spot.y_max - spot.y_min,
                                 fill=False, linewidth=2)
        ax.add_patch(rect)
  save_path = img_path.parent.parent / 'detected' / img_path.name
  if not save_path.parent.exists():
    Path.mkdir(save_path.parent)
  plt.savefig(save_path)
  plt.close()


def format_func(time: float, _, ref: float):
  """"""

  t = time - round(ref, -3)
  d = int(t // (24 * 3600))
  h = int((t % (24 * 3600)) // 3600)
  return f"{d:d}d {h:02d}h"


def plot_distance(detected: Quadrant,
                  time_ref: float,
                  save_fig: bool,
                  save_path: Optional[Path] = None) -> None:
  """"""

  fig, ax = plt.subplots()
  l1 = len(detected.well_1.distances)
  ax.plot(detected.timestamps[:l1], detected.well_1.distances, 'k+')
  l2 = len(detected.well_2.distances)
  ax.plot(detected.timestamps[:l2], detected.well_2.distances, 'r+')
  ax.xaxis.set_major_formatter(ticker.FuncFormatter(partial(format_func,
                                                            ref=time_ref)))
  ax.set_xlabel('Time in culture')
  ax.set_ylabel('Distance between posts (px)')

  if save_fig and save_path is not None:
    plt.savefig(save_path, dpi=300)
  plt.show()
