"""
Generic BoardModel.
"""
from PyQt5 import QtCore
from src.swarm.agent import DummyAgent


class BoardModel:
    def __init__(self, dimension):
        tiles = list()
        for r in range(dimension):
            row = list()
            for c in range(dimension):
                row.append(TileModel((r,c)))
            tiles.append(row)
        self.tiles = tiles
        self.dimension = dimension
        # self.tiles[3][3].image = "img/dira.png"
        # self.tiles[3][3].type = "hole"

        # Static/immovable objects in the environment - hub, obstacles...
        self.objects = dict()

    def get_objects(self, object_name) -> list:
        if object_name in self.objects.keys():
            return self.objects[object_name]
        else:
            return list()


class TileModel:
    def __init__(self, position):
        self.position = position
        self.occupied = False
        self.object = None
        self.image = ""
        self.background = None
        self.type = "generic"
        self.props = {}

    def place_object(self, obj):
        if self.occupied:
            return False
        if type(obj) == DummyAgent:
            self.occupied = True
            self.object = obj
            self.background = QtCore.Qt.black
            return True
        else:
             raise TypeError("Attempted to place unsupported object: {}", obj)

    def remove_object(self, obj):
        if self.object != obj:
            raise TypeError("Object to remove is not the object placed here!")
        self.occupied = False
        self.object = None
        self.background = QtCore.Qt.white
        return True


    def __repr__(self):
        return "Tile at {}, occupied: {}, object: {}".format(self.position, self.occupied, self.object)