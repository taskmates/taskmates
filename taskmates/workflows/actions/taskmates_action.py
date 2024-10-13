from abc import abstractmethod, ABC


class TaskmatesAction(ABC):
    @abstractmethod
    def perform(self, *args, **kwargs):
        pass
