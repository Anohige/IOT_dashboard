# dependency_injector.py

# 1) Import your classes
from File_manager.file_manager import FileManager
from connection.mqtt.mqtt_client import MqttClient
from DAQ. daq import DAQ
from connection.server.server import Server
from stats.modality_stats import Sensor
import time
import board
import adafruit_dht


class DependencyInjector:
    """
    This class is responsible for creating and injecting dependencies
    such as MqttClient, FileManager, etc.
    """

    # In dependency_injector.py, modify the constructor

    def __init__(self):
        # 2) Instantiate FileManager
        self.file_manager = FileManager()

        # 3) Instantiate MqttClient, injecting file_manager
        self.mqtt_client = MqttClient(file_manager=self.file_manager)
        self.daq = DAQ()
        self.server = Server()

        # Initialize modality stats last, after other GPIO-using components
        time.sleep(0.5)  # Brief pause to let other initializations settle
        self.mod_stats = Sensor()
    def start_mqtt_client(self):
        """
        Start the MQTT loop (blocking)
        """
        self.mqtt_client.connect_and_loop()
    def start_daq(self):
        """
        Start the DAQ
        """
        print(f"Raspberry Pi Serial: {self.daq.serial_number}")
        self.daq.store_to_db()

    def start_server(self):
        self.server.run()

    def start_modality_stats(self):
        """
        Start fetching sensor stats in the background.
        """
        print("Starting modality stats in background...")
        self.mod_stats.start_fetching()

    def monitor_continuous(interval=2):
        """
        Continuously monitor temperature and humidity (same as original test code).

        Args:
            interval: Time between readings in seconds (default: 2)
        """
        dht_device = adafruit_dht.DHT11(board.D4)
        try:
            while True:
                try:
                    # Read temperature and humidity
                    temperature = dht_device.temperature
                    humidity = dht_device.humidity
                    if temperature is not None and humidity is not None:
                        print(f"Temp: {temperature}°C  Humidity: {humidity}%")
                    else:
                        print("Sensor reading failed, retrying...")
                except RuntimeError as error:
                    print(f"Runtime Error: {error}. Retrying in 2 seconds...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nScript terminated by user.")
        finally:
            dht_device.exit()
            print("DHT sensor cleanup complete.")

