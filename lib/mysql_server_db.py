import mysql.connector
from constants import Message_IDS


class Database:
    def __init__(self) -> None:
        self.client = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rexlab",
            database="heartbeats",
        )
        self.cursor = self.client.cursor()

    def upload_data(self, type, time, data):
        if type == Message_IDS.SAT_HEARTBEAT_SUN:
            self.upload_sun(time, data)
        elif type == Message_IDS.SAT_HEARTBEAT_IMU:
            self.upload_imu(time, data)
        elif type == Message_IDS.SAT_HEARTBEAT_BATT:
            self.upload_batt(time, data)

    def upload_sun(self, time, data):
        (sun_x, sun_y, sun_z) = data
        upload = (time, sun_x, sun_y, sun_z)
        sql = "INSERT INTO sun (time, x, y, z) (%s, %s, %s, %s)"
        try:
            self.cursor.execute(sql, upload)
        except Exception as e:
            print(f"[ERROR]: Could not upload sun heartbeat: {e}")

    def upload_batt(self, time, data):
        (batt_soc, current, boot_count) = data
        upload = (time, batt_soc, current, boot_count)
        sql = "INSERT INTO battery (time, batt_soc, current, boot_count)( %s, %s, %s, %s)"
        try:
            self.cursor.execute(sql, upload)
        except Exception as e:
            print(f"[ERROR]: Could not upload battery heartbeat: {e}")

    def upload_imu(self, time, data):
        (mag_x, mag_y, mag_z,
         gyro_x, gyro_y, gyro_z) = data
        upload = (time, mag_x, mag_y, mag_z, gyro_x, gyro_y, gyro_z)
        sql = "INSERT INTO imu (time, mag_x, mag_y, mag_z, gyro_x, gyro_y, gyro_z) (%s, %s, %s, %s, %s, %s)"
        try:
            self.cursor.execute(sql, upload)
        except Exception as e:
            print(f"[ERROR]: Could not upload imu heartbeat: {e}")
