# coding: utf-8

from pathlib import Path
from time import strptime, mktime
import tomli
from typing import Tuple, List
import numpy as np
from PIL import Image

from ._structure import Quadrant
from ._tracking import detect_spots


def name2time(name: str, str_format: str) -> float:
  """"""

  return mktime(strptime(name, str_format))


def configure() -> Tuple[Quadrant, Path, str, bool, int, List[Path], str]:
  """"""

  config = tomli.loads(Path('config.toml').read_text())
  base_path = Path(config['images']['path']['base'])
  camera = config['processing']['camera']
  path_format = f"{config['images']['path']['format']}_{camera}"
  save = config['processing']['save']
  t_min = name2time(f"{config['images']['t_min']}_{camera}", path_format)
  border = config['processing']['border']

  images = sorted(Path(base_path).glob(f"*_{camera}.jpg"),
                  key=lambda p: name2time(p.stem, path_format))
  images = [img for img in images if name2time(img.stem, path_format) >= t_min]

  oy_1 = config['ROI'][camera]['left']['oy']
  ox_1 = config['ROI'][camera]['left']['ox']
  ly_1 = config['ROI'][camera]['left']['ly']
  lx_1 = config['ROI'][camera]['left']['lx']
  thresh_1 = config['ROI'][camera]['left']['thresh']

  oy_2 = config['ROI'][camera]['right']['oy']
  ox_2 = config['ROI'][camera]['right']['ox']
  ly_2 = config['ROI'][camera]['right']['ly']
  lx_2 = config['ROI'][camera]['right']['lx']
  thresh_2 = config['ROI'][camera]['right']['thresh']

  img = np.array(Image.open(images[0]))

  w1 = detect_spots(img, oy_1, ox_1, ly_1, lx_1, thresh_1)
  w2 = detect_spots(img, oy_2, ox_2, ly_2, lx_2, thresh_2)

  return Quadrant(w1, w2), base_path, path_format, save, border, images, camera
