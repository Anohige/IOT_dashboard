# dependency_injector.py

import time
from File_manager.file_manager import FileManager
from connection.mqtt.mqtt_client import MqttClient
from DAQ.daq import DAQ
from connection.server.server import Server


class DependencyInjector:
    """
    Creates and wires together:
      - DAQ
      - FileManager
      - MqttClient
      - Server
    """

    def __init__(self):
        # 1) Bring up your DAQ first so you have a Pi serial (if you need it)
        self.daq = DAQ()
        print(f"DAQ initialized. Serial = {self.daq.serial_number}")

        # 2) FileManager (it will learn serial on first incoming rule)
        self.file_manager = FileManager()

        # 3) MQTT client: inject both your FileManager *and* the Pi serial
        #    so that stats and rules both carry the correct device_serial
        self.mqtt_client = MqttClient(
            device_serial=self.daq.get_rpi_serial(),
            file_manager=self.file_manager,
        )

        # 4) HTTP or WebSocket server, etc.
        self.server = Server()

        # give GPIO or other hardware a moment
        time.sleep(0.5)

    def start_mqtt_client(self):
        """Connect and start the MQTT background loop."""
        self.mqtt_client.connect_and_loop()

    def start_daq(self):
        """Begin any DAQ logic (e.g. persistence)."""
        self.daq.store_to_db()

    def start_server(self):
        """Launch your server (blocking)."""
        self.server.run()