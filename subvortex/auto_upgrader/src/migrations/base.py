from abc import ABC, abstractmethod

class Migration(ABC):
    @abstractmethod
    def apply(self):
        pass

    @abstractmethod
    def rollback(self):
        pass