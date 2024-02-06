import random
from math import degrees, asin, sqrt

from src.swarm.types import Direction


def compute_distance(pos1, pos2):
    """
    Computes distance as a number of steps needed to travel between the two positions in a 4-neighbourhood grid.
    """
    if len(pos1) != len(pos2):
        raise ValueError("Position vectors have different lenght")
    if len(pos1) != 2:
        raise ValueError("Lenght of the position vectors is not 2")

    return sum([abs(pos1[axis] - pos2[axis]) for axis in range(len(pos1))])


def compute_area(radius):
    area = 0
    if radius == 0:
        area = 1
    else:
        area = compute_area(radius - 1) + 4 * radius
    return area


def choose_direction(start, goal):
    # if diff in rows is bigger than in cols
    axis, delta = 0, 0
    if abs(start[0] - goal[0]) > abs(start[1] - goal[1]):
        axis = 0
        delta = -1 if goal[0] - start[0] < 0 else 1
    else:
        axis = 1
        delta = -1 if goal[1] - start[1] < 0 else 1

    return axis, delta


def angle_from_deltas(dx, dy):
    bias = None
    if dy == 0 or dx == 0:
        if dx == 0 and dy == 0:
            raise Exception("Agent already arrived to the goal")
        elif dx == 0 and dy < 0:
            angle = 90
        elif dx == 0 and dy > 0:
            angle = 270
        elif dx < 0 and dy == 0:
            angle = 180
        elif dx > 0 and dy == 0:
            angle = 0
    else:
        bias = 0
        if dx > 0 and dy > 0:
            bias = 270
        elif dx < 0 < dy:
            bias = 180
        elif dx < 0 and dy < 0:
            bias = 90
        elif dy < 0 < dx:
            bias = 0

        angle = degrees(asin(abs(dy) / sqrt(abs(dx) ** 2 + abs(dy) ** 2)))

        if (dx < 0 and dy < 0) or (dx > 0 and dy > 0):
            angle = 90-angle

        angle += bias
    return angle


def compute_heading(pos_start, pos_goal, towards=True):
    """
                quadrants:
                II  | I
                III | IV

                !!!
                rows ~ y
                cols ~ x
                !!!
                """
    # NOTE rows are "y values" and cols are "x values":
    #    c1 c2 c3 ...            ____________ x values
    # r1                        |
    # r2                 ->     |                         (and y axis "grows" to down)
    # r3                        |
    # ...                       |
    #                         y values

    dy = pos_goal[0] - pos_start[0]
    dx = pos_goal[1] - pos_start[1]
    angle = angle_from_deltas(dx, dy)

    heading = Direction.UP
    """
    Directions: 
    45-134: UP
    135-224: LEFT
    225-314: DOWN
    314-404*: RIGHT
    404%360 = 44
    """
    if 45 <= angle <= 134:
        heading = Direction.UP
    elif 135 <= angle <= 224:
        heading = Direction.LEFT
    elif 225 <= angle <= 314:
        heading = Direction.DOWN
    elif angle >= 315 or angle <= 44:
        heading = Direction.RIGHT

    if not towards:  # AKA if away
        heading = Direction.broad_direction(Direction.reverse(heading))

    return heading


def pos_from_heading(pos, heading):
    ret = list(pos)
    match heading:
        case Direction.UP:
            ret[0] -= 1
        case Direction.DOWN:
            ret[0] += 1
        case Direction.RIGHT:
            ret[1] += 1
        case Direction.LEFT:
            ret[1] -= 1
    return ret
