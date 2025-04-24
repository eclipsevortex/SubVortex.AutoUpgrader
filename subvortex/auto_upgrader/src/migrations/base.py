from abc import ABC, abstractmethod

class Migration(ABC):
    def __init__(self, service):
        self.service = service

    @abstractmethod
    def apply(self):
        pass

    @abstractmethod
    def rollback(self):
        pass