import time
import pigpio


class Sensor:
    """
    A class to read temperature and humidity from DHT11 sensor using pigpio library.
    This implementation is compatible with most Raspberry Pi models.
    """

    def __init__(self, gpio=4):
        """
        Initialize the DHT11 sensor on the specified GPIO pin.

        Args:
            gpio: GPIO pin number (BCM numbering, default: 4)
        """
        self.gpio = gpio
        self.temperature = None
        self.humidity = None

        # Initialize the pigpio connection
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Could not connect to pigpio daemon. Is it running?")

        # Set up data structures for reading DHT11
        self.data = []
        self.last_tick = 0
        self.bits = 0
        self.high_tick = 0
        self.either_edge_cb = None

    def _cb(self, gpio, level, tick):
        """
        Callback for GPIO edge changes.

        Args:
            gpio: GPIO pin number
            level: Signal level (0 or 1)
            tick: Time stamp in microseconds
        """
        diff = pigpio.tickDiff(self.last_tick, tick)
        self.last_tick = tick

        if level == 0:  # Falling edge
            if diff > 50:  # Noise filter
                self.high_tick = diff
        else:  # Rising edge
            if diff > 50:  # Noise filter
                if self.bits < 40:
                    self.bits += 1
                    if self.high_tick > 100:  # Long pulse = 1, short pulse = 0
                        self.data.append(1)
                    else:
                        self.data.append(0)

    def read_sensor(self):
        """
        Read temperature and humidity from the DHT11 sensor.

        Returns:
            tuple: (temperature, humidity) or (None, None) if reading fails
        """
        try:
            self.data = []
            self.bits = 0

            # Set the GPIO pin as output and drive it low for at least 18ms
            self.pi.set_mode(self.gpio, pigpio.OUTPUT)
            self.pi.write(self.gpio, 0)
            time.sleep(0.018)

            # Set callback to record rise and fall times
            self.pi.set_mode(self.gpio, pigpio.INPUT)
            self.pi.set_pull_up_down(self.gpio, pigpio.PUD_UP)
            self.last_tick = self.pi.get_current_tick()
            self.either_edge_cb = self.pi.callback(self.gpio, pigpio.EITHER_EDGE, self._cb)

            # Wait for data collection
            time.sleep(0.2)
            self.either_edge_cb.cancel()

            # Process data if enough bits received
            if len(self.data) >= 40:
                # Convert data to bytes
                byte_data = []
                for i in range(0, 40, 8):
                    byte = 0
                    for bit in range(8):
                        byte = (byte << 1) | self.data[i + bit]
                    byte_data.append(byte)

                # Verify checksum
                if byte_data[4] == ((byte_data[0] + byte_data[1] + byte_data[2] + byte_data[3]) & 0xFF):
                    self.humidity = byte_data[0]
                    self.temperature = byte_data[2]
                    return self.temperature, self.humidity

            # Return None values if reading failed
            return None, None

        except Exception as e:
            print(f"Error reading DHT11: {e}")
            return None, None

    def get_temperature(self):
        """Get the last read temperature value in Celsius."""
        return self.temperature

    def get_humidity(self):
        """Get the last read humidity value in percentage."""
        return self.humidity

    def cleanup(self):
        """Clean up resources used by the sensor."""
        if self.either_edge_cb:
            self.either_edge_cb.cancel()
        self.pi.stop()
        print("DHT sensor cleanup complete.")


