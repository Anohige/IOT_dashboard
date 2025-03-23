import time
import board
import adafruit_dht


class Sensor:
    """
    A minimal wrapper around the working DHT11 code that allows it to be imported
    and used by other modules without changing the core functionality.
    """

    def __init__(self, pin=board.D4):
        """
        Initialize the DHT11 sensor with the same parameters as your working code.

        Args:
            pin: The pin where DHT11 is connected (default: board.D4)
        """
        self.dht_device = adafruit_dht.DHT11(pin)
        self.temperature = None
        self.humidity = None

    def read_single(self):
        """
        Read temperature and humidity once.

        Returns:
            tuple: (temperature, humidity) or (None, None) if reading fails
        """
        try:
            # Read temperature and humidity (exactly as in your working code)
            self.temperature = self.dht_device.temperature
            self.humidity = self.dht_device.humidity

            if self.temperature is not None and self.humidity is not None:
                return self.temperature, self.humidity
            return None, None
        except RuntimeError as error:
            print(f"Runtime Error: {error}")
            return None, None

    def get_temperature(self):
        """Get the last successfully read temperature."""
        return self.temperature

    def get_humidity(self):
        """Get the last successfully read humidity."""
        return self.humidity

    def cleanup(self):
        """Clean up the sensor resources."""
        self.dht_device.exit()
        print("DHT sensor cleanup complete.")
