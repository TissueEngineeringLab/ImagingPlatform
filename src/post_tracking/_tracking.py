# coding: utf-8

import numpy as np
from copy import deepcopy
import cv2
from functools import partial
from typing import Optional, Tuple

from ._structure import Spot


def detect_spot(image: np.ndarray, 
                y_1: int,
                x_1: int, 
                y_2: int, 
                x_2: int,
                min_radius: Optional[int] = None,
                max_radius: Optional[int] = None) -> Optional[Spot]:
  """"""

  x_1, x_2 = sorted((x_1, x_2))
  y_1, y_2 = sorted((y_1, y_2))
  if x_1 == x_2 or y_1 == y_2:
    return

  roi = deepcopy(image[x_1: x_2, y_1: y_2, :])
  ret = _detect_spot(roi, min_radius=min_radius, max_radius=max_radius)

  # Undetected spots are handled elsewhere
  if ret is None:
    return
  else:
     x, y, r = ret

  return Spot(y_1 + y, x_1 + x, r)


def track_spot(image: np.ndarray, 
               spot: Spot, 
               offset: int,
               min_radius: Optional[int],
               max_radius: Optional[int]) -> Optional[Spot]:
  """"""

  roi = deepcopy(image[spot.y - spot.radius - offset:
                       spot.y + spot.radius + offset,
                       spot.x - spot.radius - offset:
                       spot.x + spot.radius + offset, :])
  ret = _detect_spot(roi, prev_rad=spot.radius, 
                     min_radius=min_radius, max_radius=max_radius)

  # Undetected spots are handled elsewhere
  if ret is None:
    return
  else:
    x, y, r = ret

  return Spot(spot.x - spot.radius - offset + x,
              spot.y - spot.radius - offset + y, r)


def _detect_spot(roi: np.ndarray,
                 min_radius: Optional[int],
                 max_radius: Optional[int],
                 prev_rad: Optional[int] = None) -> Optional[Tuple[int, int,
                                                                   int]]:
  """"""

  roi = (np.average(roi, axis=2)).astype('uint8')
  _, roi = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
  contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL,
                                 cv2.CHAIN_APPROX_SIMPLE)
  contours = sorted(contours, key=partial(cv2.arcLength, closed=True),
                    reverse=True)
  spot = np.zeros_like(roi, dtype=np.uint8)
  cv2.drawContours(spot, contours, 0, (255,), -1)

  min_rad = (int(np.min(spot.shape[:2]) / 4) if prev_rad is None
             else int(prev_rad * 0.75))
  max_rad = (int(np.min(spot.shape[:2]) * 2) if prev_rad is None
             else int(prev_rad * 1.25))

  if min_radius is not None:
    min_rad = max(min_rad, min_radius)
  if max_radius is not None:
    max_rad = min(max_rad, max_radius)

  detect = cv2.HoughCircles(spot,
                            cv2.HOUGH_GRADIENT,
                            1.0,
                            np.max(spot.shape[:2]),
                            param1=255,
                            param2=1,
                            minRadius=min_rad,
                            maxRadius=max_rad)

  # Don't return anything if no spot can be detected
  if detect is None:
    return

  detect = np.squeeze(detect)
  if len(detect.shape) > 1:
    return

  y, x, r = map(int, detect)
  return y, x, r
