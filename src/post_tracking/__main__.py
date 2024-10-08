# coding: utf-8

from PyQt6.QtWidgets import QApplication
import sys

from . import MainWindow

if __name__ == "__main__":

  app = QApplication(sys.argv)

  window = MainWindow()
  window.show()

  sys.exit(app.exec())
