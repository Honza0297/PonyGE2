def compute_distance(pos1, pos2):
    if len(pos1) != len(pos2):
        raise ValueError("Position vectors have different lenght")
    if len(pos1) != 2:
        raise ValueError("Lenght of the position vectors is not 2")

    return sum([abs(pos1[axis]-pos2[axis]) for axis in range(len(pos1))])


def compute_area(radius):
    area = 0
    if radius == 0:
        area = 1
    else:
        area = compute_area(radius-1)+4*radius
    return area


def choose_direction(start, goal):
    # if diff in rows is bigger than in cols
    axis, delta = 0,0
    if abs(start[0]-goal[0]) > abs(start[1]-goal[1]):
        axis = 0
        delta = -1 if goal[0] - start[0] < 0 else 1
    else:
        axis = 1
        delta = -1 if goal[1] - start[1] < 0 else 1

    return axis, delta
