# dependency_injector.py
import sys

# 1) Import your classes
from File_manager.file_manager import FileManager
from connection.mqtt.mqtt_client import MqttClient
from DAQ. daq import DAQ
from connection.server.server import Server
from stats.modality_stats import DHT11Sensor
import time


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
        # Try different GPIO pins if one doesn't work
        pins_to_try = [4, 17, 22, 23]
        sensor = None

        # Try each pin until one works
        for pin in pins_to_try:
            try:
                print(f"Trying DHT11 on GPIO pin {pin}...")
                sensor = DHT11Sensor(pin=pin)

                # Test if sensor works
                temperature, humidity = sensor.read_sensor()
                if temperature is not None and humidity is not None:
                    print(f"Success! DHT11 found on GPIO pin {pin}")
                    break
                else:
                    print(f"Failed to read from DHT11 on GPIO pin {pin}")
                    sensor = None
            except Exception as e:
                print(f"Error with GPIO pin {pin}: {e}")

        if sensor is None:
            print("Could not initialize DHT11 sensor on any pin. Check connections and try again.")
            sys.exit(1)

        print(f"DHT11 sensor initialized successfully on GPIO pin {sensor.pin}")
        print("Starting sensor readings...")

        try:
            while True:
                temperature, humidity = sensor.read_sensor()

                if temperature is not None and humidity is not None:
                    print(f"Temperature: {temperature}°C")
                    print(f"Humidity: {humidity}%")
                else:
                    print("Failed to read sensor data")

                # Wait before next reading
                time.sleep(5)

        except KeyboardInterrupt:
            print("\nProgram terminated by user")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
