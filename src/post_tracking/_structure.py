# coding: utf-8

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Iterator, List, Dict, Union
from numpy import linalg
from pathlib import Path
from re import fullmatch
from calendar import timegm
from time import gmtime, strftime


def path_to_time(path: Path) -> float:
  """"""

  return timegm(tuple(map(int, fullmatch(r'(\d+)_(\d+)_(\d+)_(\d+)_'
                                         r'(\d+)_(\d+)_[ABCD]\.jpg',
                                         path.name).groups())))


def path_to_str(path: Path) -> str:
  """"""

  return '{}/{}/{} {}:{}:{}'.format(*fullmatch(r'(\d+)_(\d+)_(\d+)_(\d+)_'
                                               r'(\d+)_(\d+)_[ABCD]\.jpg',
                                               path.name).groups())


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

  id: int

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

  def __getitem__(self, index: int) -> Spot:
    """"""

    if index in (-2, 0):
      return self.spot_1
    elif index in (-1, 1):
      return self.spot_2
    else:
      raise IndexError

  def __setitem__(self, index: int, value: Optional[Spot]) -> None:
    """"""

    if index in (-2, 0):
      self.spot_1 = value
    elif index in (-1, 1):
      self.spot_2 = value
    else:
      raise IndexError


@dataclass
class Quadrant:
  """"""

  path: Path
  acq_time: float
  id: str

  well_1: Well = field(default_factory=lambda: Well(0))
  well_2: Well = field(default_factory=lambda: Well(1))

  def __iter__(self) -> Iterator[Well]:
    return iter((self.well_1, self.well_2))

  def __getitem__(self, index: int) -> Well:
    """"""

    if index in (-2, 0):
      return self.well_1
    elif index in (-1, 1):
      return self.well_2
    else:
      raise IndexError

  def __bool__(self) -> bool:
    """"""

    return self.well_1.is_defined or self.well_2.is_defined


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

    return cls(Quadrant(path_a, time_a, 'A'),
               Quadrant(path_b, time_b, 'B'),
               Quadrant(path_c, time_c, 'C'),
               Quadrant(path_d, time_d, 'D'))

  def export(self) -> List[Dict[str, Optional[Union[str, float, int]]]]:
    """"""

    ret = list()
    for quad in self:
      for well in quad:
        item = dict(timestamp_seconds=quad.acq_time,
                    timestamp_human=strftime('%d/%m/%Y %H:%M:%S',
                                             gmtime(quad.acq_time)),
                    quadrant=quad.id,
                    well=well.id)
        if well.spot_1 is not None:
          item['spot_1_x'] = well.spot_1.x
          item['spot_1_y'] = well.spot_1.y
          item['spot_1_r'] = well.spot_1.radius
        else:
          item['spot_1_x'] = None
          item['spot_1_y'] = None
          item['spot_1_r'] = None
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
    """"""

    return iter((self.A, self.B, self.C, self.D))

  def __getitem__(self, item: str) -> Quadrant:
    """"""

    if item == 'A':
      return self.A
    elif item == 'B':
      return self.B
    elif item == 'C':
      return self.C
    elif item == 'D':
      return self.D

    else:
      raise AttributeError

  def __bool__(self) -> bool:
    """"""

    return any((self.A, self.B, self.C, self.D))
