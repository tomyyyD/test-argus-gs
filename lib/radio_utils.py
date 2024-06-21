import datetime
import sys


def hard_exit(radio, signum, fram):
    radio.close()
    sys.exit(0)


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
    print(header_info)
