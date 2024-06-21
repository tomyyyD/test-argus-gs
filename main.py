from lib.argus_lora import LoRa, ModemConfig
from lib.radiohead import RadioHead

radio = LoRa(0, 19, 25, modem_config=ModemConfig.Bw125Cr45Sf128, acks=False, freq=915)

radiohead = RadioHead(radio, 1)

while True:
    print("receiving...")
    msg = radiohead.receive_message()
    if msg is not None:
        print(msg)
