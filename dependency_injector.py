# dependency_injector.py

# 1) Import your classes
from File_manager.file_manager import FileManager
from connection.mqtt.mqtt_client import MqttClient
from DAQ. daq import DAQ
from connection.server.server import Server

class DependencyInjector:
    """
    This class is responsible for creating and injecting dependencies
    such as MqttClient, FileManager, etc.
    """
    def __init__(self):
        # 2) Instantiate FileManager
        self.file_manager = FileManager()

        # 3) Instantiate MqttClient, injecting file_manager
        self.mqtt_client = MqttClient(file_manager=self.file_manager)
        self.daq = DAQ()
        self.server = Server()

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