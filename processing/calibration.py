# coding: utf-8

from pathlib import Path
import numpy as np
import cv2
from matplotlib import pyplot as plt
from tqdm.auto import tqdm
from itertools import repeat, chain
from re import match, sub
import sys
import concurrent.futures
import pickle


def find_corners(img: np.ndarray,
                 thresh: int,
                 n_rows: int,
                 n_cols: int) -> tuple[np.ndarray, bool]:
  """Finds the corners of a chessboard pattern on the provided image, and 
  returns their coordinates.
  
  Args:
    img: The image in which to search the chessboard pattern, as a numpy array.
    thresh: The intensity threshold to use for performing binarization on the
      image, as an integer.
    n_rows: The number of rows in the chessboard, minus one.
    n_cols: The number of columns in the chessboard, minus one.
  
  Returns:
    A numpy array containing the coordinates of the detected corners in the
    chessboard, and a boolean indicating whether the detection was successful.
  """
  
  # A black and white image is needed to find the corners
  gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
  _, thresh_img = cv2.threshold(gray_img, thresh, 255, cv2.THRESH_BINARY)
  
  # Perform the corner detection
  ret_val, corners = cv2.findChessboardCornersSB(thresh_img,
                                                 (n_rows, n_cols),
                                                 cv2.CALIB_CB_EXHAUSTIVE)
  
  if not ret_val:
    raise RuntimeError("The detection of the chessboard corners failed !")
  
  # Refine the corner detection in a second step
  corners = cv2.cornerSubPix(thresh_img, 
                             corners, 
                             (11, 11), 
                             (-1, -1), 
                             (cv2.TERM_CRITERIA_EPS + 
                              cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
  
  return corners, ret_val


def undistort_image(img: np.ndarray, 
                    camera_matrix: np.ndarray, 
                    distortion_coeffs: np.ndarray) -> np.ndarray:
  """Corrects the distortion on the given image, based on the provided matrix 
  and coefficients computed previously.
  
  Args:
    img: The image to correct, as a numpy array.
    camera_matrix: The intrinsic camera parameters, as computed by the 
      cv2.calibrateCamera method.
    distortion_coeffs: The distortion coefficients, as computed by the 
      cv2.calibrateCamera method.
  
  Returns:
    The corrected image as a numpy array.
  """
  
  height, width, *_ = img.shape
  # Computes optimal coefficients before performing the correction
  (new_camera_matrix, 
   valid_pixels_roi) = cv2.getOptimalNewCameraMatrix(camera_matrix, 
                                                     distortion_coeffs,
                                                     (width, height), 
                                                     1.0, 
                                                     (width, height))
  # Performs the actual image correction
  undistorted = cv2.undistort(img, 
                              camera_matrix, 
                              distortion_coeffs, 
                              None, 
                              new_camera_matrix)
  return undistorted


def calibrate(img_path: Path,
              n_rows: int,
              n_cols: int,
              chess_square_dim: float,
              thresh: int = 100,
              show: bool = False) -> tuple[float, float, 
                                           np.ndarray, np.ndarray, 
                                           tuple[slice, slice]]:
  """Performs a chessboard pattern detection on the provided image, and uses it
  to determine the calibration and distortion coefficients.
  
  These values can then be used to correct the provided image.
  
  Also returns the scale in pixels per mm for the x and y axes.
  
  Args:
    img_path: The path to the image to use for calibration.
    n_rows: The number of rows in the chessboard, minus one.
    n_cols: The number of columns in the chessboard, minus one.
    chess_square_dim:
    thresh: An intensity threshold to use for performing binarization on the
      image, as an integer.
    show: A boolean indicating whether to display images summarizing the output 
      of the calibration.
  Returns:
    The two scale factors in pixels per mm for the x and y axes, as floats, the
    intrinsic camera calibration parameters as a numpy array, the image
    distortion coefficients as a numpy array, and a tuple of slices indicating
    the area in which the calibration is valid.
  """
  
  # Factor for rescaling the images as the calibration cannot be performed on
  # the original ones, that are too large
  rescale_factor = 4
  
  # Coordinates of the points in real life, i.e. their theoretical position
  chess_pts = np.zeros((n_rows * n_cols, 3), dtype=np.float32)
  chess_pts[:, :2] = (np.mgrid[0:n_rows, 0:n_cols]).T.reshape(-1, 2)
  
  # Read the calibration image and resize it so that it is small enough
  img = cv2.imread(str(img_path))
  height, width, *_ = img.shape
  img = cv2.resize(img, (width // rescale_factor, height // rescale_factor))
  
  # Keep only the relevant region of the image
  img_calib = np.full_like(img, 190)
  height, width, *_ = img.shape
  if img_path.name.endswith("0.png"):
    h_slice = slice(int(0.19 * height), int(0.53 * height), 1)
    w_slice = slice(int(0.24 * width), int(0.75 * width), 1)
  elif img_path.name.endswith("1.png"):
    h_slice = slice(int(0.18 * height), int(0.53 * height), 1)
    w_slice = slice(int(0.22 * width), int(0.73 * width), 1)
  elif img_path.name.endswith("2.png"):
    h_slice = slice(int(0.41 * height), int(0.75 * height), 1)
    w_slice = slice(int(0.23 * width), int(0.74 * width), 1)
  elif img_path.name.endswith("3.png"):
    h_slice = slice(int(0.43 * height), int(0.76 * height), 1)
    w_slice = slice(int(0.19 * width), int(0.70 * width), 1)
  elif img_path.name.endswith("4.png"):
    h_slice = slice(int(0.48 * height), int(0.82 * height), 1)
    w_slice = slice(int(0.24 * width), int(0.75 * width), 1)
  elif img_path.name.endswith("5.png"):
    h_slice = slice(int(0.48 * height), int(0.82 * height), 1)
    w_slice = slice(int(0.21 * width), int(0.73 * width), 1)
  else:
    raise RuntimeError("Got image with wrong index")
  img_calib[h_slice, w_slice] = img[h_slice, w_slice]
  
  # Find the corners of the chessboard
  detected_corners, ret_find_corn = find_corners(img_calib,
                                                 thresh,
                                                 n_rows,
                                                 n_cols)
  
  # Determine the calibration coefficients for the image
  (error_calib, 
   camera_matrix, 
   distortion_coeffs, 
   rotation_vectors, 
   translation_vectors) = cv2.calibrateCamera((chess_pts,),
                                              (detected_corners,),
                                              img_calib.shape[:2][::-1],
                                              None,
                                              None)
  
  # Correct the distortion on the original image
  undistorted = undistort_image(img, 
                                camera_matrix,
                                distortion_coeffs)
  
  # Detect the chessboard pattern on the corrected image
  undist_calib = np.full_like(img_calib, 190)
  undist_calib[h_slice, w_slice] = undistorted[h_slice, w_slice]
  corners_undistorted, ret_corn_undist = find_corners(undist_calib,
                                                      thresh,
                                                      n_rows,
                                                      n_cols)
  # Reshape to match grid size
  corners_undistorted_rshp = corners_undistorted.reshape((n_cols, n_rows, 2))
  
  # Identify the extreme points
  top_right = corners_undistorted_rshp[0, 0]
  top_left = corners_undistorted_rshp[-1, 0]
  bottom_left = corners_undistorted_rshp[-1, -1]
  bottom_right = corners_undistorted_rshp[0, -1]
  
  # Define the limits in which the correction is valid, and add 10% horizontal
  min_w = min(top_right[0], top_left[0], bottom_right[0], bottom_left[0])
  max_w = max(top_right[0], top_left[0], bottom_right[0], bottom_left[0])
  min_h = min(top_right[1], top_left[1], bottom_right[1], bottom_left[1])
  max_h = max(top_right[1], top_left[1], bottom_right[1], bottom_left[1])
  roi_w = slice(int(rescale_factor * (min_w - 0.1 * (max_w - min_w))), 
                int(rescale_factor * (max_w + 0.1 * (max_w - min_w))))
  roi_h = slice(int(rescale_factor * min_h), int(rescale_factor * max_h))
  
  # Calculate the average number of pixels in each direction
  pix_x = (np.sqrt(np.sum((top_right - top_left) ** 2)) + 
           np.sqrt(np.sum((bottom_right - bottom_left) ** 2))) / 2
  pix_y = (np.sqrt(np.sum((top_right - bottom_right) ** 2)) + 
           np.sqrt(np.sum((top_left - bottom_left) ** 2))) / 2
  
  # Calculate the final pixel/mm ratio in both directions
  pix_mm_x = rescale_factor * pix_x / ((n_cols - 1) * chess_square_dim)
  pix_mm_y = rescale_factor * pix_y / ((n_rows - 1) * chess_square_dim)
  
  # Some coefficients of the scaling matrix need to be adapted for the original
  # images
  rescaled_matrix = camera_matrix.copy()
  rescaled_matrix[:2] *= rescale_factor
  
  # For debugging, displaying the original and corrected images with the 
  # detected chessboards
  if show:
  
    plt.figure()
    # Display the original image and its detected chessboard
    plt.subplot(221)
    cv2.drawChessboardCorners(img, 
                              (n_rows, n_cols), 
                              detected_corners, 
                              ret_find_corn)
    plt.imshow(img)
    plt.title("Original image")
    
    # Display the corrected image and its detected chessboard
    plt.subplot(222)
    cv2.drawChessboardCorners(undistorted, 
                              (n_rows, n_cols), 
                              corners_undistorted, 
                              ret_corn_undist)
    plt.imshow(undistorted)
    plt.title("Corrected image")
    
    # Align the corrected corners with the original ones for display
    corners_undistorted += detected_corners[0, 0] - corners_undistorted[0, 0]
    
    # Display a close-up on the chessboard area
    plt.subplot(212)
    cv2.drawChessboardCorners(img, 
                              (n_rows, n_cols), 
                              corners_undistorted, 
                              ret_corn_undist)
    plt.imshow(img[h_slice, w_slice])
    plt.title("Effect of the correction")
    plt.show()
  
  return (pix_mm_x, pix_mm_y, rescaled_matrix, distortion_coeffs,
          (roi_h, roi_w))


def crop_to_roi(img_path: Path, 
                dest_folder: Path,
                params: dict[str, tuple[float, float, np.ndarray, np.ndarray,
                                        tuple[slice, slice]]]) -> None:
  """Uses the parameters computed by the calibrate function to correct the 
  provided image, then crops it to the region of interest and saves it at the 
  indicated location.
  
  Args:
    img_path: The path to the image on which to apply the correction.
    dest_folder: The folder where to save the cropped and corrected image.
    params: A tuple containing the parameters necessary for calibration, as 
      returned by the calibrate function.
  """
  
  # Retrieve the correct calibration parameters for the provided image
  idx = match(r'.+?(\d)\.png', str(img_path.name)).groups()[0]
  if idx == '0':
    idxs = ('0', '4')
  elif idx == '1':
    idxs = ('1', '5')
  elif idx == '2':
    idxs = ('2',)
  elif idx == '3':
    idxs = ('3',)
  else:
    raise RuntimeError("Got image with wrong index")

  for idx in idxs:
    fx, fy, mat, coe, (roi_h, roi_w) = params[idx]

    # Undistort the image using the correct parameters
    img = cv2.imread(str(img_path))
    img = undistort_image(img, mat, coe)

    # Resize the image to have a 1:1 ratio between x and y
    # Also crop it to keep only the valid part of the image
    fxx = 1.0 if fx > fy else fy / fx
    fyy = 1.0 if fy > fx else fx / fy
    img = cv2.resize(img[roi_h, roi_w], None, fx=fxx, fy=fyy)

    # Write the cropped and corrected image at the given location
    name = sub(r"\d\.", f"{idx}.", img_path.name)
    cv2.imwrite(str(dest_folder / name), img)


if __name__ == "__main__":
  
  base_path = Path(".")
  calib_images = tuple(base_path.glob("*.png"))
  calib_params = dict()
  for path in tqdm(calib_images,
                   total=len(calib_images),
                   desc='Computing the calibration parameters',
                   file=sys.stdout,
                   colour='green'):
    
    index = match(r'.*(\d)\.png', str(path.name)).groups()[0]
    calib_params[index] = calibrate(img_path=path, 
                                    n_rows=7, 
                                    n_cols=16, 
                                    chess_square_dim=3.0,
                                    thresh=100, 
                                    show=False)
  
  with open(base_path / 'calib_params.pickle', 'wb') as pickle_file:
    pickle.dump(calib_params, pickle_file, protocol=pickle.HIGHEST_PROTOCOL)

  images = tuple(chain((base_path.parent / "images").glob("*.png"),
                       (base_path.parent / "images").glob("*.jpg")))
  dest = Path(base_path.parent / "cropped")
  dest.mkdir(exist_ok=True, parents=True)
  with tqdm(total=len(images),
            desc='Extracting the regions of interest',
            file=sys.stdout,
            colour='green') as pbar:
    with concurrent.futures.ProcessPoolExecutor() as executor:
      for _ in executor.map(crop_to_roi, 
                            images, 
                            repeat(dest, len(images)),
                            repeat(calib_params),
                            chunksize=1):
        pbar.update()
        pbar.refresh()
