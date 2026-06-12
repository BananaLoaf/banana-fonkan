import pytest

from banana_fonkan.reader import FonkanReader, MemoryBank, TagData

TID_MEMORY_ADDRESS = 0
TID_MEMORY_LENGTH = 6
USER_MEMORY_ADDRESS = 0
USER_MEMORY_LENGTH = 1
MIN_POWER = 0


def is_hex(text: str) -> bool:
    return all(character in "0123456789ABCDEF" for character in text)


def assert_tag_data(value: TagData | None) -> None:
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


@pytest.mark.parametrize("reader_power", [MIN_POWER], indirect=True)
@pytest.mark.usefixtures("reader_power")
class TestReaderWriteMemory:
    @pytest.mark.flaky(reruns=19)
    def test_write_epc_memory_same_word(self, reader: FonkanReader) -> None:
        tag = reader.query_epc()
        if tag is None:
            pytest.fail("EPC write test requires one queryable tag in range")

        assert_tag_data(tag)
        word = tag.epc[:4]

        assert reader.write_memory(MemoryBank.EPC, 2, 1, word) is True
        assert reader.query_epc() == tag

    @pytest.mark.flaky(reruns=19)
    def test_write_tid_memory_is_not_allowed(self, reader: FonkanReader) -> None:
        tid = reader.read_tid_memory(TID_MEMORY_ADDRESS, TID_MEMORY_LENGTH)
        if tid is None:
            pytest.skip("TID write test requires readable TID memory")

        assert reader.write_memory(MemoryBank.TID, 0, 1, tid[:4]) is not True

    @pytest.mark.flaky(reruns=19)
    def test_write_user_memory_same_word(self, reader: FonkanReader) -> None:
        word = reader.read_user_memory(USER_MEMORY_ADDRESS, USER_MEMORY_LENGTH)
        if word is None:
            pytest.fail("USER write test requires one queryable tag in range")

        assert reader.write_memory(MemoryBank.USER, 0, 1, word) is True
        assert reader.read_user_memory(USER_MEMORY_ADDRESS, USER_MEMORY_LENGTH) == word
