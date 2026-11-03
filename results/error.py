from dataclasses import dataclass
from results.result import Result
from typing import Generic, TypeVar

T = TypeVar('T')

@dataclass(frozen=True)
class Error(Result):
  error_msg: str

  @property
  def success(self) -> bool:
    return False