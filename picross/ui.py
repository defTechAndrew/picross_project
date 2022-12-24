"""Picross board UI implemented with QT"""

import sys
from PySide6 import QtCore, QtWidgets, QtGui
import picross.core as core


class GameWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(GameWindow, self).__init__(parent=parent)

        self.setWindowTitle('Picross')

        file_menu = QtWidgets.QMenu('File')
        self.menuBar().addMenu(file_menu)
        file_menu.addAction('New Game', self.new_game)

        self.board_widget = BoardWidget(board=core.Board(), parent=self)
        self.setCentralWidget(self.board_widget)

    def new_game(self):

        self.board_widget.close()
        self.board_widget = BoardWidget(board=core.Board(), parent=self)
        self.setCentralWidget(self.board_widget)


class BoardWidget(QtWidgets.QWidget):

    def __init__(self, board, parent=None):
        super(BoardWidget, self).__init__(parent=parent)

        self.board = board
        self.setLayout(QtWidgets.QGridLayout())
        self.layout().setSpacing(0)

        grid_index = [1, 1]
        for row in self.board:
            for _ in row:
                print(grid_index)
                cell = Cell()
                self.layout().addWidget(cell, *grid_index)
                grid_index[0] += 1
            grid_index[0] = 1
            grid_index[1] += 1


class Cell(QtWidgets.QWidget):
    SIZE = 32

    def __init__(self, parent=None):
        super(Cell, self).__init__(parent=parent)

        self.setFixedSize(self.SIZE, self.SIZE)
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor('light grey'))
        self.setPalette(palette)
        self.setAutoFillBackground(True)


if __name__ == "picross.ui":
    app = QtWidgets.QApplication([])

    widget = GameWindow()
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())
