from typing import Literal

from pydantic import BaseModel


class Weather(BaseModel):
    cache: dict = {}

    def unrelated_method(self):
        pass

    def get_weather(self, location: str, unit: Literal["celsius", "fahrenheit"] = "celsius") -> str:
        """
        Get the current weather in a given location
        :param location: The city and state, e.g. San Francisco, CA
        :param unit: The unit of measurement to use
        :raises ValueError: if the location is not available in self.cache
        :returns: the description of the weather, if it can be found
        """
