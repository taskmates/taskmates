from abc import ABC, abstractmethod
import argparse

class Command(ABC):
    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser):
        pass

    @abstractmethod
    async def execute(self, args: argparse.Namespace):
        pass
