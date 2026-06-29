"""Tiny conversion library used by the CenEMS agent pilot."""

from .converter import TemperatureScale, convert_temperature

__all__ = ["TemperatureScale", "convert_temperature"]
