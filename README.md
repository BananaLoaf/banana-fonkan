# banana-fonkan

Unofficial Python library for communicating with Fonkan RFID readers over a serial
connection.

## Installation

```bash
pip install banana-fonkan
# or 
uv add banana-fonkan
# or
poetry add banana-fonkan
```

For local development in this repository:

```bash
uv sync
```

## Basic Usage

```python
from banana_fonkan.reader import FonkanReader

PORT = "/dev/tty.usbmodemXXXX"

with FonkanReader(PORT) as reader:
    print(reader.firmware_version())
    print(reader.reader_id())
    print(reader.power())

    print(reader.set_power(255))
    tag = reader.multi_epc()
    # For multiple reads
    # tag = reader.query_epc() 
    if tag is not None:
        print(tag.pc)
        print(tag.epc)
        print(tag.crc16)
        print(tag.is_crc16_valid)
```

## Reading Tag Memory

```python
from banana_fonkan.reader import FonkanReader

PORT = "/dev/tty.usbmodemXXXX"

with FonkanReader(PORT) as reader:
    epc_memory = reader.read_epc_memory()

    if epc_memory is not None:
        print(epc_memory.pc)
        print(epc_memory.epc)
        print(epc_memory.crc16)
```

The memory banks are:

- `MemoryBank.RESERVED`: kill/access password memory
- `MemoryBank.EPC`: CRC16, PC, and EPC memory
- `MemoryBank.TID`: tag identifier memory
- `MemoryBank.USER`: optional user data memory

Convenience methods are available for the reads used while mapping the hardware.
EPC memory is read dynamically: the first read gets the PC word, then the reader
uses the EPC word count from PC to read the full EPC payload.

```python
with FonkanReader(PORT) as reader:
    print(reader.read_tid_memory(0, 6))
    print(reader.read_user_memory(0, 2))
```

## Polling Tags

```python
from banana_fonkan.reader import FonkanReader

PORT = "/dev/tty.usbmodemXXXX"
TARGET_EPC = "E280691500004021BBE17A29"

with FonkanReader(PORT) as reader:
    reader.set_power(127)

    for tag in reader.poll_multi_epc(delay=0.1):
        if tag is not None and tag.epc == TARGET_EPC:
            print(tag)
```

## Reader Settings

```python
from banana_fonkan.reader import BaudRate, FonkanReader, Regulation

PORT = "/dev/tty.usbmodem5B170096841"

with FonkanReader(PORT) as reader:
    print(reader.power())
    print(reader.set_power(255))
    print(reader.regulation())
    print(reader.set_regulation(Regulation.EU))
    print(reader.set_uart_baud_rate(BaudRate.BAUD_57600))
```

`set_power()` and `set_regulation()` wait briefly before and after sending the
command so the reader has time to apply RF settings.

## Writing Memory

```python
from banana_fonkan.reader import FonkanReader, MemoryBank

PORT = "/dev/tty.usbmodemXXXX"
TID = "E280691500004021BBE17A29"

with FonkanReader(PORT) as reader:
    print(reader.write_memory(MemoryBank.EPC, 2, 6, TID))
```

Be careful with write operations; they modify tags. In local hardware testing,
USER memory and EPC memory may be writable depending on the tag, while TID
memory is expected not to be writable.

## Raw Commands

If the wrapper does not expose a command yet, use `query()` directly:

```python
from banana_fonkan.reader import FonkanReader, build_command

PORT = "/dev/tty.usbmodemXXXX"

with FonkanReader(PORT) as reader:
    print(reader.query(build_command("V")))
    print(reader.query(b"\nN1,FF\r"))
```

The UART baud-rate command from the hardware scratch script is also exposed:

```python
from banana_fonkan.reader import BaudRate, FonkanReader

with FonkanReader(PORT) as reader:
    print(reader.set_uart_baud_rate(BaudRate.BAUD_57600))
```

## Examples

The repository includes small scripts with constants at the top:

- `examples/read_reader_info.py`: prints reader metadata and current settings
- `examples/capture_tags.py`: captures tag data using `poll_multi_epc` in a loop
- `examples/read_epc_memory.py`: reads parsed EPC memory repeatedly

## Development

```bash
uv run poe lint
uv run poe typecheck
uv run poe test -q
```

The test suite talks to a real reader found with `/dev/tty.usbmodem*`.
`tests/test_device.py` covers reader commands that do not require a tag.
`tests/test_power.py` covers power reads, writes, and invalid power values.
`tests/test_reader.py` covers tag reads and no-tag reads.
`tests/test_write_memory.py` covers memory writes. Hardware tests use pytest reruns for operations that
sometimes miss on the first attempt.

## Tested Hardware

Tested with:
- `Fonkan FM-509`, `865-868 MHz`, `120mm`, integrated `5.5dBi` ceramic antenna. ([AliExpress page](https://aliexpress.ru/item/1005008298553392.html?sku_id=12000053383057719))
