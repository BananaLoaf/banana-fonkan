from collections.abc import Iterator
from glob import glob

import pytest

from banana_fonkan.reader import FonkanReader

SERIAL_TIMEOUT = 0.3
TAG_POWER_SETTLE_SECONDS = 3.0


@pytest.fixture(scope="session")
def device() -> str:
    devices = sorted(glob("/dev/tty.usbmodem*"))
    if not devices:
        pytest.skip("No /dev/tty.usbmodem* device found")
    return devices[0]


@pytest.fixture
def reader(device: str) -> Iterator[FonkanReader]:
    with FonkanReader(device, timeout=SERIAL_TIMEOUT) as reader:
        yield reader


@pytest.fixture(scope="class")
def reader_power(reader: FonkanReader, request: pytest.FixtureRequest) -> None:
    power = request.param
    reader.set_power(power, settle_time=TAG_POWER_SETTLE_SECONDS)
