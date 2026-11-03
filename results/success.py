from dataclasses import dataclass
from results.result import Result
from typing import Generic, TypeVar

T = TypeVar('T')

@dataclass(frozen=True)
class Success(Result, Generic[T]):
  data: T

  @property
  def success(self) -> bool:
    return True