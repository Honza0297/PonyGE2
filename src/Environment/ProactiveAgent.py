from Agent import Agent
from Runtime import Runtime
import numpy

class TileModel:
    """
    Tile model represents one tile of the environment
    """
    def __init__(self):
        self.hole = False
        self.agent = False
        self.confidence = 1

class ProactiveAgent(Agent):
    """
    Intelligent agent able to rationally go through the whole map.
    """
    def __init__(self, runtime: Runtime, position, sense_radius=5, name="reactive_agent"):
        super().__init__(runtime, position, name)
        self.image = "proactive_agent.png"
        self.sense_radius = sense_radius
        self.plan = []
        self.model = numpy.ndarray((runtime.dimension, runtime.dimension), dtype=object)  #
        for i_r in range(len(self.model)):
            for i_c in range(len(self.model[0])):
                self.model[i_r][i_c] = TileModel()
        self.set_my_pos_in_model()
        return

    def sense(self):
        sur = self.runtime.get_surrounding(self.position, self.sense_radius)
        return sur

    def step(self):
        sur = self.sense() # Done
        self.update_model(sur)  # Done
        self.check_plan()
        self.perform_action()

    def update_model(self, surrounding):
        for row in self.model:
            for tile in row:
                if not tile.hole:
                    tile.confidence *= (1-self.runtime.hole_chance)

        offset = numpy.array(self.position) - self.sense_radius
        for i_r in range(len(surrounding)):
            for i_c in range(len(surrounding[0])):
                if surrounding[i_r][i_c] == 1:  # Dira
                    self.model[i_r + offset[0]][i_c + offset[1]].hole = True
                    self.model[i_r + offset[0]][i_c + offset[1]].confidence = 1
                if surrounding[i_r][i_c] < 0:  # agent nebo zed - zatím nic
                    continue
                if surrounding[i_r][i_c] == 0:
                    self.model[i_r + offset[0]][i_c + offset[1]].hole = False
                    self.model[i_r + offset[0]][i_c + offset[1]].confidence = 1

    def check_plan(self):
        if self.plan:
            # Make check
            pass
        else: # Chci nový plan
            self.make_plan()

    def make_plan(self):
        # problem obchodniho cestujiciho - nejkratsi cesta mezi vsemi dlazdicemi
        pass

    def perform_action(self):
        pass

    def move(self, dir):
        self.runtime.move_notif(self,self.position, dir)
        self.update_pos(dir)

    def update_pos(self, direction):
        self.reset_my_pos_in_model()
        super(ProactiveAgent, self).update_pos(direction)
        self.set_my_pos_in_model()

    def reset_my_pos_in_model(self):
        self.model[self.position[0]][self.position[1]].agent = False
        self.model[self.position[0]][self.position[1]].hole = False
        self.model[self.position[0]][self.position[1]].confidence = 1

    def set_my_pos_in_model(self):
        self.model[self.position[0]][self.position[1]].agent = True
        self.model[self.position[0]][self.position[1]].hole = False
        self.model[self.position[0]][self.position[1]].confidence = 1
