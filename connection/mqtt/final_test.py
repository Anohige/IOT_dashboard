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
    level=logging.INFO,
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
        self.device_serial = device_serial  # optional override
        self.file_manager = FileManager() if file_manager is None else file_manager
        self.broker = broker
        self.port = port
        self.use_websockets = use_websockets
        self.rules_topic = rules_topic
        self.stats_topic = stats_topic
        self.system_stats = SystemStats() if system_stats is None else system_stats

        # Initialize DAQ for sensor data
        print("Initializing DAQ for sensor data...")
        self.daq = DAQ()

        self.client_id = f"python_client_{int(time.time())}_{os.getpid()}"
        self.connected = False

        self._check_connectivity()
        self._initialize_client()

    def _check_connectivity(self):
        try:
            ip = socket.gethostbyname(self.broker)
            logger.info(f"Resolved {self.broker} → {ip}")
            sock = socket.socket()
            sock.settimeout(5)
            res = sock.connect_ex((ip, self.port))
            sock.close()
            if res == 0:
                logger.info(f"TCP connect to {ip}:{self.port} succeeded")
            else:
                logger.warning(f"TCP connect to {ip}:{self.port} failed (code {res})")
        except Exception:
            logger.exception("Connectivity check failed")

    def _initialize_client(self):
        if self.use_websockets:
            self.client = paho_mqtt.Client(
                client_id=self.client_id,
                transport="websockets",
                clean_session=True,
            )
            self.client.ws_set_options(path="/mqtt")
        else:
            self.client = paho_mqtt.Client(
                client_id=self.client_id, clean_session=True
            )

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
            print(f"Connecting to MQTT at {self.broker}:{self.port} …")
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()

            for i in range(10):
                if self.connected:
                    print("Successfully connected to MQTT broker!")
                    break
                time.sleep(1)
                logger.info(f"Waiting for CONNACK… {i + 1}/10")
                print(f"Waiting for connection... {i + 1}/10")
            else:
                logger.error("Failed to connect in 10s")
                print("Failed to connect to MQTT broker in 10 seconds.")
                sys.exit(1)

            # Start the stats publisher thread
            print("Starting stats publisher thread...")
            thread = threading.Thread(
                target=self.publish_system_stats, daemon=True
            )
            thread.start()
            return thread

        except Exception as e:
            logger.exception("Failed to start MQTT loop")
            print(f"Failed to start MQTT loop: {e}")
            sys.exit(1)

    # ─── MQTT CALLBACKS ──────────────────────────────────────────────────
    def on_connect(self, client, userdata, flags, rc):
        mapping = {
            0: "OK", 1: "BAD_PROTO", 2: "BAD_ID",
            3: "UNAVAIL", 4: "BAD_AUTH", 5: "NOT_AUTH"
        }
        result = mapping.get(rc, f"UNKNOWN({rc})")
        logger.info(f"on_connect → {result}")
        print(f"MQTT connection result: {result}")

        if rc == 0:
            self.connected = True
            client.subscribe(self.rules_topic, qos=1)
            logger.info(f"Subscribed to rules topic `{self.rules_topic}`")
            print(f"Subscribed to rules topic: {self.rules_topic}")
        else:
            logger.error(f"Connection refused: {result}")
            print(f"MQTT connection refused: {result}")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected DISCONNECT (rc={rc}), will reconnect")
            print(f"Unexpected disconnection (rc={rc}), will try to reconnect")
            threading.Timer(5.0, self.client.reconnect).start()
        else:
            logger.info("Clean disconnect")
            print("Cleanly disconnected from MQTT broker")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        logger.info(f"on_subscribe → mid={mid}, qos={granted_qos}")
        print(f"Subscription confirmed: mid={mid}, qos={granted_qos}")

    def on_publish(self, client, userdata, mid):
        logger.debug(f"on_publish → mid={mid}")
        # Debug printing successful publish
        print(f"Message published successfully: {mid}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        logger.info(f"MSG `{topic}` → {payload}")
        print(f"Received message on topic `{topic}`: {payload}")

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
        except Exception:
            logger.exception("Error handling rules message")

    # ─── STATS PUBLISHER ─────────────────────────────────────────────────
    def publish_system_stats(self):
        logger.info("Starting stats publisher thread")
        print("Stats publisher thread started")

        while True:
            try:
                print("─── Publishing system stats ───")

                # STEP 1: Get system stats
                if self.system_stats:
                    try:
                        stats = self.system_stats.get_system_stats()
                        print(f"System stats: {stats}")
                    except Exception as e:
                        logger.error(f"Error getting system stats: {e}")
                        print(f"Error getting system stats: {e}")
                        # Create minimal stats to ensure we can publish something
                        stats = {
                            "cpu_usage": 0.0,
                            "ram_usage": 70.0,
                            "disk_usage": 10.0
                        }
                else:
                    print("System stats object not available, using defaults")
                    stats = {
                        "cpu_usage": 0.0,
                        "ram_usage": 70.0,
                        "disk_usage": 10.0
                    }

                # STEP 2: Get sensor data from DAQ
                try:
                    print("Getting sensor data from DAQ...")
                    sensor_data = self.daq.get_sensor_data()
                    print(f"Retrieved sensor data: {sensor_data}")

                    # Add temperature directly to stats (not nested)
                    if sensor_data.get("temperature") is not None:
                        stats["temperature"] = sensor_data["temperature"]
                        print(f"Temperature: {stats['temperature']}°C")
                    else:
                        stats["temperature"] = 25.0  # Default
                        print("Temperature not available, using default: 25.0°C")

                    # Add humidity directly to stats (not nested)
                    if sensor_data.get("humidity") is not None:
                        stats["humidity"] = sensor_data["humidity"]
                        print(f"Humidity: {stats['humidity']}%")
                    else:
                        stats["humidity"] = 60.0  # Default
                        print("Humidity not available, using default: 60.0%")

                except Exception as e:
                    logger.error(f"Error getting sensor data: {e}")
                    print(f"Error getting sensor data: {e}")
                    # Add defaults
                    stats["temperature"] = 25.0
                    stats["humidity"] = 60.0
                    print("Using default temperature (25.0°C) and humidity (60.0%)")

                # STEP 3: Set device serial
                if self.device_serial:
                    stats["device_serial"] = self.device_serial
                elif hasattr(self.daq,
                             'serial_number') and self.daq.serial_number and self.daq.serial_number != "UNKNOWN":
                    stats["device_serial"] = self.daq.serial_number
                    print(f"Using DAQ serial: {self.daq.serial_number}")
                else:
                    stats["device_serial"] = self.file_manager.device_serial or "UNKNOWN"
                    print(f"Using FileManager serial: {stats['device_serial']}")

                # STEP 4: Add timestamp
                stats["timestamp"] = time.time()

                # STEP 5: Convert to JSON and publish
                try:
                    payload = json.dumps(stats)
                    print(f"Payload to publish: {payload}")

                    # Check connection before publishing
                    if not self.connected:
                        print("MQTT client not connected! Cannot publish.")
                        logger.error("MQTT client not connected, cannot publish")
                        time.sleep(5)
                        continue

                    print(f"Publishing to `{self.stats_topic}`...")
                    result = self.client.publish(
                        self.stats_topic, payload, qos=1
                    )

                    if result.rc != 0:
                        logger.error(f"Stats publish failed (rc={result.rc})")
                        print(f"Publish failed with code: {result.rc}")
                    else:
                        logger.info("Stats published successfully")
                        print(
                            f"✅ SUCCESSFULLY PUBLISHED: temp={stats.get('temperature')}°C, hum={stats.get('humidity')}%")

                except Exception as e:
                    logger.error(f"Error during publishing: {e}")
                    print(f"Error during publishing: {e}")

            except Exception as e:
                logger.exception("Error in publish_system_stats")
                print(f"Unhandled error in stats publisher: {e}")

            # Wait before next publish
            print("Waiting 5 seconds before next publish...")
            time.sleep(5)

    def cleanup(self):
        """Cleanup resources"""
        try:
            print("Cleaning up resources...")
            self.client.loop_stop()
            self.client.disconnect()
            if hasattr(self.daq, 'cleanup'):
                self.daq.cleanup()
            print("Cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            print(f"Error during cleanup: {e}")


# Run as standalone for testing
if __name__ == "__main__":
    print("\n=== MQTT CLIENT STANDALONE MODE ===\n")

    # Create client
    client = MqttClient(device_serial="STANDALONE_TEST")

    try:
        # Connect and start publisher thread
        publisher_thread = client.connect_and_loop()

        # Keep main thread alive
        print("Press Ctrl+C to exit...")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        client.cleanup()
        print("\nExited cleanly")