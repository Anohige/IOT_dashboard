from DB_Manager.db_manager import DBManager

class DAQ:
    """
    A class for DAQ operations (e.g., retrieving Raspberry Pi serial number)
    and storing it in the database.
    """

    def __init__(self):
        self.serial_number = self.get_rpi_serial()
        self.db = DBManager()
        self.db.connect()  # Establish DB connection

    def get_rpi_serial(self):
        """
        Reads the Raspberry Pi serial number from /proc/cpuinfo.
        """
        cpuserial = "UNKNOWN"
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('Serial'):
                        parts = line.split(':')
                        if len(parts) == 2:
                            cpuserial = parts[1].strip()
                            break
        except FileNotFoundError:
            print("[DAQ] Warning: /proc/cpuinfo not found. Not running on Raspberry Pi?")
        except Exception as e:
            print(f"[DAQ] Could not read /proc/cpuinfo: {e}")
        return cpuserial

    def store_to_db(self):
        """
        Checks whether the Raspberry Pi serial exists in `iot_devices`.
        If not, inserts a new entry.
        """
        if self.serial_number == "UNKNOWN":
            print("[DAQ] Pi serial is 'UNKNOWN'. Skipping DB insertion.")
            return

        # Check if serial exists
        query = "SELECT COUNT(*) AS count FROM iot_devices WHERE device_serial = %s"
        result = self.db.execute_query(query, (self.serial_number,), fetch=True)
        count = result[0]["count"] if result else 0

        if count > 0:
            print(f"[DAQ] Pi serial '{self.serial_number}' already exists in DB. Skipping insertion.")
        else:
            # Insert new entry
            query = "INSERT INTO iot_devices (device_serial) VALUES (%s)"
            self.db.execute_query(query, (self.serial_number,))
            print(f"[DAQ] Inserted Pi serial '{self.serial_number}' into the database.")

        # Do not close DB connection here, let it persist for reuse