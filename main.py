import busio
import time
import board
import digitalio
from lib.rfm9x import RFM9x

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

cs = digitalio.DigitalInOut(board.D8)
reset = digitalio.DigitalInOut(board.D25)

cs.switch_to_output(value=True)
reset.switch_to_output(value=True)

# radio_DIO0 = digitalio.DigitalInOut(board.RF_IO0)
# radio_DIO0.switch_to_input()

radio = RFM9x(
    spi,
    cs,
    reset,
    433.0,
    baudrate=5000000
)

msg = b"hello"
while True:
    print(f"sending...\nmessage: {msg}")
    radio.send(b'hello')
    time.sleep(2)
    print("receiving...")
    radio.receive()
