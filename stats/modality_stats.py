import time
import RPi.GPIO as GPIO


class Sensor:
    def __init__(self, pin=4):  # Using GPIO 4 (BCM numbering)
        """
        Initialize a DHT11 temperature and humidity sensor using RPi.GPIO.

        Args:
            pin: The GPIO pin number in BCM mode where the sensor is connected (default: 4)
        """
        self.pin = pin
        self.temperature = None
        self.humidity = None

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)

    def read_dht11_dat(self):
        """
        Read raw data from DHT11 sensor using RPi.GPIO.
        This is a more direct implementation that doesn't rely on Adafruit libraries.

        Returns:
            tuple: (humidity, temperature) or (None, None) if reading fails
        """
        # Initialize variables
        humidity = 0
        temperature = 0
        data = [0] * 40

        # Pull down to start signal
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)
        time.sleep(0.018)  # Wait at least 18ms

        # Pull up and wait for sensor response
        GPIO.output(self.pin, GPIO.HIGH)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Wait for sensor response
        count = 0
        while GPIO.input(self.pin) == GPIO.HIGH:
            count += 1
            if count > 100:
                return None, None  # Timeout waiting for response

        # Sensor pulls low for 80μs
        count = 0
        while GPIO.input(self.pin) == GPIO.LOW:
            count += 1
            if count > 100:
                return None, None

        # Sensor pulls high for 80μs
        count = 0
        while GPIO.input(self.pin) == GPIO.HIGH:
            count += 1
            if count > 100:
                return None, None

        # Read 40 bits of data
        for i in range(40):
            # Each bit starts with a 50μs low
            count = 0
            while GPIO.input(self.pin) == GPIO.LOW:
                count += 1
                if count > 100:
                    return None, None

            # Length of high signal determines bit value
            count = 0
            start = time.time()
            while GPIO.input(self.pin) == GPIO.HIGH:
                count += 1
                if count > 100:
                    break

            # If high pulse is longer than 30μs, it's a 1
            if (time.time() - start) > 0.00003:
                data[i] = 1

        # Convert data to humidity and temperature values
        humidity_high = sum(data[0:8])
        humidity_low = sum(data[i] * 2 ** (7 - i) for i in range(8, 16))
        temperature_high = sum(data[i] * 2 ** (7 - i) for i in range(16, 24))
        temperature_low = sum(data[i] * 2 ** (7 - i) for i in range(24, 32))
        checksum = sum(data[i] * 2 ** (7 - i) for i in range(32, 40))

        # Verify checksum
        if checksum == ((humidity_high + humidity_low + temperature_high + temperature_low) & 0xFF):
            humidity = humidity_high + humidity_low / 10.0
            temperature = temperature_high + temperature_low / 10.0
            return humidity, temperature
        else:
            return None, None

    def read_sensor(self):
        """
        Read temperature and humidity from the DHT11 sensor.

        Returns:
            tuple: (temperature, humidity) or (None, None) if reading fails
        """
        try:
            humidity, temperature = self.read_dht11_dat()
            if humidity is not None and temperature is not None:
                self.humidity = humidity
                self.temperature = temperature
                return temperature, humidity
            return None, None
        except Exception as e:
            print(f"Error reading sensor: {e}")
            return None, None

    def get_temperature(self):
        """Get the last read temperature value in Celsius."""
        return self.temperature

    def get_humidity(self):
        """Get the last read humidity value in percentage."""
        return self.humidity

    def cleanup(self):
        """Clean up the GPIO resources."""
        GPIO.cleanup(self.pin)
        print("DHT sensor cleanup complete.")
