import enum


class ObjectType(enum.Enum):
    AGENT = "A"
    OBJECT = "O"
    FOOD = "F"
    HUB = "H"
    GENERIC = OBJECT
