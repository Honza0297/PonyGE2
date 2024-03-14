import enum
from typing import List, Tuple, Union

class ObjectType(enum.Enum):
    AGENT = "A"
    OBJECT = "="
    FOOD = "F"
    HUB = "H"
    GENERIC = OBJECT
    NOTYPE = "X"

    @staticmethod
    def str2enum(item: str) -> 'ObjectType':
        item = item.lower()
        retval: ObjectType
        if item == "food":
            retval = ObjectType.FOOD
        elif item == "hub" or item == "base":
            retval = ObjectType.HUB
        elif item == "agent":
            retval = ObjectType.AGENT
        elif item == "generic":
            retval = ObjectType.GENERIC
        else:
            retval = ObjectType.NOTYPE

        return retval

    @staticmethod
    def enum2str(self, item, capitality="First"):
        raise NotImplemented()


class Direction(enum.Enum):
    UP = "U"
    DOWN = "D"
    LEFT = "L"
    RIGHT = "R"

    @staticmethod
    def broad_direction(direction: 'Direction') -> List['Direction']:
        if isinstance(direction, list):
            if len(direction) > 1:
                raise ValueError("Broad heading was used in place of normal heading")
            else:
                direction = direction[0]
        ret = ()
        if direction == Direction.UP:
            ret = (Direction.UP, Direction.LEFT, Direction.RIGHT)
        elif direction == Direction.DOWN:
            ret = (Direction.DOWN, Direction.LEFT, Direction.RIGHT)
        elif direction == Direction.LEFT:
            ret = (Direction.UP, Direction.DOWN, Direction.LEFT)
        elif direction == Direction.RIGHT:
            ret = (Direction.UP, Direction.DOWN, Direction.RIGHT)
        return list(ret)

    @staticmethod
    def reverse(direction: 'Direction') -> 'Direction':
        if isinstance(direction, list):
            if len(direction) > 1:
                raise ValueError("Broad heading was used in place of normal heading")
            else:
                direction = direction[0]
        ret = direction
        if direction == Direction.UP:
            ret = Direction.DOWN
        elif direction == Direction.DOWN:
            ret = Direction.UP
        elif direction == Direction.RIGHT:
            ret = Direction.LEFT
        elif direction == Direction.LEFT:
            ret = Direction.RIGHT
        return ret
    