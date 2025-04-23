# coding: utf-8

from scipy.signal import savgol_filter
from scipy.interpolate import CloughTocher2DInterpolator
from matplotlib import pyplot as plt
import pandas as pd
from pathlib import Path
import pickle
import numpy as np
from collections import defaultdict
from itertools import product
from datetime import datetime
from copy import deepcopy

# Correspondence between the index of a well and its position on the plate
pos_to_label = {(0, 0): "A2",
                (0, 1): "A1",
                (1, 0): "A4",
                (1, 1): "A3",
                (2, 0): "C2",
                (2, 1): "C1",
                (3, 0): "C4",
                (3, 1): "C3",
                (4, 0): "B2",
                (4, 1): "B1",
                (5, 0): "B4",
                (5, 1): "B3"}

# For each well, the effective length of the pin as measured
label_to_length = {"A1": 5.0,
                   "A2": 5.0,
                   "A3": 5.5,
                   "A4": 5.7,
                   "B1": 5.2,
                   "B2": 5.3,
                   "B3": 5.1,
                   "B4": 5.9,
                   "C1": 4.9,
                   "C2": 5.0,
                   "C3": 5.8,
                   "C4": 5.2}

# Indicates the moments when the medium was refreshed
refreshments = ("28/02/2025 16:53:34",
                "02/03/2025 17:53:34",
                "04/03/2025 17:53:34",
                "06/03/2025 16:53:34",
                "08/03/2025 20:53:34",
                "10/03/2025 16:53:34",
                "12/03/2025 16:53:34",
                "14/03/2025 18:53:34",
                "17/03/2025 14:53:34")


def formatter(x: float, _) -> str:
  """Helper function for a nicer display of time on the generated graphs."""

  return f"{x // (3600 * 24)}d, {(x % (3600 * 24)) // 3600}h"


def plot_results(img_calib_file: Path,
                 results_file: Path,
                 pins_calib_file: Path) -> None:
  """Reads the various results and calibration files from the pin tracking
  process, and generates graphs summarizing the output.

  Args:
    img_calib_file: Path to the .pickle file containing all the calibration
      parameters for the optical correction.
    results_file: Path to the .csv file containing the raw output from the
      pin tracking interface.
    pins_calib_file: Path to the .csv file containing the force-to-displacement
      information obtained using finite elements modelling.
  """

  # Load the calibration file
  with open(img_calib_file, 'rb') as file:
    calib = pickle.load(file)

  # Read the results file and compute the distance between the pins
  res = pd.read_csv(results_file)
  res['Distance px'] = np.sqrt((res['spot_2_x'] - res['spot_1_x']) ** 2 +
                               (res['spot_2_y'] - res['spot_1_y']) ** 2)

  # Read the pins calibration file and create an interpolator from its values
  calib_data = pd.read_csv(pins_calib_file)
  force_interp = CloughTocher2DInterpolator(
    np.stack((calib_data["Distance (mm)"].values,
              calib_data["Length (mm)"].values), axis=1),
    calib_data["Force (mN)"].values)

  # Plot the output of the pin calibration, to ensure it is correct
  plt.figure()
  dist_grid = np.linspace(calib_data["Distance (mm)"].min(),
                          calib_data["Distance (mm)"].max())
  length_grid = np.linspace(calib_data["Length (mm)"].min(),
                            calib_data["Length (mm)"].max())
  grid = np.meshgrid(dist_grid, length_grid)
  force_grid = force_interp(*grid)
  plt.pcolormesh(*grid, force_grid, shading='auto', cmap="plasma")
  plt.plot(calib_data["Distance (mm)"].values,
           calib_data["Length (mm)"].values, "ok", label="Data points")
  plt.legend()
  plt.xlabel("Pin displacement (mm)")
  plt.ylabel("Pin length (mm)")
  plt.colorbar(label="Force (mN)")
  plt.contour(*grid, force_grid, cmap="GnBu")
  plt.show()

  # Compute the distance between the pins in mm for each moment and each well
  dist_dict = defaultdict(dict)
  for quad, well in product((0, 1, 2, 3, 4, 5), (0, 1)):

    # Retrieve the pixel-to-mm ratio for the specific well
    fx, fy, *_ = calib[str(quad)]
    ratio = max(fx, fy)

    # Convert the time to a date, and smoothen the measured signal
    dist_dict[quad][well] = [
      list(map(datetime.fromtimestamp,
               res[(res['quadrant'] == quad) &
                   (res['well'] == well)]['timestamp_seconds'].values)),
      savgol_filter(res[(res['quadrant'] == quad) &
                        (res['well'] == well)]['Distance px'].values, 40, 3)]
    # Convert to mm, and offset the distance and the time to the first values
    dist_dict[quad][well][1] /= ratio
    dist_dict[quad][well][1] -= np.mean(dist_dict[quad][well][1][:20])
    dist_dict[quad][well][0] = list(
      map(lambda t: t - dist_dict[quad][well][0][0], dist_dict[quad][well][0]))

  # From the computed distance, calculate the effort for each well and moment
  force_dict = deepcopy(dist_dict)
  for quad, well in product((0, 1, 2, 3, 4, 5), (0, 1)):
    force_dict[quad][well][1] = force_interp(
      abs(dist_dict[quad][well][1]),
      label_to_length[pos_to_label[(quad, well)]])

  # Also retrieve the moments when the medium was refreshed
  refresh_timestamps = tuple(map(
    datetime.fromtimestamp,
    (res[res['timestamp_human'] == ref_t].iloc[0]['timestamp_seconds']
     for ref_t in refreshments)))
  refresh_timestamps = tuple(
    map(lambda t: t - datetime.fromtimestamp(res.iloc[0]['timestamp_seconds']),
        refresh_timestamps))

  # Plot the distance vs time chart, with a color for each well
  plt.figure()
  ax = plt.subplot()
  ax.xaxis.set_major_formatter(formatter)
  for quad, well in product((0, 1, 2, 3, 4, 5), (0, 1)):
    plt.plot([t.total_seconds() for t in dist_dict[quad][well][0]],
             dist_dict[quad][well][1], label=pos_to_label[(quad, well)])
  lim = ax.get_ylim()
  for t in refresh_timestamps:
    plt.vlines(t.total_seconds(), *lim, alpha=0.5)
  plt.xlabel("Time in culture")
  plt.ylabel("Distance between the pins (mm)")
  plt.legend()

  # Plot the distance vs time chart, with a color for each condition
  plt.figure()
  ax = plt.subplot()
  ax.xaxis.set_major_formatter(formatter)
  labels = list()
  for quad, well in product((0, 1, 2, 3, 4, 5), (0, 1)):
    if pos_to_label[(quad, well)].endswith(("1", "2")):
      color = 'red'
      label = "0.5M cells"
    else:
      color = 'blue'
      label = "1M cells"
    plt.plot([t.total_seconds() for t in force_dict[quad][well][0]],
             dist_dict[quad][well][1], color=color,
             label=label if label not in labels else None)
    labels.append(label)
  lim = ax.get_ylim()
  for t in refresh_timestamps:
    plt.vlines(t.total_seconds(), *lim, alpha=0.5)
  plt.xlabel("Time in culture")
  plt.ylabel("Distance between the pins (mm)")
  plt.legend()

  # Plot the force vs time chart, with a color for each well
  plt.figure()
  ax = plt.subplot()
  ax.xaxis.set_major_formatter(formatter)
  for quad, well in product((0, 1, 2, 3, 4, 5), (0, 1)):
    plt.plot([t.total_seconds() for t in force_dict[quad][well][0]],
             force_dict[quad][well][1], label=pos_to_label[(quad, well)])
  lim = ax.get_ylim()
  for t in refresh_timestamps:
    plt.vlines(t.total_seconds(), *lim, alpha=0.5)
  plt.xlabel("Time in culture")
  plt.ylabel("Force exerted by the BAM (mN)")
  plt.legend()

  # Plot the force vs time chart, with a color for each condition
  plt.figure()
  ax = plt.subplot()
  ax.xaxis.set_major_formatter(formatter)
  labels = list()
  for quad, well in product((0, 1, 2, 3, 4, 5), (0, 1)):
    if pos_to_label[(quad, well)].endswith(("1", "2")):
      color = 'red'
      label = "0.5M cells"
    else:
      color = 'blue'
      label = "1M cells"
    plt.plot([t.total_seconds() for t in force_dict[quad][well][0]],
             force_dict[quad][well][1], color=color,
             label=label if label not in labels else None)
    labels.append(label)
  lim = ax.get_ylim()
  for t in refresh_timestamps:
    plt.vlines(t.total_seconds(), *lim, alpha=0.5)
  plt.xlabel("Time in culture")
  plt.ylabel("Force exerted by the BAM (mN)")
  plt.legend()

  plt.show()


if __name__ == "__main__":

  base_path = Path(__file__).parent
  calib_path = base_path / "calibration_pins.csv"
  plot_results(base_path / "calib_params.pickle",
               base_path / "results.csv",
               calib_path)
