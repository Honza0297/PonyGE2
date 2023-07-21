
class Packet:
    def __init__(self, agent_name):
        self.agent_name = agent_name


class Sense(Packet):
    def __init__(self, agent_name):
        super(Sense, self).__init__(agent_name)


class Move(Packet):
    def __init__(self, agent_name, position):
        super(Move, self).__init__(agent_name)
        self.position = position


class Position(Packet):
    def __init__(self, agent_name, position):
        super(Position, self).__init__(agent_name)
        self.position = position

class Neighbourhood(Packet):
    def __init__(self, agent_name, nh):
        super(Neighbourhood, self).__init__(agent_name)
        self.neighbourhood = nh
