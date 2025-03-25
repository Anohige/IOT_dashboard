import time
import gpiozero
import Adafruit_DHT


class DHT11Sensor:
    """
    DHT11 sensor implementation using gpiozero and Adafruit_DHT libraries.
    """

    def __init__(self, pin=4):
        """
        Initialize the DHT11 sensor.

        Args:
            pin: The GPIO pin number (BCM mode) the sensor is connected to.
        """
        self.pin = pin
        self.humidity = None
        self.temperature = None
        self.sensor_type = Adafruit_DHT.DHT11

    def read_sensor(self, max_attempts=5):
        """
        Read temperature and humidity data from the sensor.

        Returns:
            tuple: (temperature, humidity) or (None, None) if reading fails
        """
        for _ in range(max_attempts):
            try:
                # Use Adafruit_DHT library for reading (more reliable)
                humidity, temperature = Adafruit_DHT.read_retry(self.sensor_type, self.pin)

                if humidity is not None and temperature is not None:
                    self.humidity = humidity
                    self.temperature = temperature
                    return self.temperature, self.humidity

                # Small delay between attempts
                time.sleep(0.5)

            except Exception as e:
                print(f"Error reading sensor: {e}")
                time.sleep(0.5)

        return None, None

    def get_temperature(self):
        """Get the last read temperature value in Celsius."""
        return self.temperature

    def get_humidity(self):
        """Get the last read humidity value in percentage."""
        return self.humidity