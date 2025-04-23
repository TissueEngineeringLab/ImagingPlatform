# coding: utf-8

from pathlib import Path
import cv2
from tqdm.auto import tqdm
import sys
import concurrent.futures
from itertools import chain


def flip_img(img_pth: Path) -> None:
  """"""
  
  if img_pth.name.endswith("2.png") or img_pth.name.endswith("3.png"):
    cv2.imwrite(str(img_pth), cv2.flip(cv2.imread(str(img_pth)), -1))


if __name__ == "__main__":

  base_path = Path(__file__).parent
  images = tuple(chain((base_path.parent / "images").glob("*.png"),
                       (base_path.parent / "images").glob("*.jpg")))
  with tqdm(total=len(images),
            desc='Flipping the images',
            file=sys.stdout,
            colour='green') as pbar:
    with concurrent.futures.ProcessPoolExecutor() as executor:
      for _ in executor.map(flip_img, images, chunksize=1):
        pbar.update()
        pbar.refresh()
