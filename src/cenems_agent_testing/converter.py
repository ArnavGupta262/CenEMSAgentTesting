"""Temperature conversion helpers for the agent workflow pilot."""

from __future__ import annotations

from enum import Enum


class TemperatureScale(str, Enum):
    """Supported temperature scales."""

    CELSIUS = "celsius"
    KELVIN = "kelvin"


def convert_temperature(value: float, source: TemperatureScale, target: TemperatureScale) -> float:
    """Convert a temperature value between supported scales."""

    if source == target:
        return value

    if source == TemperatureScale.CELSIUS and target == TemperatureScale.KELVIN:
        return value + 273.15

    if source == TemperatureScale.KELVIN and target == TemperatureScale.CELSIUS:
        return value - 273.15

    raise ValueError(f"Unsupported conversion: {source} to {target}")
