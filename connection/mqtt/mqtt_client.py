# mqtt_client.py

import json
import paho.mqtt.client as paho_mqtt
import sys
import os
import time
import threading

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from File_manager.file_manager import FileManager
from stats.system_stats import SystemStats

class MqttClient:
    """
    Manages MQTT connection and subscriptions.
    """
    def __init__(
        self,
        file_manager=None,
        broker="broker.hivemq.com",
        port=1883,
        rules_topic="iot/rules/updated",
        stats_topic="iot/device/stats"
    ):
        """
        :param file_manager: Instance of FileManager
        :param broker: MQTT broker address
        :param port: MQTT broker port
        :param rules_topic: Topic to receive rules
        :param stats_topic: Topic to send system stats
        """
        self.broker = broker
        self.port = port
        self.rules_topic = rules_topic
        self.stats_topic = stats_topic

        self.client = paho_mqtt.Client()

        # Bind callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.file_manager = file_manager if file_manager else FileManager()
        self.system_stats = SystemStats()

    def connect_and_loop(self):
        """Connect to the MQTT broker and start a non-blocking loop."""
        print(f"[MQTT] Connecting to {self.broker}:{self.port}...")
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        print("[MQTT] MQTT loop started (non-blocking).")

        # Start publishing system stats in a separate thread
        threading.Thread(target=self.publish_system_stats, daemon=True).start()

    def stop(self):
        """Stop MQTT loop and disconnect."""
        print("[MQTT] Stopping...")
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        """Subscribe to topics when connected."""
        print(f"[MQTT] Connected with result code {rc}")
        self.client.subscribe(self.rules_topic)
        print(f"[MQTT] Subscribed to: {self.rules_topic}")

    def on_message(self, client, userdata, msg):
        """Handle incoming messages."""
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        if topic == self.rules_topic:
            self.handle_rules_message(payload)

    def handle_rules_message(self, payload):
        """Handles rules topic messages."""
        try:
            rule_data = json.loads(payload)
            self.file_manager.append_rule(rule_data)
        except json.JSONDecodeError:
            print("[MQTT] Invalid JSON in rules topic.")
        except Exception as e:
            print(f"[MQTT] Error handling rules: {e}")

    def publish_system_stats(self):
        """Periodically publish system stats to MQTT."""
        while True:
            stats = self.system_stats.get_system_stats()
            if stats:
                payload = json.dumps(stats)
                self.client.publish(self.stats_topic, payload)
                print(f"[MQTT] Published System Stats: {payload}")
            time.sleep(5)