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
        """
        Start fetching sensor stats in the background.
        """
        try:
            # Try different pin specifications if your default isn't working
            # Option 1: Use default
            sensor = DHT11Sensor()

            # If that fails, you might need to specify the pin number explicitly
            # Uncomment one of these alternatives:
            # sensor = DHT11Sensor(pin_number=4)  # For GPIO4
            # sensor = DHT11Sensor(pin_number=17)  # Common alternative pin

            print("DHT11 sensor initialized successfully")
        except Exception as e:
            print(f"Failed to initialize sensor: {e}")
            print("Try running with sudo if this is a permission issue")
            print("Or ensure no other process is using the GPIO pin")
            sys.exit(1)

        try:
            while True:
                # Read temperature and humidity
                temperature, humidity = sensor.read_sensor()

                if temperature is not None and humidity is not None:
                    print(f"Temperature: {temperature}°C")
                    print(f"Humidity: {humidity}%")
                else:
                    print("Failed to read from DHT11 sensor!")

                # Wait before next reading
                time.sleep(5)

        except KeyboardInterrupt:
            # Clean up when user terminates program
            print("Program terminated by user")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            sensor.close()
            print("Sensor closed")
