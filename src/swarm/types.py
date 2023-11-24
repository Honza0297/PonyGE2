import enum


class ObjectType(enum.Enum):
    AGENT = "A"
    OBJECT = "O"
    FOOD = "F"
    HUB = "H"
    GENERIC = OBJECT
    NOTYPE = "X"

    @staticmethod
    def str2enum(item):
        item = item.lower()
        retval: ObjectType
        match item:
            case "food":
                retval = ObjectType.FOOD
            case "hub" | "base":
                retval = ObjectType.HUB
            case "agent":
                retval = ObjectType.AGENT
            case "generic":
                retval = ObjectType.GENERIC
            case _:
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
    def broad_direction(direction):
        ret = ()
        match direction:
            case Direction.UP:
                ret = (Direction.UP, Direction.LEFT, Direction.RIGHT)
            case Direction.DOWN:
                ret = (Direction.DOWN, Direction.LEFT, Direction.RIGHT)
            case Direction.LEFT:
                ret = (Direction.UP, Direction.DOWN, Direction.LEFT)
            case Direction.RIGHT:
                ret = (Direction.UP, Direction.DOWN, Direction.RIGHT)
        return ret

    @staticmethod
    def reverse(direction):
        ret = direction
        match direction:
            case Direction.UP:
                ret = Direction.DOWN
            case Direction.DOWN:
                ret = Direction.UP
            case Direction.RIGHT:
                ret = Direction.LEFT
            case Direction.LEFT:
                ret = Direction.RIGHT
        return ret


class BlackboardKeys(enum.Enum):
    NEAR_OBJECT = "nearObject"
