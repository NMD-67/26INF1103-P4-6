from abc import ABC
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

class Result(ABC):

  @property 
  def success(self) -> bool:
    return isinstance(self, Success)

@dataclass(frozen=True)
class Success(Result, Generic[T]):
  data: T

@dataclass(frozen=True)
class Error(Result):
  error_msg: str