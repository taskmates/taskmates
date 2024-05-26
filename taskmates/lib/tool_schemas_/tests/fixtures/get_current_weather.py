from typing import Literal

# from enum import Enum
# class MetricSystem(Enum):
#     fahrenheit = 1
#     celsius = 2
# def get_current_weather(location: str, unit: MetricSystem):

def get_current_weather(location: str, unit: Literal["celsius", "fahrenheit"] = "celsius"):
    """
    Get the current weather in a given location
    :param location: The city and state, e.g. San Francisco, CA
    """
