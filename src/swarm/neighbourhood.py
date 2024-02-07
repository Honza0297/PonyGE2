from src.swarm.types import Direction, ObjectType
from src.swarm.math import  compute_distance

class Neighbourhood:
    def __init__(self, neighbourhood=None):
        if neighbourhood is None:
            self.neighbourhood = list()  # matrix
            self.valid = False
            self.radius = 0
            self.center = None
            self.center_abs_coordinates = None
            self.size = 0
            self.objects = dict()
        else:
            self.set_neighbourhood(neighbourhood)

    def __str__(self):
        s = "  "
        for i in range(len(self.neighbourhood)):
            s += str(i) + (" " if i < 10 else "")
        s += "\n"
        cnt_r = 0
        for r in self.neighbourhood:
            s += str(cnt_r) + (" " if cnt_r < 10 else "")
            cnt_r += 1
            for tile in r:
                if not tile:
                    s += "X" + " "
                else:
                    s += str(tile.type.value) + " "
            s += "\n"
        return s

    def set_neighbourhood(self, neighbourhood):
        self.neighbourhood = neighbourhood
        self.valid = True
        self.radius = len(self.neighbourhood) // 2
        self.center = (self.radius, self.radius)
        self.center_abs_coordinates = self.neighbourhood[self.center[0]][self.center[1]].position
        self.size = len(self.neighbourhood)
        self.objects = {t: [] for t in (ObjectType.AGENT, ObjectType.HUB, ObjectType.FOOD)}

        for row in self.neighbourhood:
            for cell in row:
                if cell and cell.occupied:
                    distance = compute_distance(self.center_abs_coordinates, cell.position)
                    if not self.objects[cell.type]:
                        self.objects[cell.type] = [(cell, distance)]
                    else:
                        self.objects[cell.type].append((cell, distance))


    def get(self, obj_type: ObjectType):
        cells_with_object = list()
        for row in self.neighbourhood:
            for cell in row:
                if cell and cell.occupied:
                    if cell.object.type == obj_type:
                        cells_with_object.append(cell)

        return len(cells_with_object) > 0, cells_with_object

    def get_relative_pos(self, abs_pos):
        offset_r = self.neighbourhood[self.center[0]][self.center[1]].position[0] - self.center[0]
        offset_c = self.neighbourhood[self.center[0]][self.center[1]].position[1] - self.center[1]

        return abs_pos[0] - offset_r, abs_pos[1] - offset_c

    def get_objects(self, object_type: ObjectType, max_distance=None):
        """
        Returns list of objects of given type that are no farther than max_distance,
        """
        if not max_distance:
            max_distance = self.size
        return [obj for obj in self.objects[object_type] if obj[1] <= max_distance]

    def get_next_tile_in_dir(self, curr_pos, direction):
        next_tile = None
        match direction:
            case Direction.UP:
                if curr_pos[0] == 0:  # top row, cannot go up
                    next_tile = None
                else:
                    next_tile = self.neighbourhood[curr_pos[0] - 1][curr_pos[1]]  # set init tile
            case Direction.DOWN:
                if curr_pos[0] == len(self.neighbourhood):  # bottom row, cannot go down
                    next_tile = None
                else:
                    next_tile = self.neighbourhood[curr_pos[0] + 1][curr_pos[1]]  # set init tile
            case Direction.LEFT:
                if curr_pos[1] == 0:  # leftmost col, cannot go left
                    next_tile = None
                else:
                    next_tile = self.neighbourhood[curr_pos[0]][curr_pos[1] - 1]  # set init tile
            case Direction.RIGHT:
                if curr_pos[1] == len(self.neighbourhood):  # rightmost row, cannot go right
                    next_tile = None
                else:
                    next_tile = self.neighbourhood[curr_pos[0]][curr_pos[1] + 1]  # set init tile

        return next_tile
