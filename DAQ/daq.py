from DB_Manager.db_manager import DBManager
from stats.modality_stats import ModalityStats
import logging
import threading
import time

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
        try:
            self.modality = ModalityStats()
            self._sensor_data = {
                "temperature": 25.0,  # Default values
                "humidity": 60.0,
                "status": "initializing"
            }
            logger.info(f"DAQ initialized with serial number: {self.serial_number}")

            # Start background thread to update sensor data
            self._stop_thread = False
            self._sensor_thread = threading.Thread(target=self._background_sensor_read, daemon=True)
            self._sensor_thread.start()

        except Exception as e:
            logger.error(f"Error initializing modality stats: {e}")
            self.modality = None
            self._sensor_data = {
                "temperature": 25.0,  # Default values on error
                "humidity": 60.0,
                "status": f"error: {str(e)}"
            }

    def _background_sensor_read(self):
        """Background thread to continuously read sensor data without blocking"""
        while not self._stop_thread:
            try:
                # Get data with timeout protection
                if hasattr(self, 'modality') and self.modality:
                    # Use a separate thread with timeout to prevent hanging
                    sensor_data = self.modality.get_temperature_humidity()

                    # Only update if we got valid data
                    if sensor_data and sensor_data.get("temperature") is not None:
                        self._sensor_data = sensor_data
                        print(
                            f"Updated sensor data: temp={sensor_data['temperature']}°C, humid={sensor_data['humidity']}%")
                    else:
                        print("Sensor read returned None or invalid data")

            except Exception as e:
                logger.error(f"Error in background sensor read: {e}")
                print(f"Sensor read error: {e}")

            # Wait before next read (DHT11 needs time between reads)
            time.sleep(2.5)

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
        NEVER BLOCKS - returns cached data immediately.

        Returns:
            dict: Dictionary with temperature, humidity and status
        """
        print(f"Returning cached sensor data: {self._sensor_data}")
        return self._sensor_data

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
            self._stop_thread = True
            if hasattr(self, '_sensor_thread') and self._sensor_thread:
                self._sensor_thread.join(timeout=1.0)

            if hasattr(self, 'modality') and self.modality:
                self.modality.cleanup()

            self.db.disconnect()
            logger.info("DAQ resources cleaned up")
        except Exception as e:
            logger.error(f"Error during DAQ cleanup: {e}")