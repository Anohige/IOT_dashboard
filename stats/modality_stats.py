import time
import board
import adafruit_dht
import os
import atexit

class DHT11Sensor:
    """
    A class to interface with the DHT11 temperature and humidity sensor.
    Requires the Adafruit_CircuitPython_DHT library.
    """

    def __init__(self, pin=board.D17, pin_number=None):
        """
        Initialize the DHT11 sensor interface.

        Args:
            pin: The GPIO pin the sensor is connected to. Default is board.D17.
            pin_number: Alternative way to specify pin by number (e.g., 17 for GPIO17)
        """
        self.pin = pin
        self.pin_number = pin_number if pin_number is not None else 17
        self.last_read_time = 0
        self.temperature = None
        self.humidity = None
        self._initialize_sensor()
        # Register the cleanup to run when the program exits
        atexit.register(self.close)

    def _initialize_sensor(self):
        """Initialize the DHT11 sensor."""
        try:
            self.dht_device = adafruit_dht.DHT11(self.pin, use_pulseio=False)
        except Exception as e:
            print(f"Error initializing DHT11: {e}")
            print("Attempting cleanup and retry...")
            try:
                os.system(f"gpio unexport {self.pin_number}")
                time.sleep(1)
                self.dht_device = adafruit_dht.DHT11(self.pin, use_pulseio=False)
            except Exception as e2:
                raise RuntimeError(f"Failed to initialize DHT11 after cleanup: {e2}")

    def read_sensor(self, max_retries=5):
        """
        Read temperature and humidity data from the sensor.

        Args:
            max_retries: Maximum number of retries if reading fails

        Returns:
            tuple: (temperature, humidity) or (None, None) if reading fails
        """
        current_time = time.time()
        # Ensure at least 2 seconds between sensor reads
        if current_time - self.last_read_time < 2.0:
            time.sleep(2.0 - (current_time - self.last_read_time))

        retries = 0
        while retries < max_retries:
            try:
                self.temperature = self.dht_device.temperature
                self.humidity = self.dht_device.humidity
                self.last_read_time = time.time()
                return self.temperature, self.humidity
            except RuntimeError as e:
                print(f"RuntimeError: {e}. Retrying...")
                retries += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"Critical error reading sensor: {e}")
                # Reinitialize sensor on critical errors
                self._initialize_sensor()
                retries += 1
                time.sleep(0.5)
        return None, None

    def close(self):
        """Clean up the DHT device."""
        try:
            self.dht_device.exit()
            print("DHT11 sensor cleanup successful.")
        except Exception as e:
            print(f"Error during sensor cleanup: {e}")