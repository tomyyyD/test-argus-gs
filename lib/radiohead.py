import time

from gpiozero import LED


class RadioHead:
    def __init__(self, radio, receive_timeout) -> None:
        self.radio = radio
        self.receive_timeout = receive_timeout
        self.radio.on_recv = self.on_recv

        self.rx_ctrl = LED(22)
        self.tx_ctrl = LED(23)
        self.receive_success = False

    def receive_message(self) -> bytes:
        self.rx_ctrl.on()
        self.radio.set_mode_rx()
        self.receive_success = False
        start = time.monotonic()
        timed_out = False
        while not self.receive_success and not timed_out:
            if (time.monotonic() - start) >= self.receive_timeout:
                timed_out = True
        if timed_out:
            return None
        return self.last_payload

    def on_recv(self, payload):
        self.receive_success = True
        self.last_payload = payload
