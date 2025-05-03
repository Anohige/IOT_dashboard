import json
import paho.mqtt.client as paho_mqtt
import sys
import os
import time
import threading
import logging
import ssl
from datetime import datetime
from DAQ.daq import DAQ

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MqttClient:
    def __init__(
            self,
            file_manager=None,
            broker="broker.emqx.io",  # EMQX broker
            port=8083,  # EMQX WebSocket port
            use_websockets=True,
            rules_topic="iot/rules/updated",
            stats_topic="iot/device/stats",
            system_stats=None,
    ):
        self.broker = broker
        self.port = port
        self.rules_topic = rules_topic
        self.stats_topic = stats_topic
        self.client_id = f"python_client_{int(time.time())}_{os.getpid()}"
        self.connected = False
        self.client = None
        self.file_manager = file_manager
        self.system_stats = system_stats
        self.daq = DAQ()
        self.connect_retries = 0
        self.max_retries = 5
        self.subscription_mid = None  # Store message ID for subscription
        self.use_websockets = use_websockets

        # Initialize MQTT client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the MQTT client with proper settings."""
        if self.use_websockets:
            self.client = paho_mqtt.Client(
                client_id=self.client_id,
                transport="websockets",
                clean_session=True
            )
            self.client.ws_set_options(path="/mqtt")
            logger.info(f"Created WebSocket client with ID: {self.client_id}")
        else:
            self.client = paho_mqtt.Client(client_id=self.client_id, clean_session=True)
            logger.info(f"Created TCP client with ID: {self.client_id}")

        # Set up callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_log = self.on_log
        self.client.on_subscribe = self.on_subscribe
        self.client.on_publish = self.on_publish

        # Set a longer keepalive time
        self.client.enable_logger(logger)

    def connect_and_loop(self):
        """Connect to the MQTT broker and start a non-blocking loop."""
        logger.info(f"Connecting to {self.broker}:{self.port}")
        try:
            # Increase keepalive interval to avoid disconnections
            self.client.connect(self.broker, self.port, keepalive=120)
            self.client.loop_start()
            logger.info("MQTT loop started (non-blocking)")

            # Wait for connection to be established
            retry_count = 0
            while not self.connected and retry_count < 5:
                time.sleep(1)
                retry_count += 1

            if not self.connected:
                logger.error("Failed to connect to broker after 5 seconds")
                return False

            # Start publishing system stats in a separate thread if system stats module is provided
            if self.system_stats:
                threading.Thread(target=self.publish_system_stats, daemon=True).start()

            return True
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            return False

    def stop(self):
        """Stop MQTT loop and disconnect."""
        logger.info("Stopping MQTT client...")
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

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
            self.connected = True
            logger.info(f"Successfully connected to broker: {self.broker}")

            # Subscribe to the rules topic with QoS 1 for more reliable delivery
            result, mid = self.client.subscribe(self.rules_topic, qos=1)
            self.subscription_mid = mid
            logger.info(f"Subscribing to {self.rules_topic}, result: {result}, message ID: {mid}")

            # Also subscribe to test topic to validate subscription works
            self.client.subscribe("test/debug", qos=1)

            # Publish a test message
            self.publish_test_message()
        else:
            self.connected = False
            self.connect_retries += 1
            logger.error(f"Failed to connect: {result}")

            if self.connect_retries < self.max_retries:
                logger.info(f"Retrying connection (attempt {self.connect_retries}/{self.max_retries})...")
                time.sleep(2)  # Wait before retry
                try:
                    self.client.reconnect()
                except Exception as e:
                    logger.error(f"Reconnection error: {e}")
            else:
                logger.error(f"Max connection retries ({self.max_retries}) reached")

    def on_disconnect(self, client, userdata, rc):
        """Handle disconnection events."""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection: {rc}")
            # Try to reconnect
            threading.Timer(5.0, self._reconnect).start()
        else:
            logger.info("Disconnected successfully")

    def _reconnect(self):
        """Attempt to reconnect to the broker."""
        if not self.connected:
            try:
                logger.info("Attempting to reconnect...")
                self.client.reconnect()
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                # Schedule another reconnection attempt
                if self.connect_retries < self.max_retries:
                    self.connect_retries += 1
                    threading.Timer(5.0, self._reconnect).start()

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """Handle subscription confirmation."""
        logger.info(f"Successfully subscribed with message ID: {mid}, QoS: {granted_qos}")
        if mid == self.subscription_mid:
            logger.info(f"Confirmed subscription to {self.rules_topic}")

    def on_publish(self, client, userdata, mid):
        """Handle publish confirmation."""
        logger.info(f"Message {mid} published successfully")

    def on_message(self, client, userdata, msg):
        """Handle incoming messages."""
        topic = msg.topic
        try:
            payload = msg.payload.decode("utf-8")
            logger.info(f"Message received on topic {topic}: {payload}")

            # Parse message based on topic
            if topic == self.rules_topic:
                self.handle_rules_message(payload)
            elif topic == "test/debug":
                logger.info(f"Test message received: {payload}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    def on_log(self, client, userdata, level, buf):
        """Log MQTT client internal messages."""
        # Only log important messages to reduce noise
        if level in [paho_mqtt.MQTT_LOG_ERR, paho_mqtt.MQTT_LOG_WARNING]:
            logger.debug(f"MQTT Log: {buf}")

    def handle_rules_message(self, payload):
        """Handle rules topic messages."""
        try:
            logger.info(f"Processing rules message: {payload}")

            # Try to parse the JSON payload
            rule_data = json.loads(payload)
            logger.info(f"Parsed rule data: {rule_data}")

            # Check if the message has the expected format
            if not isinstance(rule_data, dict):
                logger.warning(f"Unexpected rule data format: {type(rule_data)}")
                return

            # Check for required fields
            if 'expression' not in rule_data:
                logger.warning("Missing required field 'expression' in rule data")
                return

            # Process the rule
            if self.file_manager:
                self.file_manager.append_rule(rule_data)
                logger.info(f"Rule saved successfully")
            else:
                logger.warning("No file manager available to save rule")

            # Echo the rule back for debugging
            self.client.publish("iot/rules/received", json.dumps({
                "status": "received",
                "timestamp": time.time(),
                "rule": rule_data
            }))

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in rules topic: {e}")
            logger.error(f"Raw payload: {payload}")
        except Exception as e:
            logger.error(f"Error handling rules: {e}", exc_info=True)

    def publish_test_message(self):
        """Publish a test message to verify connection."""
        try:
            test_msg = {
                "type": "test",
                "client_id": self.client_id,
                "timestamp": time.time(),
                "message": "Test message from backend"
            }
            self.client.publish("test/debug", json.dumps(test_msg), qos=1)
            logger.info("Published test message")
        except Exception as e:
            logger.error(f"Error publishing test message: {e}")

    def publish_system_stats(self):
        """Periodically publish system stats to MQTT."""
        while self.connected:
            try:
                # Example stats - replace with your actual system stats
                if self.system_stats:
                    stats = self.system_stats.get_system_stats()
                else:
                    # Generate dummy stats for testing
                    import random
                    stats = {
                        "cpu_usage": random.randint(10, 90),
                        "ram_usage": random.randint(20, 85),
                        "disk_usage": random.randint(30, 95),
                        "temperature": random.randint(25, 75),
                        "humidity": random.randint(30, 70),
                        "timestamp": time.time()
                    }

                # Add device ID
                stats["device_serial"] = self.daq.get_rpi_serial()
                stats["timestamp"] = time.time()

                # Convert to JSON
                payload = json.dumps(stats)

                # Publish with QoS 1 for more reliable delivery
                result = self.client.publish(self.stats_topic, payload, qos=1)
                logger.info(f"Published stats: {result.rc == 0}")
                if result.rc != 0:
                    logger.error(f"Failed to publish stats, result code: {result.rc}")

            except Exception as e:
                logger.error(f"Error publishing stats: {e}", exc_info=True)

            # Wait before publishing again
            time.sleep(5)

    def publish_message(self, topic, message, qos=1):
        """Publish a custom message to a specified topic."""
        try:
            if not self.connected:
                logger.warning("Cannot publish message: Not connected to broker")
                return False

            if isinstance(message, dict):
                message = json.dumps(message)

            result = self.client.publish(topic, message, qos=qos)
            logger.info(f"Published message to {topic}: {result.rc == 0}")
            return result.rc == 0
        except Exception as e:
            logger.error(f"Error publishing message to {topic}: {e}")
            return False

    def subscribe_to_topic(self, topic, qos=1):
        """Subscribe to an additional topic."""
        if self.connected:
            result, mid = self.client.subscribe(topic, qos)
            logger.info(f"Subscribed to {topic}, result: {result}")
            return result == 0
        else:
            logger.warning(f"Cannot subscribe to {topic}: Not connected")
            return False