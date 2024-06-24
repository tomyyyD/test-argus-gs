import signal
import sys

from lib.argus_lora import LoRa, ModemConfig
from lib.radio_utils import unpack_message
from lib.radiohead import RadioHead
from lib.mondo_db import Database


radio = LoRa(0, 19, 25, modem_config=ModemConfig.Bw125Cr45Sf128, acks=False, freq=433)
radiohead = RadioHead(radio, 10)

database = Database()


def hard_exit(radio, signum, fram):
    radio.close()
    database.client.close()
    sys.exit(0)


signal.signal(signal.SIGINT, lambda signum, frame: hard_exit(radio, signum, frame))

while True:
    print("receiving...")
    msg = radiohead.receive_message()
    if msg is not None:
        print(msg)
        type, time, data = unpack_message(msg)
        database.upload_data(type, time, data)
