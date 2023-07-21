from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QSize
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class BoardModel():
    def __init__(self, dimension):
        self.board = [[TileModel for d in range(dimension)] for dd in range(dimension)]


class TileModel():
    def __init__(self):
        self.occupancy = False
        self.object = None
        self.type = "generic"
        self.props = {}



"""
Class representing Board on the screen
"""
class QBoard(QWidget):
    def __init__(self, parent=None, dimension=8):
        super().__init__(parent=parent)

        self.dimension = dimension

        """
        Init grid of tiles
        """
        grid = QGridLayout()
        tiles = []
        # create grid of tiles = environment
        for x in range(self.dimension):
            row = list()
            for y in range(self.dimension):
                square = QTile(self, position=(x, y))
                row.append(square)
                square.setFixedSize(800 // self.dimension, 800 // self.dimension)
                grid.addWidget(square, x, y)
                #grid.setSpacing(1)
                grid.setHorizontalSpacing(1)
                grid.setVerticalSpacing(1)
            tiles.append(row)
        # reference to the tiles to be able to modify them
        self.tiles = tiles
        self.setLayout(grid)

class QTile(QWidget):
    def __init__(self, parent, position):
        super().__init__(parent=parent)
        # Tile abilities/perks
        self.color = QtCore.Qt.white
        self.image = None
        self.position = position
        self.hole = False

    def set_image(self, img):
        self.image = img

    def create_hole(self):
        self.hole = True
        self.set_image("img/dira.png")
        self.update()

    def delete_hole(self):
        self.hole = False
        self.update()

    def set_color(self, color):
        self.color = color
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        if self.hole:
            painter = QPainter()
            painter.begin(self)
            pixmap = QPixmap(self.image)
            painter.fillRect(self.rect(), self.color)

            painter.drawPixmap(self.rect(), pixmap)

            painter.end()
        elif self.image:
            painter = QPainter()
            painter.begin(self)
            pixmap = QPixmap(self.image)
            painter.fillRect(self.rect(), self.color)

            painter.drawPixmap(self.rect(), pixmap)

            painter.end()
        else:
            painter = QPainter()
            painter.begin(self)
            painter.fillRect(self.rect(), self.color)
            painter.end()