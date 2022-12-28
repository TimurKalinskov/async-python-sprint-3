import json

from dataclasses import dataclass, asdict, field
from typing import Literal


@dataclass
class RequestData:
    nick_name: str
    target: Literal['all', 'one_to_one', 'hello'] = 'all'
    receiver: str = ''
    message: str = ''
    delay: int | None = None
    message_life: int = 3600

    def to_json(self):
        return asdict(self)

    def to_string_json(self):
        return json.dumps(self.to_json())
