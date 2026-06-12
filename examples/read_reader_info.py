from banana_fonkan.reader import FonkanReader


def main() -> None:
    with FonkanReader("/dev/tty.usbmodem5B170096841", timeout=0.5) as reader:
        print("firmware_version", repr(reader.firmware_version()))
        print("reader_id", repr(reader.reader_id()))
        print("power", repr(reader.power()))
        print("regulation", repr(reader.regulation()))


if __name__ == "__main__":
    main()
