from DB_Manager.db_manager import DBManager
from stats.modality_stats import ModalityStats
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


class DAQ:
    """
    A class for DAQ operations (e.g., retrieving Raspberry Pi serial number)
    and storing it in the database.
    """

    def __init__(self):
        self.serial_number = self.get_rpi_serial()
        self.db = DBManager()
        self.db.connect()  # Establish DB connection
        # Initialize the modality stats (sensor interface)
        self.modality = ModalityStats()
        logger.info(f"DAQ initialized with serial number: {self.serial_number}")

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
            logger.warning("/proc/cpuinfo not found. Not running on Raspberry Pi?")
        except Exception as e:
            logger.error(f"Could not read /proc/cpuinfo: {e}")
        return cpuserial

    def get_sensor_data(self):
        """
        Get the latest temperature and humidity readings from the sensor.

        Returns:
            dict: Dictionary with temperature, humidity and status
        """
        logger.debug("Fetching sensor data")
        return self.modality.get_temperature_humidity()

    def store_to_db(self):
        """
        Checks whether the Raspberry Pi serial exists in `iot_devices`.
        If not, inserts a new entry.
        """
        if self.serial_number == "UNKNOWN":
            logger.warning("Pi serial is 'UNKNOWN'. Skipping DB insertion.")
            return

        # Check if serial exists
        query = "SELECT COUNT(*) AS count FROM iot_devices WHERE device_serial = %s"
        result = self.db.execute_query(query, (self.serial_number,), fetch=True)
        count = result[0]["count"] if result else 0

        if count > 0:
            logger.info(f"Pi serial '{self.serial_number}' already exists in DB. Skipping insertion.")
        else:
            # Insert new entry
            query = "INSERT INTO iot_devices (device_serial) VALUES (%s)"
            self.db.execute_query(query, (self.serial_number,))
            logger.info(f"Inserted Pi serial '{self.serial_number}' into the database.")

        # Do not close DB connection here, let it persist for reuse

    def cleanup(self):
        """Release resources when done."""
        try:
            self.modality.cleanup()
            self.db.disconnect()
            logger.info("DAQ resources cleaned up")
        except Exception as e:
            logger.error(f"Error during DAQ cleanup: {e}")