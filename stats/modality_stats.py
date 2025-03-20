# stats/modality_stats.py

import RPi.GPIO as GPIO
import adafruit_dht
import board
import time
import threading


class Modality_stats:
    def __init__(self):
        # Clean up any existing GPIO setups to avoid conflicts
        try:
            GPIO.cleanup()
        except:
            pass

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # Use a slight delay before initializing the DHT device
        time.sleep(0.5)

        # Initialize the DHT device
        self.device = adafruit_dht.DHT11(board.D4)

        # This event will let us stop the loop gracefully
        self.stop_event = threading.Event()

        # Flag to track if we're currently fetching
        self.is_fetching = False

    def start_fetching(self):
        """
        Start the temperature/humidity fetching in a background thread.
        """
        if self.is_fetching:
            print("Already fetching stats!")
            return

        print("Initializing DHT11 sensor...")
        self.is_fetching = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._fetch_loop, daemon=True)
        self.thread.start()

    def _fetch_loop(self):
        """
        Continuously fetch stats until stop_event is set.
        """
        # Give the sensor a moment to stabilize
        time.sleep(1)

        while not self.stop_event.is_set():
            try:
                temperature = self.device.temperature
                humidity = self.device.humidity
                print(f"Temp: {temperature}C Humidity: {humidity}%")
            except RuntimeError as error:
                print(f"DHT11 Error: {error}")
            except Exception as e:
                print(f"Unexpected error with DHT11: {e}")

            # Wait between readings
            time.sleep(2)

    def stop_fetching(self):
        """
        Signal the loop to stop, then join the thread.
        """
        if not self.is_fetching:
            print("Not currently fetching stats!")
            return

        print("Stopping modality stats...")
        self.stop_event.set()

        if hasattr(self, 'thread'):
            self.thread.join(timeout=3)  # Wait up to 3 seconds

        # Clean up GPIO
        try:
            GPIO.cleanup()
        except:
            pass

        self.is_fetching = False
        print("Modality stats fetching stopped.")