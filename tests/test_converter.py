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

    def test_celsius_to_fahrenheit(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(0, TemperatureScale.CELSIUS, TemperatureScale.FAHRENHEIT),
            32,
        )

    def test_celsius_to_fahrenheit_positive(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(21.5, TemperatureScale.CELSIUS, TemperatureScale.FAHRENHEIT),
            70.7,
        )

    def test_celsius_to_fahrenheit_negative(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(-40, TemperatureScale.CELSIUS, TemperatureScale.FAHRENHEIT),
            -40,
        )

    def test_fahrenheit_to_celsius(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(32, TemperatureScale.FAHRENHEIT, TemperatureScale.CELSIUS),
            0,
        )

    def test_fahrenheit_to_celsius_positive(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(70.7, TemperatureScale.FAHRENHEIT, TemperatureScale.CELSIUS),
            21.5,
        )

    def test_fahrenheit_to_celsius_negative(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(-40, TemperatureScale.FAHRENHEIT, TemperatureScale.CELSIUS),
            -40,
        )

    def test_kelvin_to_fahrenheit(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(273.15, TemperatureScale.KELVIN, TemperatureScale.FAHRENHEIT),
            32,
        )

    def test_kelvin_to_fahrenheit_positive(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(294.65, TemperatureScale.KELVIN, TemperatureScale.FAHRENHEIT),
            70.7,
        )

    def test_fahrenheit_to_kelvin(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(32, TemperatureScale.FAHRENHEIT, TemperatureScale.KELVIN),
            273.15,
        )

    def test_fahrenheit_to_kelvin_positive(self) -> None:
        self.assertAlmostEqual(
            convert_temperature(70.7, TemperatureScale.FAHRENHEIT, TemperatureScale.KELVIN),
            294.65,
        )

    def test_fahrenheit_same_scale_returns_value(self) -> None:
        self.assertEqual(
            convert_temperature(98.6, TemperatureScale.FAHRENHEIT, TemperatureScale.FAHRENHEIT),
            98.6,
        )


if __name__ == "__main__":
    unittest.main()
