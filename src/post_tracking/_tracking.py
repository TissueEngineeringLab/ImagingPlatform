# coding: utf-8

import numpy as np
from copy import deepcopy
import cv2
from functools import partial
from typing import Optional

from _structure import Spot


def detect_spot(image: np.ndarray, y_1: int,
                x_1: int, y_2: int, x_2: int) -> Optional[Spot]:
  """"""

  # Todo: Maximum radius parameter based on previous

  (x_1, y_1), (x_2, y_2) = sorted(((x_1, y_1), (x_2, y_2)))

  if x_1 == x_2 or y_1 == y_2:
    return

  roi = deepcopy(image[x_1: x_2, y_1: y_2])
  roi = (np.average(roi, axis=2)).astype('uint8')
  _, roi = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
  contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL,
                                 cv2.CHAIN_APPROX_SIMPLE)
  contours = sorted(contours, key=partial(cv2.arcLength, closed=True),
                    reverse=True)
  spot = np.zeros_like(roi, dtype=np.uint8)
  cv2.drawContours(spot, contours, 0, (255,), -1)
  detect = cv2.HoughCircles(spot,
                            cv2.HOUGH_GRADIENT,
                            1.0,
                            np.max(spot.shape[:2]),
                            param1=255,
                            param2=1,
                            minRadius=int(np.min(spot.shape[:2]) / 4),
                            maxRadius=int(np.min(spot.shape[:2]) * 2))

  if detect is None:
    # Todo: handle lost spot instead
    raise ValueError

  y, x, r = map(int, np.squeeze(detect))
  return Spot(y_1 + y, x_1 + x, r)


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
