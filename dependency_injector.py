# dependency_injector.py

import os
import sys

# 1) Import your classes
from File_manager.file_manager import FileManager
from mqtt.mqtt_client import MqttClient

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

    def start_mqtt_client(self):
        """
        Start the MQTT loop (blocking)
        """
        self.mqtt_client.connect_and_loop()