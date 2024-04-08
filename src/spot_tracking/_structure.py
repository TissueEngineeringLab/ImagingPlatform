# coding: utf-8

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Iterator
from math import sqrt


@dataclass
class Spot:
  """"""

  y_min: int
  x_min: int
  y_max: int
  x_max: int

  x_offset: int
  y_offset: int

  y_center: Optional[int] = None
  x_center: Optional[int] = None

  lost: bool = False
  threshold: Optional[int] = None

  def __sub__(self, other: Spot) -> float:

    return sqrt(((self.x_center + self.x_offset) -
                 (other.x_center + other.x_offset)) ** 2 +
                ((self.y_center + self.y_offset) -
                 (other.y_center + other.y_offset)) ** 2)


@dataclass
class Well:
  """"""

  spot_1: Spot
  spot_2: Spot

  distances: List[float] = field(default_factory=list)

  def __iter__(self) -> Iterator[Spot]:
    return iter((self.spot_1, self.spot_2))


@dataclass
class Quadrant:
  """"""

  well_1: Well
  well_2: Well

  timestamps: List[float] = field(default_factory=list)

  def __iter__(self) -> Iterator[Well]:
    return iter((self.well_1, self.well_2))
