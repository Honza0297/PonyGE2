
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


class NeighbourhoodResp(Packet):
    def __init__(self, agent_name, nh):
        super(NeighbourhoodResp, self).__init__(agent_name)
        self.neighbourhood = nh


class PickUpReq(Packet):
    def __init__(self, agent_name, position):
        super(PickUpReq, self).__init__(agent_name)
        self.position = position


class DropReq(Packet):
    def __init__(self, agent_name, item_type, position):
        super(DropReq, self).__init__(agent_name)
        self.item_type = item_type
        self.position = position


class PickUpResp(Packet):
    def __init__(self, agent_name, obj):
        super(PickUpResp, self).__init__(agent_name)
        self.pickedObj = obj


class DropResp(Packet):
    def __init__(self, agent_name, dropped):
        super(DropResp, self).__init__(agent_name)
        self.dropped = dropped
