import subprocess
import time

from banana_fonkan.reader import FonkanReader, TagData

POWER = 255
CAPTURE_SECONDS = 10.0
POLL_DELAY_SECONDS = 0.02


def main():
    seen: dict[TagData, int] = {}

    with FonkanReader("/dev/tty.usbmodem5B170096841", timeout=0.5) as reader:
        print(f"set_power={reader.set_power(POWER, settle_time=1)}")

        for response in reader.poll_multi_epc(delay=POLL_DELAY_SECONDS):
            seen[response] = seen.get(response, 0) + 1
            if seen[response] == 1:
                print(f"new response={response}")
                subprocess.Popen(["afplay", "/System/Library/Sounds/Ping.aiff"])
            time.sleep(POLL_DELAY_SECONDS)


if __name__ == "__main__":
    main()
