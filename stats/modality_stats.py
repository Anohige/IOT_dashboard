import time
import board
import adafruit_dht
import os


class DHT11Sensor:
    """
    A class to interface with the DHT11 temperature and humidity sensor.
    Requires the Adafruit_CircuitPython_DHT library.
    """

    def __init__(self, pin=board.D4, pin_number=None):
        """
        Initialize the DHT11 sensor.

        Args:
            pin: The GPIO pin the sensor is connected to. Default is D4.
            pin_number: Alternative way to specify pin by number (e.g., 4 for D4)
        """
        # Use pin_number if provided, otherwise use the board pin
        if pin_number is not None:
            if hasattr(board, f"D{pin_number}"):
                pin = getattr(board, f"D{pin_number}")
            else:
                # Some platforms might need a different approach
                pin = pin_number

        try:
            # Try creating the device with use_pulseio=False
            self.dht_device = adafruit_dht.DHT11(pin, use_pulseio=False)
        except Exception as e:
            print(f"Error initializing DHT11: {e}")
            print("Attempting cleanup and retry...")
            # Try to release the GPIO before retrying
            try:
                # Force release GPIO if possible
                os.system(f"gpio unexport {pin_number if pin_number is not None else 4}")
                time.sleep(1)
                self.dht_device = adafruit_dht.DHT11(pin, use_pulseio=False)
            except Exception as e2:
                raise RuntimeError(f"Failed to initialize DHT11 after cleanup: {e2}")

        self.temperature = None
        self.humidity = None
        self.last_read_time = 0

    def read_sensor(self, max_retries=15):
        """
        Read temperature and humidity data from the sensor.

        Args:
            max_retries: Maximum number of retries if reading fails

        Returns:
            tuple: (temperature, humidity) or (None, None) if reading fails
        """
        # DHT11 needs at least 2 seconds between readings
        current_time = time.time()
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
                # DHT11 sometimes has reading errors, so we retry
                retries += 1
                time.sleep(0.5)
                continue
            except Exception as e:
                # Non-reading errors should be raised
                print(f"Critical error reading sensor: {e}")
                try:
                    self.dht_device.exit()
                except:
                    pass
                raise e

        # If we get here, all retries failed
        return None, None

    def get_temperature(self):
        """Get the last read temperature value in Celsius."""
        return self.temperature

    def get_humidity(self):
        """Get the last read humidity value in percentage."""
        return self.humidity

    def close(self):
        """Clean up the DHT device."""
        try:
            self.dht_device.exit()
        except:
            pass  # Ignore errors on cleanup