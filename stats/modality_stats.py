import time
import board
import adafruit_dht


class Sensor:
    def __init__(self, pin=board.D4):
        """
        Initialize a DHT11 temperature and humidity sensor.

        Args:
            pin: The GPIO pin where the sensor is connected (default: board.D4)
        """
        self.dht_device = adafruit_dht.DHT11(pin)
        self.temperature = None
        self.humidity = None

    def read_sensor(self):
        """
        Read temperature and humidity from the DHT11 sensor.

        Returns:
            tuple: (temperature, humidity) or (None, None) if reading fails
        """
        try:
            self.temperature = self.dht_device.temperature
            self.humidity = self.dht_device.humidity
            return self.temperature, self.humidity
        except RuntimeError as error:
            print(f"Runtime Error: {error}")
            return None, None

    def get_temperature(self):
        """Get the last read temperature value in Celsius."""
        return self.temperature

    def get_humidity(self):
        """Get the last read humidity value in percentage."""
        return self.humidity

    def cleanup(self):
        """Clean up the sensor resources."""
        self.dht_device.exit()
        print("DHT sensor cleanup complete.")


# Example of using the class in a continuous monitoring loop
