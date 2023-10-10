from src.swarm import types


class Neighbourhood:
    def __init__(self, neighbourhood=None):
        if neighbourhood is None:
            self.neighbourhood = list() # matrix
            self.valid = False
            self.radius = 0
            self.center = None
            self.size = 0
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
        self.size = len(self.neighbourhood)

    def get(self, obj_type: types.ObjectType):
        cells_with_object = list()
        for row in self.neighbourhood:
            for cell in row:
                if cell:
                    if cell.type == obj_type:
                        cells_with_object.append(cell)

        return len(cells_with_object) > 0, cells_with_object
