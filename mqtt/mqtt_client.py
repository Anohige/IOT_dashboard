# mqtt_client.py

import json
import paho.mqtt.client as paho_mqtt
import sys
import os

# If you have your FileManager in another directory, adjust the import accordingly
# or use a dependency injection approach.
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from File_manager.file_manager import FileManager

class MqttClient:
    """
    A class to manage MQTT connection and subscriptions.
    """
    def __init__(
        self,
        file_manager=None,
        broker="broker.hivemq.com",
        port=1883,
        rules_topic="iot/rules/updated"
    ):
        """
        :param file_manager: An instance of FileManager (injected).
        :param broker: MQTT broker address
        :param port: MQTT broker port
        :param rules_topic: Topic to receive new rules
        """
        self.broker = broker
        self.port = port
        self.rules_topic = rules_topic

        # Instantiate Paho MQTT Client
        self.client = paho_mqtt.Client()

        # Bind event callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Injected FileManager or create your own
        self.file_manager = file_manager if file_manager else FileManager()

    def connect_and_loop(self):
        """
        Connect to the MQTT broker and start a non-blocking loop in a background thread.
        """
        print(f"Connecting to broker {self.broker}:{self.port} ...")
        self.client.connect(self.broker, self.port, 60)

        # Instead of blocking with loop_forever(), use loop_start()
        self.client.loop_start()
        print("MQTT loop started in the background (non-blocking).")

    def stop(self):
        """
        Gracefully stop the MQTT loop and disconnect from the broker.
        """
        print("Stopping MQTT loop...")
        self.client.loop_stop()   # Stop the background thread
        self.client.disconnect()  # Close the connection

    def on_connect(self, client, userdata, flags, rc):
        """
        Callback when the client connects to the broker.
        """
        print("Connected to MQTT broker with result code:", rc)
        self.client.subscribe(self.rules_topic)
        print(f"Subscribed to topic: {self.rules_topic}")

    def on_message(self, client, userdata, msg):
        """
        Callback when a subscribed message arrives.
        """
        topic = msg.topic
        if topic == self.rules_topic:
            self.handle_rules_message(msg)

    def handle_rules_message(self, msg):
        """
        Handle messages on the rules topic. Attempt to parse JSON and pass to FileManager.
        """
        try:
            payload_str = msg.payload.decode("utf-8")
            new_rule = json.loads(payload_str)  # e.g. {"expression": "..."}
            self.file_manager.append_rule(new_rule)
        except json.JSONDecodeError:
            print("Received invalid JSON for rules. Not appending.")
        except Exception as e:
            print(f"Error handling rules message: {e}")