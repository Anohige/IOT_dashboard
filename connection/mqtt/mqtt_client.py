import json
import paho.mqtt.client as paho_mqtt
import sys
import os
import time
import threading
import logging
import ssl
from datetime import datetime
import socket
from File_manager.file_manager import FileManager
# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MqttClient:
    def __init__(
            self,
            file_manager=FileManager(),
            broker="broker.emqx.io",
            port=1883,  # Using standard MQTT port instead of WebSocket
            use_websockets=False,  # Disable WebSockets for more reliable connection
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
        self.connect_retries = 0
        self.max_retries = 5
        self.subscription_mid = None  # Store message ID for subscription
        self.use_websockets = use_websockets

        # Check network connectivity before proceeding
        self._check_connectivity()

        # Initialize MQTT client
        self._initialize_client()

    def _check_connectivity(self):
        """Check basic network connectivity to the broker"""
        try:
            # Try to resolve the hostname
            logger.info(f"Resolving hostname: {self.broker}")
            host_ip = socket.gethostbyname(self.broker)
            logger.info(f"Resolved {self.broker} to IP: {host_ip}")

            # Try to establish a socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host_ip, self.port))
            sock.close()

            if result == 0:
                logger.info(f"Socket connection to {self.broker}:{self.port} successful")
            else:
                logger.warning(f"Socket connection to {self.broker}:{self.port} failed with code: {result}")
        except Exception as e:
            logger.error(f"Connectivity check failed: {e}")

    def _initialize_client(self):
        """Initialize the MQTT client with proper settings."""
        # Clean up any existing client
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except:
                pass

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

        # Enable logger
        self.client.enable_logger(logger)

    def connect_and_loop(self):
        """Connect to the MQTT broker and start a non-blocking loop."""
        logger.info(f"Connecting to {self.broker}:{self.port}")
        try:
            # Increase keepalive interval to avoid disconnections
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            logger.info("MQTT loop started (non-blocking)")

            # Wait for connection to be established
            retry_count = 0
            while not self.connected and retry_count < 10:  # Increased retry count
                time.sleep(1)
                retry_count += 1
                logger.info(f"Waiting for connection... {retry_count}/10")

            if not self.connected:
                logger.error("Failed to connect to broker after 10 seconds")
                # Try alternative broker if primary fails
                if self.broker == "broker.emqx.io":
                    logger.info("Trying alternative broker: test.mosquitto.org")
                    self.broker = "test.mosquitto.org"
                    self.client.loop_stop()
                    self._initialize_client()
                    self.client.connect(self.broker, self.port, keepalive=60)
                    self.client.loop_start()

                    # Wait again for connection
                    retry_count = 0
                    while not self.connected and retry_count < 10:
                        time.sleep(1)
                        retry_count += 1
                        logger.info(f"Waiting for connection to alternate broker... {retry_count}/10")

                if not self.connected:
                    return False

            # Start publishing system stats in a separate thread if system stats module is provided
            if self.system_stats:
                threading.Thread(target=self.publish_system_stats, daemon=True).start()
                logger.info("Started system stats publishing thread")

            return True
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            return False

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
            logger.info("Subscribed to test/debug topic")

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
        # Log all messages during debugging
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
                # Try to call append_rule and get the result
                try:
                    result = self.file_manager.append_rule(rule_data)
                    if result:
                        logger.info("Rule saved successfully")
                    else:
                        logger.warning("Rule was not saved (might be for another device)")
                except Exception as e:
                    logger.error(f"Error calling append_rule: {e}")
                    # Try a direct approach if the expected method isn't available
                    if hasattr(self.file_manager, 'rules_file'):
                        try:
                            # Get existing rules
                            existing_rules = []
                            if os.path.exists(self.file_manager.rules_file):
                                with open(self.file_manager.rules_file, 'r') as f:
                                    existing_rules = json.load(f)

                            # Add new rule
                            existing_rules.append({"expression": rule_data["expression"]})

                            # Save back to file
                            with open(self.file_manager.rules_file, 'w') as f:
                                json.dump(existing_rules, f, indent=2)

                            logger.info("Rule saved using direct file access")
                        except Exception as e2:
                            logger.error(f"Error saving rule directly: {e2}")
            else:
                logger.warning("No file manager available to save rule")

            # Echo the rule back for debugging
            try:
                self.client.publish("iot/rules/received", json.dumps({
                    "status": "received",
                    "timestamp": time.time(),
                    "rule": rule_data
                }))
            except Exception as e:
                logger.error(f"Error publishing receipt confirmation: {e}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in rules topic: {e}")
            logger.error(f"Raw payload: {payload}")
        except Exception as e:
            logger.error(f"Error handling rules: {e}", exc_info=True)

    def publish_test_message(self):
        """Publish a test message to verify connection."""
        try:
            # Try to get device serial if available
            device_serial = "UNKNOWN"
            if hasattr(self, 'file_manager') and hasattr(self.file_manager, '_get_device_serial'):
                try:
                    device_serial = self.file_manager._get_device_serial() or "UNKNOWN"
                except:
                    pass

            test_msg = {
                "type": "test",
                "client_id": self.client_id,
                "device_serial": device_serial,
                "timestamp": time.time(),
                "message": "Test message from backend"
            }

            logger.info(f"Publishing test message: {test_msg}")
            result = self.client.publish("test/debug", json.dumps(test_msg), qos=1)
            logger.info(f"Published test message, result code: {result.rc}, message ID: {result._mid}")

            if result.rc != 0:
                logger.error(f"Failed to publish test message, result code: {result.rc}")

        except Exception as e:
            logger.error(f"Error publishing test message: {e}", exc_info=True)

    def publish_system_stats(self):
        """Periodically publish system stats to MQTT."""
        logger.info("Starting system stats publishing loop")

        # Publish immediately on start
        self._publish_current_stats()

        # Then continue with regular interval
        while self.connected:
            try:
                time.sleep(5)  # Wait before next publish
                if not self.connected:
                    logger.warning("Lost connection, stopping stats publishing")
                    break

                self._publish_current_stats()

            except Exception as e:
                logger.error(f"Error in publish loop: {e}", exc_info=True)
                time.sleep(5)  # Wait before retry

    def _publish_current_stats(self):
        """Get and publish current system stats"""
        if not self.connected:
            logger.warning("Not connected, skipping stats publish")
            return

        try:
            # Try to get device serial if available
            device_serial = "UNKNOWN"
            try:
                # Try multiple sources for device serial
                if hasattr(self, 'file_manager') and hasattr(self.file_manager, '_get_device_serial'):
                    device_serial = self.file_manager._get_device_serial() or device_serial

                # Try to read from device_info.json as fallback
                if device_serial == "UNKNOWN":
                    try:
                        device_info_path = os.path.join(
                            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "device_info.json"
                        )
                        if os.path.exists(device_info_path):
                            with open(device_info_path, 'r') as f:
                                device_info = json.load(f)
                                if "device_serial" in device_info:
                                    device_serial = device_info["device_serial"]
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error getting device serial: {e}")

            logger.info(f"Using device_serial: {device_serial}")

            # Get system stats
            if self.system_stats:
                stats = self.system_stats.get_system_stats()
                logger.info(f"Got real system stats: {stats}")
            else:
                # Generate dummy stats for testing
                import random
                stats = {
                    "cpu_usage": random.randint(10, 90),
                    "ram_usage": random.randint(20, 85),
                    "disk_usage": random.randint(30, 95),
                    "temperature": random.randint(25, 75),
                    "humidity": random.randint(30, 70)
                }
                logger.info("Generated dummy stats")

            # Add device serial and timestamp
            stats["device_serial"] = device_serial
            stats["timestamp"] = time.time()

            # Convert to JSON
            payload = json.dumps(stats)
            logger.info(f"Stats payload prepared: {payload}")

            # Debug broker connection
            logger.info(f"MQTT connection status: connected={self.connected}, client_id={self.client_id}")

            # Double-check connection
            if not self.connected or not self.client:
                logger.error("Cannot publish - no active connection")
                return

            # Publish with QoS 1 for more reliable delivery
            logger.info(f"Publishing to {self.stats_topic}")
            result = self.client.publish(self.stats_topic, payload, qos=1)
            logger.info(f"Publish result: {result}")
            logger.info(f"Result code: {result.rc}, message ID: {result.mid}")
            if result.rc != 0:
                logger.error(f"Failed to publish stats, result code: {result.rc}")
                raise Exception(f"Publish failed with code {result.rc}")
            else:
                logger.info("Successfully published stats message")

        except Exception as e:
            logger.error(f"Error publishing stats: {e}", exc_info=True)
            # Try to reconnect if there was a publishing error
            if self.client:
                try:
                    logger.info("Attempting to reconnect after publish error")
                    self.client.reconnect()
                except:
                    logger.error("Reconnection failed after publish error")

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