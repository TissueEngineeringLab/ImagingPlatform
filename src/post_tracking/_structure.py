# coding: utf-8

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Iterator
from numpy import linalg
from pathlib import Path
from re import fullmatch
from calendar import timegm


def path_to_time(path: Path) -> float:
  """"""

  return timegm(tuple(map(int, fullmatch(r'(\d+)_(\d+)_(\d+)_(\d+)_'
                                         r'(\d+)_(\d+)_[ABCD]\.jpg',
                                         path.name).groups())))


@dataclass
class Spot:
  """"""

  x: int
  y: int

  radius: Optional[int] = None

  def __sub__(self, other: Spot) -> Spot:
    """"""

    return Spot(self.x - other.x, self.y - other.y, None)


@dataclass
class Well:
  """"""

  spot_1: Optional[Spot] = None
  spot_2: Optional[Spot] = None

  @property
  def distance(self) -> float:
    """"""

    if not self.is_defined:
      raise ValueError

    diff = self.spot_1 - self.spot_2
    return linalg.norm((diff.x, diff.y))

  @property
  def is_defined(self) -> bool:
    """"""

    return self.spot_1 is not None and self.spot_2 is not None

  def __iter__(self) -> Iterator[Spot]:
    return iter((self.spot_1, self.spot_2))


@dataclass
class Quadrant:
  """"""

  path: Path
  acq_time: float

  well_1: Well = field(default_factory=Well)
  well_2: Well = field(default_factory=Well)

  def __iter__(self) -> Iterator[Well]:
    return iter((self.well_1, self.well_2))


@dataclass
class TimePoint:
  """"""

  A: Quadrant
  B: Quadrant
  C: Quadrant
  D: Quadrant

  @classmethod
  def parse_paths(cls, path_1: Path, path_2: Path,
                  path_3: Path, path_4: Path) -> TimePoint:
    """"""

    path_a, path_b, path_c, path_d = None, None, None, None
    for path in (path_1, path_2, path_3, path_4):
      if 'A' in path.name:
        path_a = path
        continue
      elif 'B' in path.name:
        path_b = path
        continue
      elif 'C' in path.name:
        path_c = path
        continue
      elif 'D' in path.name:
        path_d = path
        continue

    if any(path is None for path in (path_a, path_b, path_c, path_d)):
      raise FileNotFoundError

    try:
      time_a = path_to_time(path_a)
      time_b = path_to_time(path_b)
      time_c = path_to_time(path_c)
      time_d = path_to_time(path_d)
    except AttributeError:
      raise

    return cls(Quadrant(path_a, time_a),
               Quadrant(path_b, time_b),
               Quadrant(path_c, time_c),
               Quadrant(path_d, time_d))
