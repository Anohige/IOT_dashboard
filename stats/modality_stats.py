import RPi.GPIO as GPIO
import adafruit_dht
import board
import time

class Modality_stats:
    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        self.device = adafruit_dht.DHT11(board.D4)
        self.fetch_stats()

    def fetch_stats(self):
        try:
            while True:
                self.temperature = self.device.read_temperature()
                self.humidity = self.device.read_humidity()
                print(F"Temperature: {self.temperature} C Humidity: {self.humidity}%")
                time.sleep(1)
        except RuntimeError as e:
            print(e)




