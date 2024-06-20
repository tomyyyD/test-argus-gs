import spidev
import time

spi = spidev.SpiDev(0, 0)
spi.max_speed_hz = 5000000

spi.xfer([0x01, 0x80])
time.sleep(1)
result = spi.xfer([0x01, 0])

print(result)
