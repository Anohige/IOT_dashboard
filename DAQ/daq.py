import pymysql
import uuid

class daq:
    """
    A simple class for data acquisition (DAQ) operations,
    here focusing on retrieving the Raspberry Pi serial number
    and storing it in a database along with a unique ID.
    """

    def __init__(self):
        self.serial_number = self.get_rpi_serial()
        self.host = ""
        self.user = ""
        self.password = ""
        self.database = ""
        self.port = 3306

    def get_rpi_serial(self):
        """
        Attempt to read the Raspberry Pi serial from /proc/cpuinfo.
        Returns a string. If not on a Pi or any error occurs, returns 'UNKNOWN'.
        """
        cpuserial = "UNKNOWN"
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('Serial'):
                        # Typically looks like: "Serial  : 00000000xxxxxxx"
                        parts = line.split(':')
                        if len(parts) == 2:
                            cpuserial = parts[1].strip()
                            break
        except Exception as e:
            print(f"[DAQ] Could not read /proc/cpuinfo: {e}")
        return cpuserial

    def store_to_db(self):
        """
        If self.serial_number is not 'UNKNOWN', checks whether this serial
        already exists in the iot_devices table. If it does not exist, inserts
        a new row with a unique_id and the pi_serial. Otherwise, skips insertion.
        """
        # 1) If we have no valid serial, skip insertion
        if self.serial_number == "UNKNOWN":
            print("[DAQ] Pi serial is 'UNKNOWN'. Skipping DB insertion.")
            return

        try:
            # 2) Connect using PyMySQL
            connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port
            )

            with connection.cursor() as cursor:
                # 3) Check if this serial already exists
                select_query = """
                    SELECT COUNT(*)
                    FROM iot_devices
                    WHERE pi_serial = %s
                """
                cursor.execute(select_query, (self.serial_number,))
                (count,) = cursor.fetchone()

                if count > 0:
                    # Already in DB, skip insertion
                    print(f"[DAQ] Pi serial '{self.serial_number}' already exists in DB. Skipping insertion.")
                else:
                    # Not in DB, insert new row
                    unique_id = f"dev_{uuid.uuid4()}"
                    insert_query = """
                        INSERT INTO iot_devices (unique_id, pi_serial)
                        VALUES (%s, %s)
                    """
                    cursor.execute(insert_query, (unique_id, self.serial_number))
                    connection.commit()

                    print(f"[DAQ] Inserted Pi serial '{self.serial_number}'")
                    print(f"       with unique ID '{unique_id}' into the DB.")

        except pymysql.MySQLError as e:
            print(f"[DAQ] MySQL error: {e}")
        except Exception as ex:
            print(f"[DAQ] Unexpected error: {ex}")
        finally:
            if 'connection' in locals() and connection:
                connection.close()
                print("[DAQ] Database connection closed.")