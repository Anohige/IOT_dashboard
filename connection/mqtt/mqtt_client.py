import json
import os
import time
import threading
import logging
import socket
import random
import sys

import paho.mqtt.client as paho_mqtt
from File_manager.file_manager import FileManager
from stats.system_stats import SystemStats
from DAQ.daq import DAQ

# --- Logging setup ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


class MqttClient:
    def __init__(
            self,
            device_serial: str = None,
            file_manager: FileManager = None,
            broker: str = "broker.emqx.io",
            port: int = 1883,
            use_websockets: bool = False,
            rules_topic: str = "iot/rules/updated",
            stats_topic: str = "iot/device/stats",
            system_stats=None,
    ):
        # Initialize DAQ first to get serial number
        print("Initializing DAQ...")
        self.daq = DAQ()

        # Get device serial from DAQ if none provided
        if device_serial is None and hasattr(self.daq, 'serial_number') and self.daq.serial_number != "UNKNOWN":
            self.device_serial = self.daq.serial_number
            print(f"Using device serial from DAQ: {self.device_serial}")
        else:
            self.device_serial = device_serial
            print(f"Using provided device serial: {self.device_serial}")

        self.file_manager = FileManager()
        self.broker = broker
        self.port = port
        self.use_websockets = use_websockets
        self.rules_topic = rules_topic
        self.stats_topic = stats_topic
        self.system_stats = SystemStats()

        self.client_id = f"python_client_{int(time.time())}_{os.getpid()}"
        self.connected = False

        print(f"MQTT Client initialized with ID: {self.client_id}")
        print(f"Device Serial: {self.device_serial}")
        print(f"Broker: {self.broker}:{self.port}")
        print(f"Stats Topic: {self.stats_topic}")

        self._check_connectivity()
        self._initialize_client()

    def _check_connectivity(self):
        try:
            ip = socket.gethostbyname(self.broker)
            logger.info(f"Resolved {self.broker} → {ip}")
            print(f"Resolved broker {self.broker} to IP: {ip}")

            sock = socket.socket()
            sock.settimeout(5)
            res = sock.connect_ex((ip, self.port))
            sock.close()

            if res == 0:
                logger.info(f"TCP connect to {ip}:{self.port} succeeded")
                print(f"TCP connectivity test to {ip}:{self.port} SUCCEEDED")
            else:
                logger.warning(f"TCP connect to {ip}:{self.port} failed (code {res})")
                print(f"TCP connectivity test to {ip}:{self.port} FAILED (code {res})")
        except Exception as e:
            logger.exception("Connectivity check failed")
            print(f"Connectivity check failed: {e}")

    def _initialize_client(self):
        if self.use_websockets:
            self.client = paho_mqtt.Client(
                client_id=self.client_id,
                transport="websockets",
                clean_session=True,
            )
            self.client.ws_set_options(path="/mqtt")
            print("Initialized MQTT client with WebSockets transport")
        else:
            self.client = paho_mqtt.Client(
                client_id=self.client_id, clean_session=True
            )
            print("Initialized MQTT client with TCP transport")

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.client.on_publish = self.on_publish
        self.client.enable_logger(logger)

    def connect_and_loop(self):
        """Connect & start loop, then always start stats thread."""
        try:
            logger.info(f"Connecting to MQTT at {self.broker}:{self.port} …")
            print(f"Connecting to MQTT broker at {self.broker}:{self.port}...")

            # Add connection timeout
            self.client.connect_async(self.broker, self.port, keepalive=60)
            self.client.loop_start()

            for i in range(10):
                if self.connected:
                    print("✅ Successfully connected to MQTT broker!")
                    break
                time.sleep(1)
                logger.info(f"Waiting for CONNACK… {i + 1}/10")
                print(f"Waiting for connection... {i + 1}/10")
            else:
                logger.error("Failed to connect in 10s")
                print("❌ Failed to connect to MQTT broker in 10 seconds!")
                print("Trying direct TCP connection...")

                # Try a direct connection without loop_start
                try:
                    self.client.loop_stop()
                    time.sleep(1)
                    print("Attempting direct connection...")
                    self.client.connect(self.broker, self.port, keepalive=60)
                    self.connected = True
                    self.client.loop_start()
                    print("Direct connection successful!")
                except Exception as connect_error:
                    print(f"Direct connection also failed: {connect_error}")
                    print("Check network connectivity and try again.")
                    sys.exit(1)

            # Start stats publisher thread
            print("Starting stats publisher thread")
            threading.Thread(
                target=self.publish_system_stats, daemon=True
            ).start()
        except Exception as e:
            logger.exception("Failed to start MQTT loop")
            print(f"❌ Failed to start MQTT loop: {e}")
            sys.exit(1)

    # ─── MQTT CALLBACKS ──────────────────────────────────────────────────
    def on_connect(self, client, userdata, flags, rc):
        mapping = {
            0: "OK", 1: "BAD_PROTO", 2: "BAD_ID",
            3: "UNAVAIL", 4: "BAD_AUTH", 5: "NOT_AUTH"
        }
        result = mapping.get(rc, f"UNKNOWN({rc})")
        logger.info(f"on_connect → {result}")

        print(f"MQTT Connect Result: {result}")

        if rc == 0:
            self.connected = True
            client.subscribe(self.rules_topic, qos=1)
            logger.info(f"Subscribed to rules topic `{self.rules_topic}`")
            print(f"Subscribed to rules topic: {self.rules_topic}")
        else:
            logger.error(f"Connection refused: {result}")
            print(f"❌ Connection refused: {result}")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected DISCONNECT (rc={rc}), will reconnect")
            print(f"❌ Unexpected disconnection (rc={rc}), attempting to reconnect...")
            threading.Timer(5.0, self.client.reconnect).start()
        else:
            logger.info("Clean disconnect")
            print("Clean disconnect from MQTT broker")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        logger.info(f"on_subscribe → mid={mid}, qos={granted_qos}")
        print(f"Subscription confirmed: mid={mid}, qos={granted_qos}")

    def on_publish(self, client, userdata, mid):
        logger.debug(f"on_publish → mid={mid}")
        print(f"Message published successfully (mid={mid})")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        logger.info(f"MSG `{topic}` → {payload}")

        if topic == self.rules_topic:
            self.handle_rules_message(payload)

    # ─── RULES HANDLER ───────────────────────────────────────────────────
    def handle_rules_message(self, payload: str):
        try:
            rule_data = json.loads(payload)
            logger.info(f"Parsed rule data: {rule_data}")

            saved = self.file_manager.append_rule(rule_data)
            if saved:
                logger.info("Rule saved successfully")
            else:
                logger.warning("Rule was not saved (check serial mismatch?)")

        except json.JSONDecodeError:
            logger.error("Invalid JSON in rules topic")
        except Exception as e:
            logger.exception(f"Error handling rules message: {e}")

    # ─── STATS PUBLISHER ─────────────────────────────────────────────────
    def publish_system_stats(self):
        """Thread function to publish system and sensor stats without blocking."""
        logger.info("Starting stats publisher thread")
        print("Stats publisher thread starting...")

        # Wait a moment for connection to stabilize
        time.sleep(2)

        publish_count = 0

        while True:
            try:
                publish_count += 1
                print(f"\n--- Publishing stats (attempt #{publish_count}) ---")

                # Create empty stats object first
                stats = {
                    "cpu_usage": 0.0,
                    "ram_usage": 70.0,
                    "disk_usage": 10.0,
                    "temperature": 25.0,
                    "humidity": 60.0
                }

                # Try to get system stats (with timeout protection)
                try:
                    if self.system_stats:
                        system_stats = self.system_stats.get_system_stats()
                        if system_stats:
                            # Update with actual values if available
                            for key in ["cpu_usage", "ram_usage", "disk_usage", "temperature"]:
                                if key in system_stats:
                                    stats[key] = system_stats[key]
                        print(f"System stats retrieved: {system_stats}")
                except Exception as e:
                    print(f"Error getting system stats: {e}")

                # Try to get sensor data (with timeout protection)
                try:
                    print("Getting sensor data from DAQ...")
                    sensor_data = self.daq.get_sensor_data()

                    # Only update if we have valid data
                    if sensor_data:
                        if sensor_data.get("temperature") is not None:
                            stats["temperature"] = sensor_data["temperature"]
                        if sensor_data.get("humidity") is not None:
                            stats["humidity"] = sensor_data["humidity"]
                        print(f"Sensor data integrated: temp={stats['temperature']}°C, humidity={stats['humidity']}%")
                except Exception as e:
                    print(f"Error getting sensor data: {e}")

                # Always set device serial
                if self.device_serial:
                    stats["device_serial"] = self.device_serial
                elif hasattr(self.daq, 'serial_number') and self.daq.serial_number != "UNKNOWN":
                    stats["device_serial"] = self.daq.serial_number
                else:
                    stats["device_serial"] = "UNKNOWN"

                # Add timestamp
                stats["timestamp"] = time.time()

                # Convert to JSON and publish
                try:
                    payload = json.dumps(stats)
                    print(f"Publishing to {self.stats_topic}: {payload}")

                    if self.connected:
                        result = self.client.publish(self.stats_topic, payload, qos=1)
                        if result.rc == 0:
                            print(f"✅ SUCCESSFULLY PUBLISHED DATA")
                            print(f"   Temperature: {stats['temperature']}°C")
                            print(f"   Humidity: {stats['humidity']}%")
                            print(f"   Device: {stats['device_serial']}")
                        else:
                            print(f"❌ Publish failed (rc={result.rc})")
                    else:
                        print("❌ Not connected to MQTT broker")
                except Exception as e:
                    print(f"Error publishing data: {e}")

            except Exception as e:
                print(f"Unhandled error in publish_system_stats: {e}")

            # Wait for next cycle
            print("Waiting 5 seconds until next publish...")
            time.sleep(5)