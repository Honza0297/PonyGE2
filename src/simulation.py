import logging
import sys

from PyQt5.QtWidgets import QApplication

from src.swarm.backend import TestBackend
from src.swarm.gui import SimulationWindow
from src.swarm.agent import DummyAgent

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    app = QApplication(sys.argv)

    gui = SimulationWindow(10)
    backend_thread = TestBackend(gui)
    agents = list()
    for i in range(10):
        agents.append(DummyAgent("agent"+str(i)))
        backend_thread.register_agent(agents[-1])
    print(type(agents[0]))
    #TODO create and register agents as threads?
    backend_thread.start()
    #for agent in agents:
    #    agent.start()

    

    # r_agent = ReactiveAgentSensitive(runtime, position=[3, 3], sense_radius=2, name="ag1")
    # r_agent_sens = ReactiveAgent(runtime, position=[5, 5], sense_radius=2, name="ag2")

    # p_agent = ProactiveAgent(runtime, [5,5], sense_radius=2, name="ag3")
    # runtime.register_agent(r_agent)


    #GUI



    sys.exit(app.exec())
