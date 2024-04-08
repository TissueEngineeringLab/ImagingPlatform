# coding: utf-8

import numpy as np
from PIL import Image

from ._plot import save_overlay, draw_img, plot_distance
from ._tracking import track_spot
from ._config import name2time, configure


if __name__ == "__main__":

  plate, base_path, path_format, save, border, images, camera = configure()

  for i, path in enumerate(images):

    if all(spot.lost for well in plate for spot in well):
      break

    img = np.array(Image.open(path))
    plate.timestamps.append(name2time(path.stem, path_format))

    for well in plate:
      for spot in well:
        if not spot.lost:
            track_spot(img, spot, border)
      if all(not spot.lost for spot in well):
        well.distances.append(well.spot_1 - well.spot_2)

    if save:
      save_overlay(img, plate, path)

    if not i % 50:
      draw_img(img, plate)

  plot_distance(plate, name2time(images[0].stem, path_format), save,
                base_path.parent.parent / f'result_{camera}.png')
