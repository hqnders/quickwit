from enum import StrEnum
from typing import TypeVar


class FF14Job(StrEnum):
    ALL_ROUNDER = 'Allrounder'
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
    DNC = 'Dancer',
    BLM = 'Black Mage'
    SMN = 'Summoner'
    RDM = 'Red Mage'
    PCT = 'Pictomancer'
    BLU = 'Blue Mage'


class FashionShowJob(StrEnum):
    CROWD = 'Crowd'
    MODEL = 'Model'
    JUDGE = 'Judge'


class CampfireEventJob(StrEnum):
    CROWD = 'Crowd'
    SPEAKER = 'Speaker'


JobType = TypeVar('JobType', FF14Job, FashionShowJob, CampfireEventJob)
