import math
import time
from collections import namedtuple
from enum import Enum
from random import random

import spidev
from gpiozero import Button

from lib.constants import Definitions


class ModemConfig(Enum):
    Bw125Cr45Sf128 = (0x72, 0x74, 0x04)
    Bw500Cr45Sf128 = (0x92, 0x74, 0x04)
    Bw31_25Cr48Sf512 = (0x48, 0x94, 0x04)
    Bw125Cr48Sf4096 = (0x78, 0xc4, 0x0c)


class LoRa(object):
    def __init__(self, channel, interrupt, this_address, freq=915, tx_power=14,
                 modem_config=ModemConfig.Bw125Cr45Sf128, receive_all=False,
                 acks=False, crypto=None):

        self._channel = channel
        self._interrupt = interrupt

        self._mode = None
        self._cad = None
        self._freq = freq
        self._tx_power = tx_power
        self._modem_config = modem_config
        self._receive_all = receive_all
        self._acks = acks

        self._this_address = this_address
        self._last_header_id = 0

        self._last_payload = None
        self.crypto = crypto

        self.cad_timeout = 0
        self.send_retries = 2
        self.wait_packet_sent_timeout = 0.2
        self.retry_timeout = 0.2

        self.crc_error_count = 0

        # Setup the module
        btn = Button(self._interrupt, pull_up=False)
        btn.when_pressed = self._handle_interrupt

        self.spi = spidev.SpiDev()
        self.spi.open(0, self._channel)
        self.spi.max_speed_hz = 5000000

        self._spi_write(Definitions.REG_01_OP_MODE, Definitions.MODE_SLEEP | Definitions.LONG_RANGE_MODE)
        time.sleep(0.1)

        assert self._spi_read(Definitions.REG_01_OP_MODE) == (Definitions.MODE_SLEEP | Definitions.LONG_RANGE_MODE), \
            "LoRa initialization failed"

        self._spi_write(Definitions.REG_0E_FIFO_TX_BASE_ADDR, 0)
        self._spi_write(Definitions.REG_0F_FIFO_RX_BASE_ADDR, 0)

        self.set_mode_idle()

        # set modem config (Bw125Cr45Sf128)
        self._spi_write(Definitions.REG_1D_MODEM_CONFIG1, self._modem_config.value[0])
        self._spi_write(Definitions.REG_1E_MODEM_CONFIG2, self._modem_config.value[1])
        self._spi_write(Definitions.REG_26_MODEM_CONFIG3, self._modem_config.value[2])

        # set preamble length (8)
        self._spi_write(Definitions.REG_20_PREAMBLE_MSB, 0)
        self._spi_write(Definitions.REG_21_PREAMBLE_LSB, 8)

        # set frequency
        frf = int((self._freq * 1000000.0) / Definitions.FSTEP)
        self._spi_write(Definitions.REG_06_FRF_MSB, (frf >> 16) & 0xff)
        self._spi_write(Definitions.REG_07_FRF_MID, (frf >> 8) & 0xff)
        self._spi_write(Definitions.REG_08_FRF_LSB, frf & 0xff)

        # Set tx power
        if self._tx_power < 5:
            self._tx_power = 5
        if self._tx_power > 23:
            self._tx_power = 23

        '''
        if self._tx_power < 20:
            self._spi_write(REG_4D_PA_DAC, PA_DAC_ENABLE)
            self._tx_power -= 3
        else:
            self._spi_write(REG_4D_PA_DAC, PA_DAC_DISABLE)

        self._spi_write(REG_09_PA_CONFIG, PA_SELECT | (self._tx_power - 5))
        '''
        self._spi_write(Definitions.REG_4D_PA_DAC, 0x4)
        self._spi_write(Definitions.REG_09_PA_CONFIG, 0xFF)
        # print(self._spi_read(REG_4D_PA_DAC))
        # print(self._spi_read(REG_09_PA_CONFIG))

        # CRC Enable
        self.enable_crc = True

    def on_recv(self, message):
        # This should be overridden by the user
        print("Message received!")
        pass

    def sleep(self):
        if self._mode != Definitions.MODE_SLEEP:
            self._spi_write(Definitions.REG_01_OP_MODE, Definitions.MODE_SLEEP)
            self._mode = Definitions.MODE_SLEEP

    def set_mode_tx(self):
        if self._mode != Definitions.MODE_TX:
            self._spi_write(Definitions.REG_01_OP_MODE, Definitions.MODE_TX)
            self._spi_write(Definitions.REG_40_DIO_MAPPING1, 0x40)  # Interrupt on TxDone
            self._mode = Definitions.MODE_TX

    def set_mode_rx(self):
        if self._mode != Definitions.MODE_RXCONTINUOUS:
            self._spi_write(Definitions.REG_01_OP_MODE, Definitions.MODE_RXCONTINUOUS)
            self._spi_write(Definitions.REG_40_DIO_MAPPING1, 0x00)  # Interrupt on RxDone
            self._mode = Definitions.MODE_RXCONTINUOUS

    def set_mode_cad(self):
        if self._mode != Definitions.MODE_CAD:
            self._spi_write(Definitions.REG_01_OP_MODE, Definitions.MODE_CAD)
            self._spi_write(Definitions.REG_40_DIO_MAPPING1, 0x80)  # Interrupt on CadDone
            self._mode = Definitions.MODE_CAD

    def _is_channel_active(self):
        self.set_mode_cad()

        while self._mode == Definitions.MODE_CAD:
            yield

        return self._cad

    def wait_cad(self):
        if not self.cad_timeout:
            return True

        start = time.time()
        for status in self._is_channel_active():
            if time.time() - start < self.cad_timeout:
                return False

            if status is None:
                time.sleep(0.1)
                continue
            else:
                return status

    def wait_packet_sent(self):
        # wait for `_handle_interrupt` to switch the mode back
        start = time.time()
        while time.time() - start < self.wait_packet_sent_timeout:
            if self._mode != Definitions.MODE_TX:
                return True

        return False

    def set_mode_idle(self):
        if self._mode != Definitions.MODE_STDBY:
            self._spi_write(Definitions.REG_01_OP_MODE, Definitions.MODE_STDBY)
            time.sleep(0.1)
            self._mode = Definitions.MODE_STDBY

    def send(self, data, header_to, header_id=0, header_flags=0):
        self.wait_packet_sent()
        self.set_mode_idle()
        self.wait_cad()

        header = [header_to, self._this_address, header_id, header_flags]
        if isinstance(data, int):
            data = [data]
        elif isinstance(data, bytes):
            data = [p for p in data]
        elif isinstance(data, str):
            data = [ord(s) for s in data]

        if self.crypto:
            data = [b for b in self._encrypt(bytes(data))]

        payload = header + data

        self._spi_write(Definitions.REG_0D_FIFO_ADDR_PTR, 0)
        self._spi_write(Definitions.REG_00_FIFO, payload)
        self._spi_write(Definitions.REG_22_PAYLOAD_LENGTH, len(payload))
        self.set_mode_tx()

        return True

    def send_to_wait(self, data, header_to, header_flags=0, retries=3):
        self._last_header_id += 1

        for _ in range(retries + 1):
            self.send(data, header_to, header_id=self._last_header_id, header_flags=header_flags)
            self.set_mode_rx()

            if header_to == Definitions.BROADCAST_ADDRESS:  # Don't wait for acks from a broadcast message
                return True

            start = time.time()
            while time.time() - start < self.retry_timeout + (self.retry_timeout * random()):
                if self._last_payload:
                    if self._last_payload.header_to == self._this_address and \
                            self._last_payload.header_flags & Definitions.FLAGS_ACK and \
                            self._last_payload.header_id == self._last_header_id:

                        # We got an ACK
                        return True
        return False

    def send_ack(self, header_to, header_id):
        self.send(b'!', header_to, header_id, Definitions.FLAGS_ACK)
        self.wait_packet_sent()

    def _spi_write(self, register, payload):
        if isinstance(payload, int):
            payload = [payload]
        elif isinstance(payload, bytes):
            payload = [p for p in payload]
        elif isinstance(payload, str):
            payload = [ord(s) for s in payload]

        self.spi.xfer([register | 0x80] + payload)

    def _spi_read(self, register, length=1):
        if length == 1:
            return self.spi.xfer([register] + [0] * length)[1]
        else:
            return self.spi.xfer([register] + [0] * length)[1:]

    def _decrypt(self, message):
        decrypted_msg = self.crypto.decrypt(message)
        msg_length = decrypted_msg[0]
        return decrypted_msg[1:msg_length + 1]

    def _encrypt(self, message):
        msg_length = len(message)
        padding = bytes(((math.ceil((msg_length + 1) / 16) * 16) - (msg_length + 1)) * [0])
        msg_bytes = bytes([msg_length]) + message + padding
        encrypted_msg = self.crypto.encrypt(msg_bytes)
        return encrypted_msg

    def _handle_interrupt(self, channel):
        irq_flags = self._spi_read(Definitions.REG_12_IRQ_FLAGS)

        if self._mode == Definitions.MODE_RXCONTINUOUS and (irq_flags & Definitions.RX_DONE) and (self.crc_error() == 0):
            packet_len = self._spi_read(Definitions.REG_13_RX_NB_BYTES)
            self._spi_write(Definitions.REG_0D_FIFO_ADDR_PTR, self._spi_read(Definitions.REG_10_FIFO_RX_CURRENT_ADDR))

            packet = self._spi_read(Definitions.REG_00_FIFO, packet_len)
            self._spi_write(Definitions.REG_12_IRQ_FLAGS, 0xff)  # Clear all IRQ flags

            snr = self._spi_read(Definitions.REG_19_PKT_SNR_VALUE) / 4
            rssi = self._spi_read(Definitions.REG_1A_PKT_RSSI_VALUE)

            if snr < 0:
                rssi = snr + rssi
            else:
                rssi = rssi * 16 / 15

            if self._freq >= 779:
                rssi = round(rssi - 157, 2)
            else:
                rssi = round(rssi - 164, 2)

            if packet_len >= 4:
                header_to = packet[0]
                header_from = packet[1]
                header_id = packet[2]
                header_flags = packet[3]
                message = bytes(packet[4:]) if packet_len > 4 else b''

                # for i in range(0,packet_len):
                #     print(hex(packet[i]))

                if (header_to != 255 and self._this_address != header_to) or self._receive_all is True:
                    return

                if self.crypto and len(message) % 16 == 0:
                    message = self._decrypt(message)

                if self._acks and header_to == self._this_address and not header_flags & Definitions.FLAGS_ACK:
                    self.send_ack(header_from, header_id)

                self.set_mode_rx()

                self._last_payload = namedtuple(
                    "Payload",
                    ['message', 'header_to', 'header_from', 'header_id', 'header_flags', 'rssi', 'snr']
                )(message, header_to, header_from, header_id, header_flags, rssi, snr)

                if not header_flags & Definitions.FLAGS_ACK:
                    self.on_recv(self._last_payload)

        elif self._mode == Definitions.MODE_TX and (irq_flags & Definitions.TX_DONE):
            self.set_mode_idle()

        elif self._mode == Definitions.MODE_CAD and (irq_flags & Definitions.CAD_DONE):
            self._cad = irq_flags & Definitions.CAD_DETECTED
            self.set_mode_idle()

        self._spi_write(Definitions.REG_12_IRQ_FLAGS, 0xff)

    @property
    def enable_crc(self):
        """Set to True to enable hardware CRC checking of incoming packets.
        Incoming packets that fail the CRC check are not processed.  Set to
        False to disable CRC checking and process all incoming packets.
        Taken from PyCubed Repo by Max Holliday"""
        return (self._spi_read(Definitions.REG_1E_MODEM_CONFIG2) & 0x04) == 0x04

    @enable_crc.setter
    def enable_crc(self, val):
        # Optionally enable CRC checking on incoming packets.
        # Taken from PyCubed Repo by Max Holliday
        if val:
            self._spi_write(Definitions.REG_1E_MODEM_CONFIG2, self._spi_read(Definitions.REG_1E_MODEM_CONFIG2) | 0x04)
        else:
            self._spi_write(Definitions.REG_1E_MODEM_CONFIG2, self._spi_read(Definitions.REG_1E_MODEM_CONFIG2) & 0xFB)

    def crc_error(self):
        """crc status. Taken from PyCubed Repo by Max Holliday"""
        error = (self._spi_read(Definitions.REG_12_IRQ_FLAGS) & 0x20) >> 5

        if (error == 1):
            print("CRC Error!")
            self.crc_error_count += 1
        return error

    def close(self):
        # GPIO.cleanup()
        self.spi.close()
