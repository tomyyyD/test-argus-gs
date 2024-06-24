import datetime
import sys


class Definitions:
    # Message ID definitions
    SAT_HEARTBEAT_BATT = 0x00
    SAT_HEARTBEAT_SUN = 0x01
    SAT_HEARTBEAT_IMU = 0x02
    SAT_HEARTBEAT_GPS = 0x03
    SAT_HEARTBEAT_JETSON = 0x04

    GS_ACK = 0x08
    SAT_ACK = 0x09

    GS_OTA_REQ = 0x14
    SAT_OTA_RES = 0x15

    SAT_IMG_INFO = 0x21
    SAT_DEL_IMG = 0x22

    GS_STOP = 0x30

    SAT_IMG_CMD = 0x50

    REQ_ACK_NUM = 0x80


def hard_exit(radio, signum, fram):
    radio.close()
    sys.exit(0)


def unpack_header(msg):
    ack_req = (int.from_bytes((msg.message[0:1]), byteorder='big') & 0b10000000) >> 7
    message_ID = int.from_bytes((msg.message[0:1]), byteorder='big') & 0b01111111
    message_sequence_count = int.from_bytes(msg.message[1:3], byteorder='big')
    message_size = int.from_bytes(msg.message[3:4], byteorder='big')
    return ack_req, message_ID, message_sequence_count, message_size


def unpack_message(msg):
    # Get the current time
    current_time = datetime.datetime.now()
    # Format the current time
    formatted_time = current_time.strftime("%Y-%m-%d_%H-%M-%S\n")
    formatted_time = formatted_time.encode('utf-8')

    header_info = (f"Header To: {msg.header_to}," +
                   f"Header From: {msg.header_from}," +
                   f"Header ID: {msg.header_id}," +
                   f"Header Flags: {msg.header_flags}," +
                   f"RSSI: {msg.rssi}," +
                   f"SNR: {msg.snr}\n")
    header_info = header_info.encode('utf-8')
    payload = f"Payload: {msg.message}\n\n"
    payload = payload.encode('utf-8')
    (ack, msg_id, msg_seq_count, msg_size) = unpack_header(msg)
    print(header_info)
    if msg_id == Definitions.SAT_HEARTBEAT_BATT:
        print("battery heartbeat")
        """
        byte 0: batt_soc
        byte 1: current msb
        byte 2: current lsb
        byte 3: boot count
        byte 4: time high
        byte 5: time mid high
        byte 6: time mid low
        byte 7: time low
        """
        batt_soc = msg.message[0]
        current = msg.message[1] << 8 | msg.message[2]
        boot_count = msg.message[3]
        time = (msg.message[4] << 24 |
                msg.message[5] << 16 |
                msg.message[6] << 8 |
                msg.message[7])
        print(f"battery soc: {batt_soc}")
        print(f"current: {current}")
        print(f"boot count: {boot_count}")
        print(f"time: {time}")
    elif msg_id == Definitions.SAT_HEARTBEAT_SUN:
        print("IMU heartbeat")
        """
        byte 0: sun vector x
        byte 1: sun vector y
        byte 2: sun vector 1
        bytes 3-6: time
        """
        sun_vec_x = msg.message[0]
        sun_vec_y = msg.message[1]
        sun_vec_z = msg.message[2]

        time = (msg.message[4] << 24 |
                msg.message[5] << 16 |
                msg.message[6] << 8 |
                msg.message[7])
        print(f"sun vector: ({sun_vec_x}, {sun_vec_y}, {sun_vec_z})")
        print(f"time: {time}")
    elif msg_id == Definitions.SAT_HEARTBEAT_IMU:
        print("sun heartbeat")
