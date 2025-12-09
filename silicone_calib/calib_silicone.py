# coding: utf-8

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from pathlib import Path
from scipy.signal import find_peaks, savgol_filter
from scipy.optimize import least_squares
from scipy.stats import linregress
from itertools import batched


def yeoh_model_3(x: np.ndarray, strain: np.ndarray) -> np.ndarray:
  """Computes the stress from a given strain array, using Yeoh's third-order
  model and the provided coefficients."""

  return (2 * (strain - 1 / (strain ** 2)) *
          (x[0] +
           2 * x[1] * (strain ** 2 + 2 / strain - 3) +
           3 * x[2] * (strain ** 2 + 2 / strain - 3) ** 2))


def least_square_wrapper(x: np.ndarray,
                         strain: np.ndarray,
                         stresses: tuple[np.ndarray, ...]) -> float:
  """Convenience function returning the total error between the experimental
  and modeled data."""

  error = 0.0
  for stress in stresses:
    error += np.sum(np.power(yeoh_model_3(x, strain) - stress, 2), axis=None)
  return error


def cantilever_formula(disp: np.ndarray,
                       young: float,
                       length: float,
                       diameter: float) -> np.ndarray:
  """Computes the force from all the input parameters, using the cantilever
  formula."""

  inertia = np.pi * diameter ** 4 / 64
  return 3 * young * inertia * disp / length ** 3 * 10 ** 3


if __name__ == '__main__':

  stress_data = dict()
  strain_data = dict()

  thickness = 3
  width = 10

  # For each data folder, compute the stress and the strain
  for folder in (Path('sample_1'), Path('sample_2'), Path('sample_3')):
    data = pd.read_csv(folder / 'data.csv')

    # Filter to keep only data before force peak
    data = data.iloc[:data['F(N)'].idxmax()]
    # Apply a 5N threshold
    data = data[data['F(N)'] > 5.0]

    # Smoothen the data
    exx_smooth = savgol_filter(data['Exx(%)'], 200, 3)
    lambda_ = exx_smooth / 100 + 1
    force_smooth = savgol_filter(data['F(N)'], 200, 3)

    # Detect force steps using the first derivative
    df_dt = savgol_filter(force_smooth - force_smooth[0], 20, 3, deriv=1)
    peaks, *_ = find_peaks(df_dt, prominence=0.01, height=0.01, distance=1000)
    peaks -= 150  # To use the stress value right before a force step

    # Offset the data
    force_smooth = force_smooth[peaks]
    force_smooth -= force_smooth[0]
    stress = force_smooth / thickness / width
    lambda_ = lambda_[peaks]
    lambda_ /= lambda_[0]

    # Save stress and strain for later
    strain_data[folder.name] = lambda_
    stress_data[folder.name] = stress

  # Put all data points on the same strain base for convenience
  stress_data_interp = dict()
  stress_data_interp['sample_1'] = stress_data['sample_1'][:-1]
  stress_data_interp['sample_2'] = np.interp(strain_data['sample_1'][:-1],
                                             strain_data['sample_2'],
                                             stress_data['sample_2'])
  stress_data_interp['sample_3'] = np.interp(strain_data['sample_1'][:-1],
                                             strain_data['sample_3'],
                                             stress_data['sample_3'])

  # Determine the best material coefficients
  yeoh_coeffs = least_squares(least_square_wrapper,
                              x0=(0.1, 0.01, 0.1),
                              bounds=(0.0, np.inf),
                              args=(strain_data['sample_1'][:-1],
                                    stress_data_interp.values())).x

  # Print the Yeoh coefficients and the Pearson coefficient
  print(f"\nYeoh coeffs:\n"
        f"{'\n'.join(f'C{i} = {coef:.4f}' for i, coef 
                     in enumerate(yeoh_coeffs))}\n")
  x_regress = np.concatenate((stress_data['sample_1'],
                              stress_data['sample_2'],
                              stress_data['sample_3']), axis=0)
  y_regress = yeoh_model_3(yeoh_coeffs,
                           np.concatenate((strain_data['sample_1'],
                                           strain_data['sample_2'],
                                           strain_data['sample_3']), axis=0))
  print(f"R²: {linregress(x_regress, y_regress)[2]:.4f}")

  # Plot the result curve
  plt.figure(figsize=(12, 9))
  for i, (sample, color) in enumerate(zip(('sample_1', 'sample_2', 'sample_3'),
                                          ('b+', 'g+', 'r+'))):
    plt.plot(strain_data[sample],
             stress_data[sample],
             color,
             label=f'Sample {i + 1}',
             markersize=12)
  plt.plot(strain_data['sample_1'],
           yeoh_model_3(yeoh_coeffs, strain_data['sample_1']),
           'k--',
           label='Model')
  plt.legend(fontsize=12)
  plt.xlabel("Strain (mm/mm)", fontsize=12)
  plt.ylabel("Stress (MPa)", fontsize=12)
  plt.xticks(fontsize=12)
  plt.yticks(fontsize=12)
  ax = plt.gca()
  ax.spines[['right', 'top']].set_visible(False)
  # plt.savefig('./tensile_curves.svg', dpi=300)
  plt.show()
  plt.close()

  expe_data = pd.read_csv('./flexion_expe.csv')
  force = np.array(tuple(batch for batch in
                         batched(expe_data['Force (mN)'].tolist(), 9)))
  pos = expe_data['Displacement (mm)'].iloc[:9].values
  force = np.delete(force, (1, 3, 6, 14), 0)

  simu_data = pd.read_csv('./flexion_simu.csv')
  
  a = np.interp(pos, simu_data['U(mm)'],
                simu_data['RF(mN) ssvisco encas surf'])[pos < 2.7]
  b = np.mean(force, axis=0)[pos < 2.7]
  
  print(np.mean(np.nan_to_num(np.abs((b - a) / b))))

  plt.figure(figsize=(12, 9))
  for i, batch in enumerate(force.tolist()):
    plt.plot(pos, batch, color='grey', alpha=0.2,
             label='Expe. data' if not i else None)
  plt.fill_between(pos, np.min(force, axis=0), np.max(force, axis=0),
                   color='silver', alpha=0.2, label='Expe. envelope')
  plt.plot(pos, np.mean(force, axis=0), color='blue', label='Expe. average')
  plt.plot(simu_data['U(mm)'], simu_data['RF(mN) ssvisco encas surf'],
           label='Simulation', color='tomato')
  plt.plot(pos, cantilever_formula(pos, 0.251 * 6, 8, 1),
           color='forestgreen', label='Cantilever formula')
  plt.legend(fontsize=12)
  plt.xlabel("Displacement (mm)", fontsize=12)
  plt.ylabel("Force (mN)", fontsize=12)
  plt.xticks(fontsize=12)
  plt.yticks(fontsize=12)
  ax = plt.gca()
  ax.spines[['right', 'top']].set_visible(False)
  plt.savefig('./flexion_curves.svg', dpi=300)
  plt.show()
