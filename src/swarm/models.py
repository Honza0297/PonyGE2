
from PyQt5 import QtCore
from src.swarm.types import ObjectType


class BoardModel:
    """
Generic BoardModel.
"""
    def __init__(self, dimension):
        tiles = list()
        for r in range(dimension):
            row = list()
            for c in range(dimension):
                row.append(TileModel((r, c)))
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
        self.type = ObjectType.GENERIC
        self.props = {}

    def place_object(self, obj):
        succ = False
        if self.occupied:
            succ = False
        self.occupied = True
        self.object = obj # whole object, not a type!
        self.type = obj.type
        self.background = obj.color  # TODO rozlisit mezi tim, kdyzz ma objekt jen color, jen image nebo oboji
        succ = True
        return succ

    def remove_object(self, obj):
        if not self.object:
            return False
        if self.object != obj:
            raise TypeError("Object to remove is not the object placed here!")
        obj = self.object  # backup to be able to call remove_part
        self.object = None
        if not obj.type == ObjectType.AGENT:
            obj.remove_part(self.position)
        self.occupied = False
        self.type = ObjectType.GENERIC
        self.background = QtCore.Qt.white
        return True

    def __repr__(self):
        return f"Tile at {self.position}, occupied: {self.occupied}, object: {self.object}"