from src.swarm.types import ObjectType
#from src.swarm.models import TileModel, BoardModel
from src.swarm.math import compute_distance, compute_area
from PyQt5 import QtCore


class EnvironmentObject:
    def __init__(self, name, object_type, radius):
        self.name = name
        self.type = object_type

        self.position = [None, None]
        self.placed = False
        self.tiles = list()
        self.radius = radius

        self.color = QtCore.Qt.black
        self.image = None

    def set_place(self, position, board_model):
        self.placed = True
        self.position = list()
        for row in board_model.tiles:
            for tile in row:
                dist = compute_distance(position, tile.position)
                if dist <= self.radius:
                    self.tiles.append(tile)
                    self.position.append(tile.position)

    def remove_part(self, position):
        removed = False
        for tile in self.tiles:
            if tile.position == position:
                self.tiles.remove(tile)
                self.position.remove(tile.position)
                tile.remove_object(self)
                removed = True
        if not self.tiles:
            self.placed = False

        return removed

    def remove_all(self):
        for tile in self.tiles:
            self.tiles.remove(tile)
            tile.remove_object(self)
        self.placed = False


class FoodSource(EnvironmentObject):
    def __init__(self, name, object_type=ObjectType.FOOD, radius=1, food_limit=0):
        super(FoodSource, self).__init__(name, object_type, radius)
        self.color = QtCore.Qt.green

        if food_limit == 0:
            self.food_limit = compute_area(self.radius)
        else:
            self.food_limit = food_limit

    def remove_part(self, position):
        super(FoodSource, self).remove_part(position)
        self.food_limit -= 1


class Hub(EnvironmentObject):
    def __init__(self, name, object_type, radius):
        super(Hub, self).__init__(name, object_type, radius)
        self.color = QtCore.Qt.darkRed

