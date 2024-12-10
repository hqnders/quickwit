"""Contains all necessary classes for representing an event"""
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

START_EMOJI = '<:Start:1302339755224338432>'
ORGANISER_EMOJI = '<:Organiser:1302339823813787778>'
PEOPLE_EMOJI = '<:People:1302339799436234802>'
DURATION_EMOJI = '<:Duration:1303485160934604872>'
DEFAULT_DURATION_MINUTES = 60


class Event:
    """Represents an event and it's associated message in Discord"""
    @dataclass
    class Registration:
        """Represents an event registration"""
        class Status(Enum):
            """Represents an attendance status and corresponding emoji"""
            ATTENDING = ('Attending', '<:Attending:1302340634933334137>')
            BENCH = ('Bench', '<:Bench:1302339692355784845>')
            TENTATIVE = ('Tentative', '<:Tentative:1302339734802272267>')
            LATE = ('Late', '<:Late:1302339715063877793>')
        status: Status = None

    REPRESENTATION = ('Event', '<:Event:1302570929024536626>')
    HEADER_FORMAT = '# {emoji} {name}'
    EVENT_INFO_FORMAT = '<@&1199389339281539183>\n' + START_EMOJI + ' <t:{start}:F>\n' \
        + ORGANISER_EMOJI + ' <@{organiser}>'
    DURATION_FORMAT = DURATION_EMOJI + ' {duration} minutes'
    EVENT_FORMAT = '\n\n{description}\n\n' + PEOPLE_EMOJI + \
        ' {sure_attendees} - {potential_attendees} Attendees:\n'
    ATTENDEE_FORMAT = "{status} <@{user_id}>\n"

    def __init__(self, name: str, description: str, start: datetime, organiser_id: int, duration: int = DEFAULT_DURATION_MINUTES):
        self.name = name
        self.description = description
        self.start = start
        self.duration = duration
        self.organiser_id = organiser_id
        self.registrations = {}  # type:  dict[int, Event.Registration]

    def header_message(self) -> str:
        """Generates a Discord message representing the event header

        Returns:
            str: The message representing the event header
        """
        emoji = self.REPRESENTATION[1]
        return self.HEADER_FORMAT.format(name=self.name, emoji=emoji)

    def message(self) -> str:
        """Generates a Discord message representing the event

        Returns:
            str: The message representing the event, with registrations appended
        """
        split_registrations = self._split_registrations_by_status()
        _guaranteed_attendees = len(split_registrations[Event.Registration.Status.ATTENDING]) + len(
            split_registrations[Event.Registration.Status.BENCH])
        _maximum_attendees = _guaranteed_attendees + \
            len(split_registrations[Event.Registration.Status.TENTATIVE]
                ) + len(split_registrations[Event.Registration.Status.LATE])
        start = int(self.start.timestamp())
        message = self.EVENT_INFO_FORMAT.format(
            start=start, organiser=self.organiser_id)
        if (self.duration != DEFAULT_DURATION_MINUTES):
            message += '\t' + \
                self.DURATION_FORMAT.format(duration=self.duration)
        message += self.EVENT_FORMAT.format(description=self.description,
                                            sure_attendees=_guaranteed_attendees, potential_attendees=_maximum_attendees)
        message = self._append_registrations(message, split_registrations)
        return message

    def _split_registrations_by_status(self) -> dict[Registration.Status, dict[int, Registration]]:
        split_registrations = {}  # type: dict[Event.Registration.Status, dict[int, Event.Registration]] # noqa
        for status in Event.Registration.Status:
            split_registrations[status] = {}
        for user_id, registration in self.registrations.items():
            split_registrations[registration.status][user_id] = registration
        return split_registrations

    def _append_registrations(self, message: str, split_registrations: dict[Registration.Status, dict[int, Registration]]) -> str:
        statusses_handled = 0
        for status in split_registrations:
            if statusses_handled == 2:
                # Extra newline to split sure and possible attendees
                message += '\n'
            for user_id, registration in split_registrations[status].items():
                message += self.ATTENDEE_FORMAT.format(
                    status=registration.status.value[1], user_id=user_id)
            statusses_handled += 1
        return message
