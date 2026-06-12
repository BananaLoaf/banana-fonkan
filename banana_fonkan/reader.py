import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import IntEnum
from types import TracebackType
from typing import Self, cast

import serial  # type: ignore[import-untyped]

DEFAULT_BAUD_RATE = 38400
DEFAULT_TIMEOUT = 1.0
LINE_ENDING = b"\r\n"
CRC16_RESIDUE = 0x1D0F
HEX_DIGITS = frozenset("0123456789ABCDEFabcdef")


class MemoryBank(IntEnum):
    # Password and kill-password memory.
    RESERVED = 0
    # Electronic Product Code memory: CRC16, PC, and EPC data.
    EPC = 1
    # Tag Identifier memory: manufacturer/model/serial identity.
    TID = 2
    # Optional user data memory, if the tag supports it.
    USER = 3


class Regulation(IntEnum):
    US = 0x01
    TW = 0x02
    CN = 0x03
    CN2 = 0x04
    EU = 0x05
    JP = 0x06
    KR = 0x07
    VN = 0x08
    EU2 = 0x09
    IN = 0x0A


class BaudRate(IntEnum):
    BAUD_4800 = 0
    BAUD_9600 = 1
    BAUD_14400 = 2
    BAUD_19200 = 3
    BAUD_38400 = 4
    BAUD_57600 = 5
    BAUD_115200 = 6
    BAUD_230400 = 7


@dataclass(frozen=True)
class TagData:
    pc: str
    epc: str
    crc16: str
    epc_words: int = field(init=False)
    is_crc16_valid: bool = field(init=False)
    epc_valid_size: bool = field(init=False)

    def __post_init__(self) -> None:
        epc_words = (int(self.pc, 16) >> 11) & 0x1F
        payload = self.pc + self.epc + self.crc16

        try:
            data = bytes.fromhex(payload)
            is_crc16_valid = crc16(data) == CRC16_RESIDUE
        except ValueError:
            is_crc16_valid = False

        object.__setattr__(self, "epc_words", epc_words)
        object.__setattr__(self, "is_crc16_valid", is_crc16_valid)
        object.__setattr__(self, "epc_valid_size", len(self.epc) // 4 == epc_words)


def build_command(name: str, *parts: object) -> bytes:
    command = name if not parts else f"{name},{','.join(str(part) for part in parts)}"
    return f"\n{command}\r".encode()


def format_power(power: int) -> str:
    if not 0 <= power <= 255:
        msg = "power must be between 0 and 255"
        raise ValueError(msg)
    return f"{power:02X}"


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def parse_payload(response: str, prefix: str) -> str | None:
    if not response.startswith(prefix):
        return None

    payload = response.removeprefix(prefix)
    return payload or None


def parse_ok_response(response: str, prefix: str) -> bool | None:
    payload = parse_payload(response, prefix)
    ok = None
    if payload is not None:
        ok = payload == "<OK>"
    return ok


class FonkanReader:
    def __init__(
        self,
        port: str,
        *,
        baud_rate: int = DEFAULT_BAUD_RATE,
        timeout: float | None = DEFAULT_TIMEOUT,
    ) -> None:
        """Open a serial connection to the reader.

        :param port: Serial device path.
        :param baud_rate: UART baud rate used by the reader.
        :param timeout: Serial read timeout in seconds, or ``None`` to block.
        """
        self._serial = serial.Serial(port, baudrate=baud_rate, timeout=timeout)

    def query(self, command: bytes) -> str:
        """Send a raw command frame.

        :param command: Fully encoded reader command frame.
        :return: Last non-empty response line from the reader.
        """
        self._serial.reset_input_buffer()
        self._serial.write(command)
        response = self._serial.read_until(LINE_ENDING).strip().decode()
        lines = [line for line in response.splitlines() if line]
        return lines[-1] if lines else response

    def firmware_version(self) -> str:
        """Read the reader firmware/version response.

        :return: Firmware/version text without the command prefix.
        """
        return self.query(build_command("V")).removeprefix("V")

    def reader_id(self) -> str:
        """Read the reader identifier.

        :return: Reader identifier without the command prefix.
        """
        return self.query(build_command("S")).removeprefix("S")

    def set_uart_baud_rate(self, baud_rate: BaudRate) -> str:
        """Set the reader UART baud-rate code.

        :param baud_rate: Baud-rate enum value to send to the reader.
        :return: Raw reader response.
        """
        return self.query(build_command("NA", int(baud_rate)))

    def power(self) -> int:
        """Read the current RF output power.

        :return: Current power value.
        """
        return int(self.query(build_command("N0", "00")).removeprefix("N"), 16)

    def set_power(self, power: int, *, settle_time: float = 0.33) -> int:
        """Set RF output power.

        :param power: Power value from ``0`` to ``255``.
        :param settle_time: Settle time value in seconds to sleep before and after setting the power value.
        :return: Applied power value.
        """
        hex_power = format_power(power)

        time.sleep(settle_time)
        res = int(
            self.query(build_command("N1", hex_power)).removeprefix("N"),
            16,
        )
        time.sleep(settle_time)
        return res

    def regulation(self) -> Regulation:
        """Read the current regional regulation code.

        :return: Current regulation, or ``None`` when the reader returns no payload.
        """
        payload = cast(
            str,
            parse_payload(
                self.query(build_command("N4", "00")),
                "N",
            ),
        )
        return Regulation(int(payload, 16))

    def set_regulation(
        self,
        regulation: Regulation,
        *,
        settle_time: float = 0.33,
    ) -> Regulation:
        """Set the regional regulation code.

        :param regulation: Regulation enum value to apply.
        :param settle_time: Settle time value in seconds to sleep before and after setting regulation.
        :return: Applied regulation, or ``None`` when the reader returns no payload.
        """
        time.sleep(settle_time)
        payload = cast(
            str,
            parse_payload(
                self.query(build_command("N5", format_power(int(regulation)))),
                "N",
            ),
        )
        time.sleep(settle_time)
        return Regulation(int(payload, 16))

    def query_epc(self) -> TagData | None:
        """Read one nearby tag EPC inventory response.
        [PC][EPC words...][CRC16]

        :return: Parsed tag data, or ``None`` when no valid tag is read.
        """
        payload = parse_payload(self.query(build_command("Q")), "Q")
        tag = None

        if (
            payload is not None
            and len(payload) >= 8
            and len(payload) % 4 == 0
            and all(character in HEX_DIGITS for character in payload)
        ):
            tag = TagData(
                pc=payload[:4],
                epc=payload[4:-4],
                crc16=payload[-4:],
            )

        return tag

    def multi_epc(self) -> TagData | None:
        """Read one EPC from the reader's multi-tag inventory command.
        [PC][EPC words...][CRC16]

        :return: Parsed tag data, or ``None`` when no valid tag is read.
        """
        payload = parse_payload(self.query(build_command("U")), "U")
        tag = None

        if (
            payload is not None
            and len(payload) >= 8
            and len(payload) % 4 == 0
            and all(character in HEX_DIGITS for character in payload)
        ):
            tag = TagData(
                pc=payload[:4],
                epc=payload[4:-4],
                crc16=payload[-4:],
            )

        return tag

    def read_memory(
        self,
        bank: MemoryBank,
        address: int,
        length: int,
    ) -> str | None:
        """Read raw hex words from a tag memory bank.

        :param bank: Memory bank to read.
        :param address: Word address inside the memory bank.
        :param length: Number of 16-bit words to read.
        :return: Hex memory payload, or ``None`` when no valid payload is read.
        """
        return parse_payload(
            self.query(build_command(f"R{int(bank)}", address, length)),
            "R",
        )

    def read_epc_memory(self) -> TagData | None:
        """Read and parse CRC16, PC, and EPC from the EPC memory bank.
        [CRC16][PC][EPC words...]

        :return: Parsed tag data, or ``None`` when no valid tag is read.
        """
        pc = self.read_memory(MemoryBank.EPC, 1, 1)
        tag = None

        if pc is not None:
            epc_words = (int(pc, 16) >> 11) & 0x1F
            payload = self.read_memory(MemoryBank.EPC, 0, 2 + epc_words)

            if payload is not None:
                tag = TagData(
                    crc16=payload[:4],
                    pc=payload[4:8],
                    epc=payload[8:],
                )

        return tag

    def read_tid_memory(self, address: int, length: int) -> str | None:
        """Read the tag identifier memory bank.

        :param address: Word address inside the TID memory bank.
        :param length: Number of 16-bit words to read.
        :return: TID memory payload, or ``None`` when no valid tag is read.
        """
        return self.read_memory(MemoryBank.TID, address, length)

    def read_user_memory(self, address: int, length: int) -> str | None:
        """Read optional user memory from a tag.

        :param address: Word address inside the user memory bank.
        :param length: Number of 16-bit words to read.
        :return: User memory payload, or ``None`` when no valid payload is read.
        """
        return self.read_memory(MemoryBank.USER, address, length)

    # def multi_read_memory(
    #     self,
    #     slot: int,
    #     bank: MemoryBank,
    #     address: int,
    #     length: int,
    # ) -> tuple[str, str] | None:
    #     payload = parse_payload(
    #         self.query(build_command(f"U{slot}", f"R{int(bank)}", address, length)), "U"
    #     )
    #     read_result = None
    #
    #     if payload is not None and ",R" in payload:
    #         epc, read_data = payload.split(",R", maxsplit=1)
    #         if epc and read_data:
    #             read_result = (epc, read_data)
    #
    #     return read_result

    # def query_read_memory(
    #     self,
    #     bank: MemoryBank,
    #     address: int,
    #     length: int,
    # ) -> tuple[str, str] | None:
    #     payload = parse_payload(
    #         self.query(build_command("Q", f"R{int(bank)}", address, length)), "Q"
    #     )
    #     read_result = None
    #
    #     if payload is not None and ",R" in payload:
    #         epc, read_data = payload.split(",R", maxsplit=1)
    #         if epc and read_data:
    #             read_result = (epc, read_data)
    #
    #     return read_result

    def write_memory(
        self,
        bank: MemoryBank,
        address: int,
        length: int,
        data: bytes | str,
    ) -> bool | None:
        """Write words to a tag memory bank.

        :param bank: Memory bank to write.
        :param address: Word address inside the memory bank.
        :param length: Number of 16-bit words to write.
        :param data: Hex payload to write.
        :return: ``True`` when the reader returns ``<OK>``, ``False`` when it
            returns a non-OK write response, or ``None`` when no write payload is
            returned.
        """
        data_text = data.decode() if isinstance(data, bytes) else data
        return parse_ok_response(
            self.query(build_command("W" + str(int(bank)), address, length, data_text)),
            "W",
        )

    # def select_tag(
    #     self,
    #     bank: MemoryBank,
    #     bit_address: int,
    #     bit_length: int,
    #     bit_data: bytes | str,
    # ) -> str:
    #     data_text = bit_data.decode() if isinstance(bit_data, bytes) else bit_data
    #     return self.query(
    #         build_command("T", int(bank), bit_address, bit_length, data_text)
    #     )

    # def set_access_password(self, password: bytes | str) -> bool:
    #     password_text = password.decode() if isinstance(password, bytes) else password
    #     return self.query(build_command("P" + password_text)) == "P"

    # def kill_tag(self, password: bytes | str, recommissioning: int = 0) -> bool | None:
    #     password_text = password.decode() if isinstance(password, bytes) else password
    #     return parse_ok_response(
    #         self.query(build_command("K" + password_text, recommissioning)), "K"
    #     )

    # def lock_memory(self, mask: str, action: str) -> bool | None:
    #     return parse_ok_response(self.query(build_command("L" + mask, action)), "L")

    def poll_multi_epc(self, *, delay: float = 0.1) -> Iterator[TagData | None]:
        while True:
            yield self.multi_epc()
            time.sleep(delay)

    def close(self) -> None:
        self._serial.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
