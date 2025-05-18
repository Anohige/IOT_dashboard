import time
import board
import adafruit_dht
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


class ModalityStats:
    """
    A class for reading temperature and humidity data from a DHT11/DHT22 sensor.
    """

    def __init__(self, pin=board.D4, sensor_type="DHT11"):
        """
        Initialize the DHT sensor.

        Args:
            pin: The GPIO pin (default board.D4)
            sensor_type: Type of DHT sensor ("DHT11" or "DHT22")
        """
        self.pin = pin
        self.sensor_type = sensor_type

        # Initialize the appropriate sensor
        if sensor_type == "DHT11":
            self.dht_device = adafruit_dht.DHT11(pin)
        elif sensor_type == "DHT22":
            self.dht_device = adafruit_dht.DHT22(pin)
        else:
            raise ValueError(f"Unsupported sensor type: {sensor_type}")

        logger.info(f"Initialized {sensor_type} sensor on pin {pin}")

    def get_temperature_humidity(self):
        """
        Get temperature and humidity data from the sensor.

        Returns:
            dict: Dictionary containing temperature and humidity data
        """
        data = {
            "temperature": None,
            "humidity": None,
            "status": "error"
        }

        try:
            temperature = self.dht_device.temperature
            humidity = self.dht_device.humidity

            if temperature is not None and humidity is not None:
                data["temperature"] = float(f"{temperature:.1f}")
                data["humidity"] = float(f"{humidity:.1f}")
                data["status"] = "ok"
                logger.debug(f"Read sensor data: Temp={temperature:.1f}°C, Humidity={humidity:.1f}%")
            else:
                logger.warning("Sensor returned None values")

        except RuntimeError as e:
            # Common errors like reading too frequently
            logger.warning(f"DHT sensor runtime error: {e}")
            data["status"] = f"error: {str(e)}"
        except Exception as e:
            logger.error(f"Error reading from DHT sensor: {e}")
            data["status"] = f"error: {str(e)}"

        return data

    def cleanup(self):
        """Clean up resources when done using the sensor."""
        try:
            self.dht_device.exit()
            logger.info("DHT sensor resources released")
        except Exception as e:
            logger.error(f"Error cleaning up DHT sensor: {e}")

    def __del__(self):
        """Destructor to ensure cleanup when object is garbage collected."""
        self.cleanup()