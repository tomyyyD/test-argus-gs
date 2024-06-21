import signal

from lib.argus_lora import LoRa, ModemConfig
from lib.radio_utils import hard_exit, unpack_message
from lib.radiohead import RadioHead

radio = LoRa(0, 19, 25, modem_config=ModemConfig.Bw125Cr45Sf128, acks=False, freq=433)
radiohead = RadioHead(radio, 1)

signal.signal(signal.SIGINT, lambda signum, frame: hard_exit(radio, signum, frame))

while True:
    print("receiving...")
    msg = radiohead.receive_message()
    if msg is not None:
        print(msg)
        unpack_message(msg)
