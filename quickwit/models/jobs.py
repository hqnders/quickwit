"""Contains all models necessary for job events"""
from enum import StrEnum
from typing import TypeVar


# Discord only allows a maximum of 25 options
class FF14Job(StrEnum):
    """FF14 Jobs and some custom jobs"""
    ALL_ROUNDER = 'Allrounder'
    TANK = 'Tank'
    HEALER = 'Healer'
    DPS = 'DPS'
    WAR = 'Warrior'
    PLD = 'Paladin'
    DRK = 'Dark Knight'
    GNB = 'Gunbreaker'
    WHM = 'White Mage'
    SCH = 'Scholar'
    AST = 'Astrologian'
    SGE = 'Sage'
    MNK = 'Monk'
    DRG = 'Dragoon'
    NIN = 'Ninja'
    SAM = 'Samurai'
    VPR = 'Viper'
    RPR = 'Reaper'
    BRD = 'Bard'
    MCH = 'Machinist'
    DNC = 'Dancer'
    BLM = 'Black Mage'
    SMN = 'Summoner'
    RDM = 'Red Mage'
    PCT = 'Pictomancer'
    # BLU = 'Blue Mage'
    # MELEE = 'Melee'
    # RANGED = 'Ranged'
    # CASTER = 'Caster'
    # BARRIER_HEALER = 'Barrier Healer'
    # PURE_HEALER = 'Pure Healer'
    # MAIN_TANK = 'Main Tank'
    # OFF_TANK = 'Off Tank'


class FashionShowJob(StrEnum):
    """Jobs available to fashion shows"""
    CROWD = 'Crowd'
    MODEL = 'Model'
    JUDGE = 'Judge'


class CampfireEventJob(StrEnum):
    """Jobs available to campfire events"""
    CROWD = 'Crowd'
    SPEAKER = 'Speaker'


JobType = TypeVar('JobType', FF14Job, FashionShowJob, CampfireEventJob)
