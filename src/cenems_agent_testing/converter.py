"""Temperature conversion helpers for the agent workflow pilot."""

from __future__ import annotations

from enum import Enum


class TemperatureScale(str, Enum):
    """Supported temperature scales."""

    CELSIUS = "celsius"
    KELVIN = "kelvin"
    FAHRENHEIT = "fahrenheit"


def convert_temperature(value: float, source: TemperatureScale, target: TemperatureScale) -> float:
    """Convert a temperature value between supported scales."""

    if source == target:
        return value

    if source == TemperatureScale.CELSIUS and target == TemperatureScale.KELVIN:
        return value + 273.15

    if source == TemperatureScale.KELVIN and target == TemperatureScale.CELSIUS:
        return value - 273.15

    if source == TemperatureScale.CELSIUS and target == TemperatureScale.FAHRENHEIT:
        return (value * 9 / 5) + 32

    if source == TemperatureScale.FAHRENHEIT and target == TemperatureScale.CELSIUS:
        return (value - 32) * 5 / 9

    if source == TemperatureScale.KELVIN and target == TemperatureScale.FAHRENHEIT:
        celsius = value - 273.15
        return (celsius * 9 / 5) + 32

    if source == TemperatureScale.FAHRENHEIT and target == TemperatureScale.KELVIN:
        celsius = (value - 32) * 5 / 9
        return celsius + 273.15

    raise ValueError(f"Unsupported conversion: {source} to {target}")
