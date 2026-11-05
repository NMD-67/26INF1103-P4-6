from dataclasses import dataclass

@dataclass
class DealBreaker:
  min_age: int | None
  max_age: int | None
  religion: str | None
  race: str | None
  gender: str | None