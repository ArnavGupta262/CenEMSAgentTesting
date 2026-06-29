import unittest

from src.cenems_agent_testing import TemperatureScale, convert_temperature


class TemperatureConversionTests(unittest.TestCase):
    def test_celsius_to_kelvin(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(21.5, TemperatureScale.CELSIUS, TemperatureScale.KELVIN),
            294.65,
        )

    def test_kelvin_to_celsius(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(294.65, TemperatureScale.KELVIN, TemperatureScale.CELSIUS),
            21.5,
        )

    def test_same_scale_returns_value(self) -> None:
        self.assertEqual(
            convert_temperature(12.0, TemperatureScale.CELSIUS, TemperatureScale.CELSIUS),
            12.0,
        )

    def test_unsupported_conversion_raises(self) -> None:
        class FakeScale:
            value = "rankine"

            def __str__(self) -> str:
                return self.value

        with self.assertRaises(ValueError):
            convert_temperature(12.0, TemperatureScale.CELSIUS, FakeScale())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
