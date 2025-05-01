import json
import paho.mqtt.client as paho_mqtt
import sys
import os
import time
import threading
import logging
import ssl

from stats.system_stats import SystemStats
from File_manager.file_manager import FileManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MqttClient:
    def __init__(
            self,
            file_manager=FileManager(),
            broker="broker.emqx.io",  # Changed to EMQX broker
            port=8083,  # EMQX WebSocket port
            use_websockets=True,
            rules_topic="iot/rules/updated",
            stats_topic="iot/device/stats",
            system_stats = SystemStats(),
    ):
        self.broker = broker
        self.port = port
        self.rules_topic = rules_topic
        self.stats_topic = stats_topic
        self.client_id = f"python_client_{int(time.time())}"

        # Initialize client with WebSocket transport
        if use_websockets:
            self.client = paho_mqtt.Client(
                client_id=self.client_id,
                transport="websockets"
            )
            self.client.ws_set_options(path="/mqtt")
            logger.info(f"Created WebSocket client with ID: {self.client_id}")
        else:
            self.client = paho_mqtt.Client(client_id=self.client_id)
            logger.info(f"Created TCP client with ID: {self.client_id}")

        # Set up callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_log = self.on_log

        self.file_manager = file_manager
        self.system_stats = system_stats

    def connect_and_loop(self):
        """Connect to the MQTT broker and start a non-blocking loop."""
        logger.info(f"Connecting to {self.broker}:{self.port}")
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            logger.info("MQTT loop started (non-blocking)")

            # Start publishing system stats in a separate thread
            threading.Thread(target=self.publish_system_stats, daemon=True).start()
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise

    def stop(self):
        """Stop MQTT loop and disconnect."""
        logger.info("Stopping MQTT client...")
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        """Handle connection response."""
        connection_result = {
            0: "Connection successful",
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier",
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorized"
        }
        result = connection_result.get(rc, f"Unknown error code: {rc}")
        logger.info(f"Connection result: {result}")

        if rc == 0:
            logger.info(f"Subscribing to {self.rules_topic}")
            self.client.subscribe(self.rules_topic)

    def on_disconnect(self, client, userdata, rc):
        """Handle disconnection events."""
        if rc != 0:
            logger.warning(f"Unexpected disconnection: {rc}")
        else:
            logger.info("Disconnected successfully")

    def on_message(self, client, userdata, msg):
        """Handle incoming messages."""
        topic = msg.topic
        try:
            payload = msg.payload.decode("utf-8")
            logger.info(f"Message received on topic {topic}: {payload}")

            if topic == self.rules_topic:
                self.handle_rules_message(payload)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def on_log(self, client, userdata, level, buf):
        """Log MQTT client internal messages."""
        logger.debug(f"MQTT Log: {buf}")

    def handle_rules_message(self, payload):
        """Handle rules topic messages."""
        try:
            rule_data = json.loads(payload)
            if self.file_manager:
                self.file_manager.append_rule(rule_data)
            logger.info(f"Processed rule data: {rule_data}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON in rules topic")
        except Exception as e:
            logger.error(f"Error handling rules: {e}")

    def publish_system_stats(self):
        """Periodically publish system stats to MQTT."""
        while True:
            try:
                # Example stats - replace with your actual system stats
                stats = self.system_stats.get_system_stats()
                stats["device_serial"] = "58969696969"

                payload = json.dumps(stats)

                # Publish to both general and device-specific topics
                result = self.client.publish(self.stats_topic, payload)
                logger.info(f"Published stats: {result.rc == 0}")
                logger.debug(f"Stats payload: {payload}")
            except Exception as e:
                logger.error(f"Error publishing stats: {e}")

            time.sleep(5)  # Wait 5 seconds before next publish