from enum import Enum

class UserTier(str, Enum):
    standard = "standard"
    silver = "silver"
    gold = "gold"
    platinum = "platinum"
