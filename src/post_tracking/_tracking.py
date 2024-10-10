# coding: utf-8

"""This file contains the functions used for performing post detection and post
tracking."""

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
  """Tries to detect a spot in a subframe of the image provided by the user,
  and returns it if successful.

  Args:
    image: The entire image from which to extract the subregion to search.
    y_1: The y coordinate of the top-left corner of the subregion to search.
    x_1: The x coordinate of the top-left corner of the subregion to search.
    y_2: The y coordinate of the bottom-right corner of the subregion to
      search.
    x_2: The x coordinate of the bottom-right corner of the subregion to
      search.
    min_radius: If provided, the minimum radius that the detected spot is
      allowed to have.
    max_radius: If provided, the maximum radius that the detected spot is
      allowed to have.

  Returns:
    A Spot object containing information on the detected spot, or None if no
    spot could be detected.
  """

  # Sort the coordinates so that the selection box can be drawn in any possible
  # direction
  x_1, x_2 = sorted((x_1, x_2))
  y_1, y_2 = sorted((y_1, y_2))
  # Handle case when the selection box is empty
  if x_1 == x_2 or y_1 == y_2:
    return

  # Perform the detection on the subregion only
  roi = deepcopy(image[x_1: x_2, y_1: y_2, :])
  ret = _detect_spot(roi, min_radius=min_radius, max_radius=max_radius)

  # Return None if no spot can be found
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
  """Tries to detect a spot in a subframe of the image determined based on the
  last detected spot, and returns it if successful.

  Args:
    image: The entire image from which to extract the subregion to search.
    spot: A Spot object containing information on the last detected spot.
    offset: The number of extra pixels to add on each side of the last detected
      spot to form the subframe in which to search for the new post.
    min_radius: If provided, the minimum radius that the detected spot is
      allowed to have.
    max_radius: If provided, the maximum radius that the detected spot is
      allowed to have.

  Returns:
    A Spot object containing information on the detected spot, or None if no
    spot could be detected.
  """

  # Create the new subframe based on the coordinates of the last detected spot
  roi = deepcopy(image[spot.y - spot.radius - offset:
                       spot.y + spot.radius + offset,
                       spot.x - spot.radius - offset:
                       spot.x + spot.radius + offset, :])
  # Perform the actual spot tracking
  ret = _detect_spot(roi, prev_rad=spot.radius, 
                     min_radius=min_radius, max_radius=max_radius)

  # Return None if no spot can be found
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
  """Performs the spot detection by fitting Hough circles on the provided
  subframe, after thresholding using an Otsu threshold.

  Args:
    roi: The subframe on which to perform the spot detection.
    min_radius: If provided, the minimum radius that the detected spot is
      allowed to have.
    max_radius: If provided, the maximum radius that the detected spot is
      allowed to have.
    prev_rad: The radius of the previous detected spot.

  Returns:
    If the detection is successful, returns the coordinates of the detected
    spot in the subframe and the radius of the spot. Otherwise, returns None.
  """

  # Switch to grey level image instead of color image
  roi = (np.average(roi, axis=2)).astype('uint8')
  # Apply an Otsu threshold to the image
  _, roi = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
  # Determine the contour of the region preserved by Otsu thresholding
  contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL,
                                 cv2.CHAIN_APPROX_SIMPLE)
  # Keep only closed contours and sort by perimeter
  contours = sorted(contours, key=partial(cv2.arcLength, closed=True),
                    reverse=True)
  # New array containing all the pixels inside the contour
  spot = np.zeros_like(roi, dtype=np.uint8)
  cv2.drawContours(spot, contours, 0, (255,), -1)

  # Calculate the minimum and maximum spot radius, depending on the arguments
  min_rad = (int(np.min(spot.shape[:2]) / 4) if prev_rad is None
             else int(prev_rad * 0.75))
  max_rad = (int(np.min(spot.shape[:2]) * 2) if prev_rad is None
             else int(prev_rad * 1.25))

  if min_radius is not None:
    min_rad = max(min_rad, min_radius)
  if max_radius is not None:
    max_rad = min(max_rad, max_radius)

  # Fit Hough circles on the detected contour
  detect = cv2.HoughCircles(spot,
                            cv2.HOUGH_GRADIENT,
                            1.0,
                            np.max(spot.shape[:2]),
                            param1=255,
                            param2=1,
                            minRadius=min_rad,
                            maxRadius=max_rad)

  # Return None if no spot can be detected
  if detect is None:
    return

  # If more than one Hough circle was fitted, means that the detection failed
  detect = np.squeeze(detect)
  if len(detect.shape) > 1:
    return

  # Return the coordinates and radius of the detected circle as integers
  y, x, r = map(int, detect)
  return y, x, r
