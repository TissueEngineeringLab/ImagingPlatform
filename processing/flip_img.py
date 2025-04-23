# coding: utf-8

from pathlib import Path
import cv2
from tqdm.auto import tqdm
import sys
import concurrent.futures
from itertools import chain


def flip_img(img_pth: Path) -> None:
  """Flips the image if it comes from camera 2 or 3, and overwrites the
  original file.

  Args:
    img_pth: The path to the image to flip.
  """
  
  if img_pth.name.endswith("2.png") or img_pth.name.endswith("3.png"):
    cv2.imwrite(str(img_pth), cv2.flip(cv2.imread(str(img_pth)), -1))


if __name__ == "__main__":

  # The images can be JPEG or PNG
  base_path = Path(__file__).parent
  images = tuple(chain((base_path.parent / "images").glob("*.png"),
                       (base_path.parent / "images").glob("*.jpg")))
  # Iterating over all the images
  with tqdm(total=len(images),
            desc='Flipping the images',
            file=sys.stdout,
            colour='green') as pbar:
    # Processing the images in a parallelized way for efficiency
    with concurrent.futures.ProcessPoolExecutor() as executor:
      for _ in executor.map(flip_img, images, chunksize=1):
        pbar.update()
        pbar.refresh()
