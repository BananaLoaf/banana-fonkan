import pytest

from banana_fonkan.reader import FonkanReader

MAX_POWER = 255
MIN_POWER = 0


class TestReaderPower:
    def test_read_power(self, reader: FonkanReader) -> None:
        power = reader.power()

        assert MIN_POWER <= power <= MAX_POWER

    def test_set_min_power(self, reader: FonkanReader) -> None:
        assert reader.set_power(MIN_POWER) == MIN_POWER

    def test_set_max_power(self, reader: FonkanReader) -> None:
        assert reader.set_power(MAX_POWER) == MAX_POWER

    def test_set_power_rejects_negative_value(self, reader: FonkanReader) -> None:
        with pytest.raises(ValueError, match="power must be between 0 and 255"):
            reader.set_power(-1)

    def test_set_power_rejects_too_large_value(self, reader: FonkanReader) -> None:
        with pytest.raises(ValueError, match="power must be between 0 and 255"):
            reader.set_power(256)
