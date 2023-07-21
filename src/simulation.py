import logging
import sys
import time

from PyQt5.QtCore import QSize, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from Environment.Runtime import Runtime
from Environment.Board import QBoard
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
import threading


class Backend(threading.Thread):
    def __init__(self, gui):
        super(Backend, self).__init__()
        self.gui = gui
        #TODO http

    def run(self):
        for i in range(5):
            self.gui.draw_hole((i, i))
            time.sleep(1)


class SimulationWindow(QMainWindow):

    signal_add_hole = pyqtSignal(tuple)

    def __init__(self, runtime, board):
        super().__init__()
        self.setStyleSheet("background-color: darkGray;")
        self.setWindowTitle('Simulation')
        layout = QHBoxLayout()
        layout.addWidget(board)
        layout.addWidget(self.prepare_controls(runtime))
        mainWidget = QWidget()
        mainWidget.setLayout(layout)
        self.setCentralWidget(mainWidget)

        self.runtime = runtime
        self.board = board

        self.signal_add_hole.connect(self._draw_hole)
        self.draw_hole =self.signal_add_hole.emit
        self.show()

    def _draw_hole(self, pos):
        self.board.tiles[pos[0]][pos[1]].create_hole()
        self.update()

    def prepare_controls(self, runtime):
        control_panel = QWidget()
        stepping_layout = QGridLayout()

        # todo sem házet ovládací prvky

        step_butt = QPushButton("Step")

        def step():
            runtime.step()

        step_butt.clicked.connect(step)
        step_butt.setMaximumWidth(200)

        run_butt = QPushButton("Run")
        timer = QTimer()
        timer.timeout.connect(runtime.step)

        def run():
            timer.start(int(period.text()))
            stop_butt.setEnabled(True)
            run_butt.setEnabled(False)
            step_butt.setEnabled(False)

        run_butt.clicked.connect(run)
        run_butt.setMaximumWidth(200)

        period = QLineEdit("1000")
        period.setMaximumWidth(200)

        stop_butt = QPushButton("Stop")

        def stop():
            timer.stop()
            stop_butt.setEnabled(False)
            run_butt.setEnabled(True)
            step_butt.setEnabled(True)

        stop_butt.clicked.connect(stop)
        stop_butt.setEnabled(False)
        stop_butt.setMaximumWidth(200)

        stepping_layout.addWidget(step_butt, 0, 0)
        stepping_layout.addWidget(period, 1, 1)
        stepping_layout.addWidget(run_butt, 1, 0)
        stepping_layout.addWidget(stop_butt, 2, 0)

        end_butt = QPushButton("Save simulation data")

        def end():
            runtime.dl.print()
            runtime.dl.save_to_file("test")

        end_butt.clicked.connect(end)
        end_butt.setMaximumWidth(200)

        cpl = QVBoxLayout()
        cpl.addLayout(stepping_layout)
        cpl.addWidget(end_butt)
        control_panel.setLayout(cpl)
        return control_panel



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    app = QApplication(sys.argv)

    # Simulation
    board = QBoard(dimension=10)
    runtime = Runtime(board, app,  [])

    gui = SimulationWindow(runtime, board)
    backend_thread = Backend(gui)

    backend_thread.start()
    

    # r_agent = ReactiveAgentSensitive(runtime, position=[3, 3], sense_radius=2, name="ag1")
    # r_agent_sens = ReactiveAgent(runtime, position=[5, 5], sense_radius=2, name="ag2")

    # p_agent = ProactiveAgent(runtime, [5,5], sense_radius=2, name="ag3")
    # runtime.register_agent(r_agent)


    #GUI



    sys.exit(app.exec())
