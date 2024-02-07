import sys

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from src.swarm.models import BoardModel


class QBoard(QWidget):
    """
    Class representing Board on the screen
    """
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
        self.hole = False
        self.position = position
        self.mouseReleaseEvent = self.print_info
        self.tile_model = None

    def print_info(self, event):
        print(self.tile_model) # TODO

    def set_image(self, img, img_type):
        self.image = img
        if img_type == "hole":
            self.hole = True
        else:
            self.hole = False

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


class SimulationWindow(QMainWindow):

    signal_add_hole = pyqtSignal(tuple)
    signal_step = pyqtSignal()
    signal_run = pyqtSignal()
    signal_stop = pyqtSignal()
    signal_end = pyqtSignal()

    signal_update = pyqtSignal(BoardModel)

    def __init__(self, dimension):
        super().__init__()
        self.board = None
        self.setStyleSheet("background-color: darkGray;")
        self.setWindowTitle('Simulation')

        self.layout = QHBoxLayout()
        self.board = QBoard(dimension=dimension)
        #self.reset_board(dimension)
        self.layout.addWidget(self.board)
        self.layout.addWidget(self.prepare_controls())
        mainWidget = QWidget()
        mainWidget.setLayout(self.layout)
        self.setCentralWidget(mainWidget)
        self.dimension = dimension
        #signals from GUI
        #signals to GUI
        self.signal_update.connect(self._update)
        self.update = self.signal_update.emit

        #self.signal_add_hole.connect(self._draw_hole)

        #self.draw_hole =self.signal_add_hole.emit
        self.show()

    def register_backend(self, backend):
        self.backend = backend
        for r in range(len(self.backend.board_model.tiles)):
            for c in range(len(self.backend.board_model.tiles)):
                self.board.tiles[r][c].tile_model = self.backend.board_model.tiles[r][c]

    def reset_board(self, dimension):
        for r in range(dimension):
            for c in range(dimension):
                self.board.tiles[r][c].set_color(QtCore.Qt.white)


    def _update(self, board_model):
        for r in range(self.dimension):
            for c in range(self.dimension):
                tile_model = board_model.tiles[r][c]
                if tile_model.image:
                    self.board.tiles[r][c].set_image(tile_model.image, tile_model.type)
                if tile_model.background:
                    self.board.tiles[r][c].set_color(tile_model.background)
    pass
                # TODO here update all the GUI-related thingies for tiles - primarily their color/background and images

    def prepare_controls(self):
        control_panel = QWidget()
        stepping_layout = QGridLayout()

        # todo sem házet ovládací prvky

        step_butt = QPushButton("Step")
        run_butt = QPushButton("Run")

        """step link between backend and frontend"""
        def step():
            self.signal_step.emit()
            self.backend.stop = False
            self.backend.step = True
            #runtime.step()

        step_butt.clicked.connect(step)
        step_butt.setMaximumWidth(200)

        def run():
            #timer.start(int(period.text()))
            stop_butt.setEnabled(True)
            run_butt.setEnabled(False)
            step_butt.setEnabled(False)
            self.backend.stop = False
            self.backend.step = False
            self.signal_run.emit()



        run_butt.clicked.connect(run)
        run_butt.setMaximumWidth(200)

        stop_butt = QPushButton("Stop")

        def stop():
            stop_butt.setEnabled(False)
            run_butt.setEnabled(True)
            step_butt.setEnabled(True)
            self.backend.stop = True
            self.backend.step = False
            self.signal_stop.emit()

        stop_butt.clicked.connect(stop)
        stop_butt.setEnabled(False)
        stop_butt.setMaximumWidth(200)

        end_butt = QPushButton("End simulation")
        def end():
            self.backend.end = True
            self.signal_end.emit()
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Info")
            dlg.setText("Simulation ended, please close the window.")
            dlg.exec()

        end_butt.clicked.connect(end)
        end_butt.setEnabled(True)
        end_butt.setMaximumWidth(200)

        restart_butt = QPushButton("End current and restart")

        def restart():
            self.backend.restart = True


        restart_butt.clicked.connect(restart)
        restart_butt.setEnabled(True)
        restart_butt.setMaximumWidth(200)



        stepping_layout.addWidget(step_butt, 0, 0)
        stepping_layout.addWidget(run_butt, 1, 0)
        stepping_layout.addWidget(stop_butt, 2, 0)
        stepping_layout.addWidget(end_butt, 3, 0)
        stepping_layout.addWidget(restart_butt, 4,0)

        cpl = QVBoxLayout()
        cpl.addLayout(stepping_layout)
        control_panel.setLayout(cpl)
        return control_panel


