from math import degrees, asin, sqrt

from src.swarm.types import Direction


def compute_distance(pos1, pos2):
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


def compute_heading(pos_start, pos_goal):
    """
                quadrants:
                II  | I
                III | IV
                """
    quadrant = - 1
    delta_x = pos_goal[0] - pos_start[0]
    delta_y = pos_goal[1] - pos_start[1]

    if delta_x > 0 and delta_y > 0:
        quadrant = 1
    elif delta_x < 0 < delta_y:
        quadrant = 2
    elif delta_x < 0 and delta_y < 0:
        quadrant = 3
    elif delta_x > 0 > delta_y:
        quadrant = 4

    delta_x = abs(delta_x)
    delta_y = abs(delta_y)

    angle = degrees(asin(delta_y / sqrt(delta_x ** 2 + delta_y ** 2)))
    for i in range(quadrant - 1):
        angle += 90

    angle = angle % 360
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



    return heading
