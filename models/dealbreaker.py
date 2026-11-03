from dataclasses import dataclass

@dataclass
class DealBreaker:
  name: str
  value: str | list[str]