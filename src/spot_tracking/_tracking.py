# coding: utf-8

import numpy as np
from copy import deepcopy
import cv2
from skimage.morphology import label
from skimage.measure import regionprops

from ._structure import Well, Spot


def detect_spots(image: np.ndarray,
                 y_offset: int,
                 x_offset: int,
                 height: int,
                 width: int,
                 threshold: int) -> Well:
  """"""

  y_offset = 1590
  x_offset = 1210
  height = 90
  width = 100

  roi = deepcopy(image[y_offset:y_offset + height,
                       x_offset:x_offset + width])
  roi = (np.sum(roi, axis=2) / 3).astype('uint8')
  from matplotlib import pyplot as plt
  plt.figure()
  plt.imshow(roi)
  plt.show()
  _, roi = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
  plt.figure()
  plt.imshow(roi)
  plt.show()
  raise ValueError
  roi[(roi > 200) | (roi < 100)] = 255
  roi = (np.clip(roi - 100, 0, 100) / 100 * 255).astype('uint8')

  plt.figure()
  plt.imshow(roi <= threshold)
  plt.show()

  props = regionprops(label(roi <= threshold))
  props = [prop for prop in props if prop.solidity > 0.8 and prop.area > 200]

  if len(props) != 2:
    raise ValueError(f"Detected {len(props)} spots instead of 2 expected !")

  return Well(*[Spot(spot.bbox[0], spot.bbox[1], spot.bbox[2], spot.bbox[3],
                x_offset, y_offset, spot.centroid[0], spot.centroid[1],
                     threshold=threshold) for spot in props])


def track_spot(image: np.ndarray, spot: Spot, offset: int) -> None:
  """"""

  roi = deepcopy(image[spot.y_offset + spot.y_min - offset:
                       spot.y_offset + spot.y_max + offset,
                       spot.x_offset + spot.x_min - offset:
                       spot.x_offset + spot.x_max + offset, :])
  roi = (np.sum(roi, axis=2) / 3).astype('uint8')
  min_, max_ = np.percentile(roi, 10), np.percentile(roi, 90)
  roi = ((np.clip(roi, min_, max_) - min_)
         / (max_ - min_) * 255).astype('uint8')

  detect = cv2.HoughCircles(roi, cv2.HOUGH_GRADIENT, 1.5, 100, param1=150,
                            param2=1, minRadius=15, maxRadius=30)
  if detect is None:
    spot.lost = True
    return

  x, y, r = detect[0][0]
  spot.x_offset = spot.x_offset + spot.x_min - offset
  spot.y_offset = spot.y_offset + spot.y_min - offset
  spot.y_center, spot.x_center = y, x
  spot.y_min, spot.x_min = int(y - r), int(x - r)
  spot.y_max, spot.x_max = int(y + r), int(x + r)
