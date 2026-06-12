from banana_fonkan.reader import FonkanReader, Regulation


class TestReaderDevice:
    def test_reader_info(self, reader: FonkanReader) -> None:
        assert reader.firmware_version()
        assert reader.reader_id()

    def test_reader_regulation(self, reader: FonkanReader) -> None:
        regulation = reader.regulation()
        assert isinstance(regulation, Regulation)
