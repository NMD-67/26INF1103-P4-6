from abc import ABC, abstractmethod

class Result(ABC):

  @property 
  @abstractmethod
  def success(self) -> bool:
    pass
  
  