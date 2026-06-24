import enum


class SpotType(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    SHARED = "SHARED"


class Shift(str, enum.Enum):
    FULL_DAY = "FULL_DAY"
    DAY = "DAY"
    NIGHT = "NIGHT"  # 18:00–00:00


class ReleaseType(str, enum.Enum):
    POOL = "POOL"
    TRANSFER = "TRANSFER"
