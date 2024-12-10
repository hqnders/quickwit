"""Contains all types of events with attached jobs"""
from enum import Enum
from dataclasses import dataclass
import quickwit.events.event as event


class JobEvent(event.Event):
    """Reprentation for an event where registrations have jobs"""
    @dataclass
    class Registration(event.Event.Registration):
        """Represents a registration with an attached job"""
        type Job = Enum[tuple[str, str]]
        job: Job = None

    ATTENDEE_FORMAT = "{status} {job} <@{user_id}>\n"

    def _append_registrations(self, message, split_registrations: dict[Registration.Status, dict[int, Registration]]):
        statusses_handled = 0
        for registrations_for_status in split_registrations.values():
            if statusses_handled == 2:
                message += '\n'
            for user_id, registration in registrations_for_status.items():
                status = registration.status.value[1]
                job = registration.job.value[1]

                message += self.ATTENDEE_FORMAT.format(
                    status=status, job=job, user_id=user_id)
            statusses_handled += 1
        return message


class FF14Event(JobEvent):
    """Represents a job event with FF14 jobs"""
    class Registration(JobEvent.Registration):
        """Only difference here is the job"""
        class Job(Enum):
            """Represents FF14 jobs and their Discord emoji"""
            ALL_ROUNDER = ('Allrounder', '<:Allrounder:1302305556966539346>')
            WAR = ('Warrior', '<:Warrior:1302300106103455835>')
            PLD = ('Paladin', '<:Paladin:1302300099103166565>')
            DRK = ('Dark Knight', '<:DarkKnight:1302300076600725616>')
            GNB = ('Gunbreaker', '<:Gunbreaker:1302300089292951593>')
            WHM = ('White Mage', '<:WhiteMage:1302300161271267388>')
            SCH = ('Scholar', '<:Scholar:1302300155097387118>')
            AST = ('Astrologian', '<:Astrologian:1302300139624595486>')
            SGE = ('Sage', '<:Sage:1302300147753160714>')
            MNK = ('Monk', '<:Monk:1302300274488246322>')
            DRG = ('Dragoon', '<:Dragoon:1302300259631894568>')
            NIN = ('Ninja', '<:Ninja:1302300281907970049>')
            SAM = ('Samurai', '<:Samurai:1302300299729305652>')
            VPR = ('Viper', '<:Viper:1302303987671765114>')
            RPR = ('Reaper', '<:Reaper:1302300288585044139>')
            BRD = ('Bard', '<:Bard:1302300185543708733>')
            MCH = ('Machinist', '<:Machinist:1302300267680890981>')
            DNC = ('Dancer',  '<:Dancer:1302300251679494235>',)
            BLM = ('Black Mage', '<:BlackMage:1302300194045694023>')
            SMN = ('Summoner', '<:Summoner:1302300220490776656>')
            RDM = ('Red Mage', '<:RedMage:1302300210923569183>')
            PCT = ('Pictomancer', '<:Pictomancer:1302304017107652782>')
            BLU = ('Blue Mage', '<:BlueMage:1302300345069994004>')
    REPRESENTATION = ('Final Fantasy XIV', '<:FF14:1302571147258236949>')


class FashionShow(JobEvent):
    """Represents a job event with fashion show jobs"""
    class Registration(JobEvent.Registration):
        """Only difference here is the job"""
        class Job(Enum):
            """Represents fashion show jobs and their Discord emoji"""
            CROWD = ('Crowd', '<:Crowd:1303499075865415731>')
            MODEL = ('Model', '<:Model:1303499055434960937>')
            JUDGE = ('Judge', '<:Judge:1303499086363758732>')
    REPRESENTATION = ('Fashion Show', '<:FashionShow:1303500090710687785>')


class CampfireEvent(JobEvent):
    """Represents a job event with campfire event jobs"""
    class Registration(JobEvent.Registration):
        """Only difference here is the job"""
        class Job(Enum):
            """Represents campfire event jobs and their Discord emoji"""
            CROWD = ('Crowd', '<:Crowd:1303499075865415731>')
            SPEAKER = ('Speaker', '<:Speaker:1303499095217930250>')
    REPRESENTATION = ('Campfire Event', '<:Campfire:1303500098306572388>')
