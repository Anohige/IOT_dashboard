import RPi.GPIO as GPIO
import adafruit_dht
import board
import time

class Modality_stats:
    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        self.device = adafruit_dht.DHT11(board.D4)

    def fetch_stats(self):
        # try:
        #     while True:
        #         self.temperature = self.device.temperature()
        #         self.humidity = self.device.humidity()
        #         print(F"Temperature: {self.temperature} C Humidity: {self.humidity}%")
        #         time.sleep(1)
        # except RuntimeError as e:
        #     print(e)
        #
        while True:
            try:
                temperature = self.device.temperature()
                humidity = self.device.humidity()
                print(F"Temperature: {temperature} C Humidity: {humidity}%")
            except RuntimeError as e:
                print(e)

            time.sleep(1)