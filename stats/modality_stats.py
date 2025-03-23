import time
import RPi.GPIO as GPIO


class Sensor:
    """
    DHT11 sensor result returned by DHT11.read() method
    """
    ERR_NO_ERROR = 0
    ERR_MISSING_DATA = 1
    ERR_CRC = 2

    error_code = ERR_NO_ERROR
    temperature = -1
    humidity = -1

    def __init__(self, error_code, temperature, humidity):
        self.error_code = error_code
        self.temperature = temperature
        self.humidity = humidity

    def is_valid(self):
        return self.error_code == DHT11Result.ERR_NO_ERROR


class DHT11Sensor:
    """
    DHT11 sensor interface using RPi.GPIO directly
    """

    def __init__(self, pin=4):
        """
        Initialize DHT11 sensor.

        Args:
            pin: GPIO pin number (BCM mode) where the DHT11 is connected
        """
        self.pin = pin
        self.temperature = None
        self.humidity = None

        # Initialize GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)

    def read_sensor(self):
        """
        Read DHT11 sensor data.

        Returns:
            tuple: (temperature, humidity) or (None, None) if reading fails
        """
        # Send initial signal
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(self.pin, GPIO.LOW)
        time.sleep(0.02)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Collect data
        data = self._collect_input()

        # Parse data
        if len(data) < 40:
            return None, None

        # Calculate humidity and temperature
        result = self._parse_data(data)

        if result.is_valid():
            self.temperature = result.temperature
            self.humidity = result.humidity
            return self.temperature, self.humidity

        return None, None

    def _collect_input(self):
        """
        Collect bit sequence from DHT11
        """
        MAX_UNCHANGED_COUNT = 100
        unchanged_count = 0
        data = []

        # Initial state
        last = -1
        while True:
            current = GPIO.input(self.pin)
            data.append(current)

            # Detect unchanged sequence length
            if last != current:
                unchanged_count = 0
                last = current
            else:
                unchanged_count += 1
                if unchanged_count > MAX_UNCHANGED_COUNT:
                    break

        return data

    def _parse_data(self, data):
        """
        Parse bit sequence to derive humidity and temperature
        """
        # Find initial state change after initial pulldown
        STATE_INIT_PULL_DOWN = 1
        STATE_INIT_PULL_UP = 2
        STATE_DATA_FIRST_PULL_DOWN = 3
        STATE_DATA_PULL_UP = 4
        STATE_DATA_PULL_DOWN = 5

        state = STATE_INIT_PULL_DOWN

        # Adjusted values for bit length and signal transitions
        lengths = []
        current_length = 0

        for i in range(len(data)):
            current = data[i]
            current_length += 1

            if state == STATE_INIT_PULL_DOWN:
                if current == GPIO.LOW:
                    state = STATE_INIT_PULL_UP
                    continue
            elif state == STATE_INIT_PULL_UP:
                if current == GPIO.HIGH:
                    state = STATE_DATA_FIRST_PULL_DOWN
                    continue
            elif state == STATE_DATA_FIRST_PULL_DOWN:
                if current == GPIO.LOW:
                    state = STATE_DATA_PULL_UP
                    continue
            elif state == STATE_DATA_PULL_UP:
                if current == GPIO.HIGH:
                    current_length = 0
                    state = STATE_DATA_PULL_DOWN
                    continue
            elif state == STATE_DATA_PULL_DOWN:
                if current == GPIO.LOW:
                    lengths.append(current_length)
                    state = STATE_DATA_PULL_UP
                    continue

        if len(lengths) != 40:
            return DHT11Result(DHT11Result.ERR_MISSING_DATA, -1, -1)

        # Process bit sequence to bytes
        threshold = sum(lengths) / len(lengths)
        bits = []
        for length in lengths:
            bit = 0
            if length > threshold:
                bit = 1
            bits.append(bit)

        # Byte conversion
        result_bytes = []
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits):
                    byte = (byte << 1) | bits[i + j]
            result_bytes.append(byte)

        # Verify checksum
        if len(result_bytes) != 5 or result_bytes[4] != (
                (result_bytes[0] + result_bytes[1] + result_bytes[2] + result_bytes[3]) & 0xFF):
            return DHT11Result(DHT11Result.ERR_CRC, -1, -1)

        return DHT11Result(DHT11Result.ERR_NO_ERROR, result_bytes[2], result_bytes[0])

    def get_temperature(self):
        """Get the last read temperature value in Celsius."""
        return self.temperature

    def get_humidity(self):
        """Get the last read humidity value in percentage."""
        return self.humidity

    def cleanup(self):
        """Clean up GPIO resources."""
        GPIO.cleanup(self.pin)
        print("DHT sensor cleanup complete.")
