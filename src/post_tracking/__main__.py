# coding: utf-8

"""File executed when calling the code as a module.

Simply launches the user interface, and waits for the user to exit.
"""

from PyQt6.QtWidgets import QApplication
import sys

from . import MainWindow

if __name__ == "__main__":

  app = QApplication(sys.argv)

  window = MainWindow()
  window.show()

  sys.exit(app.exec())
