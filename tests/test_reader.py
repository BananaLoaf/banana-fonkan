import pytest

from banana_fonkan.reader import FonkanReader, TagData

TID_MEMORY_ADDRESS = 0
TID_MEMORY_LENGTH = 6
MAX_POWER = 255
MIN_POWER = 0


def is_hex(text: str) -> bool:
    return all(character in "0123456789ABCDEF" for character in text)


def assert_hex_payload(value: str | None) -> str:
    assert isinstance(value, str)
    assert is_hex(value)
    assert len(value) % 4 == 0
    return value


def assert_tag_data(value: TagData | None):
    assert isinstance(value, TagData)
    assert is_hex(value.pc)
    assert is_hex(value.epc)
    assert is_hex(value.crc16)
    assert len(value.pc) == 4
    assert len(value.epc) % 4 == 0
    assert len(value.crc16) == 4
    assert value.epc_words >= 0
    assert value.is_crc16_valid
    assert value.epc_valid_size


@pytest.mark.parametrize("reader_power", [MAX_POWER], indirect=True)
@pytest.mark.usefixtures("reader_power")
class TestReaderTags:
    @pytest.mark.flaky(reruns=19)
    def test_query_epc(self, reader: FonkanReader) -> None:
        tag = reader.query_epc()
        if tag is None:
            pytest.fail("Q command did not read a single tag in the current field")

        assert_tag_data(tag)
        assert tag.epc

    @pytest.mark.flaky(reruns=19)
    def test_multi_epc(self, reader: FonkanReader) -> None:
        tag = reader.multi_epc()
        if tag is None:
            pytest.fail("Q command did not read a single tag in the current field")

        assert_tag_data(tag)
        assert tag.epc

    @pytest.mark.flaky(reruns=19)
    def test_read_epc_memory(self, reader: FonkanReader) -> None:
        tag = reader.read_epc_memory()
        if tag is None:
            pytest.fail("Error reading EPC memory")

        assert_tag_data(tag)
        assert tag.epc

    @pytest.mark.flaky(reruns=19)
    def test_read_tid(self, reader: FonkanReader) -> None:
        tid = reader.read_tid_memory(TID_MEMORY_ADDRESS, TID_MEMORY_LENGTH)

        if tid is None:
            pytest.fail("Error reading TID memory")

        assert is_hex(tid)


@pytest.mark.parametrize("reader_power", [MIN_POWER], indirect=True)
@pytest.mark.usefixtures("reader_power")
class TestReaderMissingTags:
    @pytest.mark.flaky(reruns=19)
    def test_query_epc_returns_none(self, reader: FonkanReader) -> None:
        assert reader.query_epc() is None

    @pytest.mark.flaky(reruns=19)
    def test_multi_epc_returns_none(self, reader: FonkanReader) -> None:
        assert reader.multi_epc() is None

    @pytest.mark.flaky(reruns=19)
    def test_read_epc_memory_returns_none(self, reader: FonkanReader) -> None:
        assert reader.read_epc_memory() is None

    @pytest.mark.flaky(reruns=19)
    def test_read_tid_returns_none(self, reader: FonkanReader) -> None:
        assert reader.read_tid_memory(TID_MEMORY_ADDRESS, TID_MEMORY_LENGTH) is None
