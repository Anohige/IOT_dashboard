# stats/modality_stats.py

import RPi.GPIO as GPIO
import adafruit_dht
import board
import time
import threading

class Modality_stats:
    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        self.device = adafruit_dht.DHT11(board.D4)

        # This event will let us stop the loop gracefully
        self.stop_event = threading.Event()

    def start_fetching(self):
        """
        Start the temperature/humidity fetching in a background thread.
        """
        self.thread = threading.Thread(target=self._fetch_loop, daemon=True)
        self.thread.start()

    def _fetch_loop(self):
        """
        Continuously fetch stats until stop_event is set.
        """
        while not self.stop_event.is_set():
            try:
                temperature = self.device.temperature
                humidity = self.device.humidity
                print(f"Temperature: {temperature} C | Humidity: {humidity}")
            except RuntimeError as e:
                # DHT11 often throws read errors if polled too quickly or on bad reads
                print(f"DHT11 Error: {e}")

            time.sleep(1)  # Wait 1 second before the next read

    def stop_fetching(self):
        """
        Signal the loop to stop, then join the thread.
        """
        self.stop_event.set()
        if hasattr(self, 'thread'):
            self.thread.join()
        print("Modality stats fetching stopped.")