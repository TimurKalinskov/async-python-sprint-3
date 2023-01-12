import json

from dataclasses import dataclass, asdict
from typing import Literal
from enum import Enum


class Command(str, Enum):
    SEND = 'send'
    SEND_TO = 'send-to'
    STATUS = 'status'
    EXIT = 'exit'
    QUIT = 'quit'
    HELP = 'help'

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    def __str__(self):
        return str(self.value)


class Target(str, Enum):
    ALL = 'all'
    ONE_TO_ONE = 'one_to_one'
    HELLO = 'hello'
    STATUS = 'status'

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    def __str__(self):
        return str(self.value)


@dataclass
class RequestData:
    username: str
    target: Literal[
        Target.ALL, Target.ONE_TO_ONE, Target.HELLO, Target.STATUS] = Target.ALL
    receiver: str = ''
    message: str = ''

    def to_json(self):
        return asdict(self)

    def to_string_json(self):
        return json.dumps(self.to_json())
