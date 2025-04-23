# coding: utf-8

"""This file contains the functions and classes used for building the data
structure storing all the information necessary for spot-tracking."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Iterator, List, Dict, Union
from numpy import linalg
from pathlib import Path
from re import fullmatch
from calendar import timegm
from time import gmtime, strftime


def path_to_time(path: Path) -> float:
  """Parses the path to an image, and determines the moment when this image was
  acquired as a Unix timestamp.

  Args:
    path: The Path object pointing to the image.

  Returns:
    The Unix timestamp of the moment when the image was acquired.
  """

  return timegm(tuple(map(int, fullmatch(r'(\d+)_(\d+)_(\d+)_(\d+)_'
                                         r'(\d+)_(\d+)_[0123]\.(?:jpg|png)',
                                         path.name).groups())))


def path_to_str(path: Path) -> str:
  """Parses the path to an image, and determines the moment when this image was
  acquired as a human-readable string.

  Args:
    path: The Path object pointing to the image.

  Returns:
    The moment when the image was acquired in a human-readable format.
  """

  return '{}/{}/{} {}:{}:{}'.format(*fullmatch(r'(\d+)_(\d+)_(\d+)_(\d+)_'
                                               r'(\d+)_(\d+)_[0123]\.'
                                               r'(?:jpg|png)',
                                               path.name).groups())


@dataclass
class Spot:
  """Class holding basic information about a single detected post."""

  x: int
  """x position of the post on the image containing it."""
  y: int
  """y position of the post on the image containing it."""

  radius: Optional[int] = None
  """Radius of the spot in pixels."""

  def __sub__(self, other: Spot) -> Spot:
    """Convenience function for easily getting the coordinate difference
    between two spots."""

    return Spot(self.x - other.x, self.y - other.y, None)


@dataclass
class Well:
  """Class holding information about one well, which comprises two spots. As
  long as the spots are not detected, they are left to None."""

  id: int
  """The index of the well in the quadrant, either 1 for the left well or 2 for 
  the right well."""

  spot_1: Optional[Spot] = None
  """Spot object representing the detected left spot, if any."""
  spot_2: Optional[Spot] = None
  """Spot object representing the detected right spot, if any."""

  @property
  def distance(self) -> float:
    """Convenience property for getting the distance between the two detected
    spots in a well."""

    # Can only compute the distance if both posts are detected
    if not self.is_defined:
      raise ValueError

    # Compute and return the distance
    diff = self.spot_1 - self.spot_2
    return float(linalg.norm((diff.x, diff.y)))

  @property
  def is_defined(self) -> bool:
    """Returns True if both spot objects are not None, and False otherwise."""

    return self.spot_1 is not None and self.spot_2 is not None

  def __iter__(self) -> Iterator[Spot]:
    """Iterates over the spots, first the left one and second the right one."""

    return iter((self.spot_1, self.spot_2))

  def __getitem__(self, index: int) -> Spot:
    """Allows to get the spot objects by index, for convenience."""

    if index in (-2, 0):
      return self.spot_1
    elif index in (-1, 1):
      return self.spot_2
    else:
      raise IndexError

  def __setitem__(self, index: int, value: Optional[Spot]) -> None:
    """Allows to set the spot objects by index, for convenience."""

    if index in (-2, 0):
      self.spot_1 = value
    elif index in (-1, 1):
      self.spot_2 = value
    else:
      raise IndexError


@dataclass
class Quadrant:
  """Class holding information about one quadrant, which comprises two wells.
  The wells are always initialized even when no spot is detected yet."""

  path: Path
  """Path to the image in which the quadrant is captured."""
  acq_time: float
  """The moment when the image was acquired, as a Unix timestamp."""
  id: int
  """Identifier string of the camera, either 0, 1, 2, or 3."""

  well_1: Well = field(default_factory=lambda: Well(0))
  """Well object representing the left well in the quadrant."""
  well_2: Well = field(default_factory=lambda: Well(1))
  """Well object representing the right well in the quadrant."""

  def __iter__(self) -> Iterator[Well]:
    """Iterates over the wells, first the left one and second the right one."""

    return iter((self.well_1, self.well_2))

  def __getitem__(self, index: int) -> Well:
    """Allows to get the well objects by index, for convenience."""

    if index in (-2, 0):
      return self.well_1
    elif index in (-1, 1):
      return self.well_2
    else:
      raise IndexError

  def __bool__(self) -> bool:
    """Returns True if at least one of the wells is defined, False
    otherwise."""

    return self.well_1.is_defined or self.well_2.is_defined


@dataclass
class TimePoint:
  """Class holding information about one timepoint, which comprises four
  quadrants."""

  A: Quadrant
  """Quadrant object whose image was acquired by camera 0."""
  B: Quadrant
  """Quadrant object whose image was acquired by camera 1."""
  C: Quadrant
  """Quadrant object whose image was acquired by camera 2."""
  D: Quadrant
  """Quadrant object whose image was acquired by camera 3."""

  @classmethod
  def parse_paths(cls,
                  path_1: Path,
                  path_2: Path,
                  path_3: Path,
                  path_4: Path) -> TimePoint:
    """Given four paths to acquired images, creates an instance of the
    TimePoint class containing four the quadrants associated with these images.
    """

    # Associate each image to a quadrant
    path_a, path_b, path_c, path_d = None, None, None, None
    for path in (path_1, path_2, path_3, path_4):
      if path.name.endswith('0.png') or path.name.endswith('0.jpg'):
        path_a = path
        continue
      elif path.name.endswith('1.png') or path.name.endswith('1.jpg'):
        path_b = path
        continue
      elif path.name.endswith('2.png') or path.name.endswith('2.jpg'):
        path_c = path
        continue
      elif path.name.endswith('3.png') or path.name.endswith('3.jpg'):
        path_d = path
        continue

    # Ensure that all four quadrants were found
    if any(path is None for path in (path_a, path_b, path_c, path_d)):
      raise FileNotFoundError

    # Get the timestamp for each image
    try:
      time_a = path_to_time(path_a)
      time_b = path_to_time(path_b)
      time_c = path_to_time(path_c)
      time_d = path_to_time(path_d)
    except AttributeError:
      raise

    # Return the TimePoint instance containing the detected quadrants
    return cls(Quadrant(path_a, time_a, 0),
               Quadrant(path_b, time_b, 1),
               Quadrant(path_c, time_c, 2),
               Quadrant(path_d, time_d, 3))

  def export(self) -> List[Dict[str, Optional[Union[str, float, int]]]]:
    """Method called for formatting the acquired data before saving it in a
    csv file.

    It gathers for each detected spot its x and y position, and its radius.
    Also gets the timestamp of each quadrant, as a Unix timestamp and in
    human-readable format.

    Returns:
      A list of dictionaries containing all the information to save to the csv
      file, with one dictionary per well.
    """

    # The data to save is returned as a list of dictionaries
    ret = list()

    # Iterating over all 8 defined wells
    for quad in self:
      for well in quad:
        # For each spot, saving at least its quadrant, well, and timestamp
        item: dict[str, int | None] = dict(
          timestamp_seconds=quad.acq_time,
          timestamp_human=strftime('%d/%m/%Y %H:%M:%S',
                                   gmtime(quad.acq_time)),
          quadrant=quad.id,
          well=well.id)
        # Checking if the left spot is detected, and saving its data if so
        if well.spot_1 is not None:
          item['spot_1_x'] = well.spot_1.x
          item['spot_1_y'] = well.spot_1.y
          item['spot_1_r'] = well.spot_1.radius
        else:
          item['spot_1_x'] = None
          item['spot_1_y'] = None
          item['spot_1_r'] = None
        # Checking if the right spot is detected, and saving its data if so
        if well.spot_2 is not None:
          item['spot_2_x'] = well.spot_2.x
          item['spot_2_y'] = well.spot_2.y
          item['spot_2_r'] = well.spot_2.radius
        else:
          item['spot_2_x'] = None
          item['spot_2_y'] = None
          item['spot_2_r'] = None

        ret.append(item)
    return ret

  def __iter__(self) -> Iterator[Quadrant]:
    """Iterates over the quadrants, in the order 0, 1, 2, 3."""

    return iter((self.A, self.B, self.C, self.D))

  def __getitem__(self, item: int) -> Quadrant:
    """Allows to get the quadrant objects by index, for convenience."""

    if item == 0:
      return self.A
    elif item == 1:
      return self.B
    elif item == 2:
      return self.C
    elif item == 3:
      return self.D

    else:
      raise AttributeError

  def __bool__(self) -> bool:
    """Returns True if any of the quadrants has at least one defined well,
    False otherwise."""

    return any((self.A, self.B, self.C, self.D))
