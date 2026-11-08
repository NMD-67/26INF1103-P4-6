from dataclasses import dataclass, field


@dataclass
class DealBreaker:
    min_age: int | None = None
    max_age: int | None = None
    religion: list[str] = field(default_factory=list)
    race: list[str] = field(default_factory=list)
    gender: str | None = None

    def to_row(self) -> dict:
        return {
            "min_age": self.min_age,
            "max_age": self.max_age,
            "religion": self.religion,
            "gender": self.gender,
            "race": self.race,
        }
