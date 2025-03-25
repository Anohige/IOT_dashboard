import pigpio
import time
import math


class DHT11Sensor:
    """
    DHT11 sensor implementation using pigpio library.
    """

    def __init__(self, pin=4):
        """
        Initialize the DHT11 sensor.

        Args:
            pin: The GPIO pin number the sensor is connected to.
        """
        self.pin = pin
        self.pi = pigpio.pi()
        self.temperature = None
        self.humidity = None

        # Verify pigpio connection
        if not self.pi.connected:
            raise RuntimeError("Failed to connect to pigpio. Is the pigpio daemon running?")

    def read_sensor(self, max_attempts=5):
        """
        Read temperature and humidity data from the sensor.

        Returns:
            tuple: (temperature, humidity) or (None, None) if reading fails
        """
        for attempt in range(max_attempts):
            try:
                # Prepare for reading
                self.pi.set_mode(self.pin, pigpio.OUTPUT)
                self.pi.write(self.pin, 1)
                time.sleep(0.05)
                self.pi.write(self.pin, 0)
                time.sleep(0.02)
                self.pi.write(self.pin, 1)
                self.pi.set_mode(self.pin, pigpio.INPUT)

                # Wait for response
                start_time = time.time()
                while self.pi.read(self.pin) == 1:
                    if time.time() - start_time > 0.1:
                        break

                # Collect data pulses
                data = []
                for _ in range(40):
                    # Wait for low pulse
                    while self.pi.read(self.pin) == 0:
                        pass

                    # Measure high pulse duration
                    start = time.time()
                    while self.pi.read(self.pin) == 1:
                        pass
                    duration = time.time() - start

                    # Determine bit value based on pulse duration
                    data.append(1 if duration > 0.0001 else 0)

                # Convert bit stream to bytes
                humidity_high = int(''.join(map(str, data[0:8])), 2)
                humidity_low = int(''.join(map(str, data[8:16])), 2)
                temperature_high = int(''.join(map(str, data[16:24])), 2)
                temperature_low = int(''.join(map(str, data[24:32])), 2)
                checksum = int(''.join(map(str, data[32:40])), 2)

                # Verify checksum
                calculated_sum = (humidity_high + humidity_low +
                                  temperature_high + temperature_low) & 0xFF

                if calculated_sum == checksum:
                    # Handle temperature sign (for DHT11 this is usually positive)
                    temperature = temperature_high

                    self.temperature = temperature
                    self.humidity = humidity_high

                    return self.temperature, self.humidity

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(1)

        return None, None

    def get_temperature(self):
        """Get the last read temperature value in Celsius."""
        return self.temperature

    def get_humidity(self):
        """Get the last read humidity value in percentage."""
        return self.humidity

    def close(self):
        """Close the pigpio connection."""
        self.pi.stop()