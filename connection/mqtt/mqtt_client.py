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
from DAQ.daq import DAQ  # Import the DAQ class

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
        self.device_serial = device_serial  # optional override
        self.file_manager = FileManager()
        self.broker = broker
        self.port = port
        self.use_websockets = use_websockets
        self.rules_topic = rules_topic
        self.stats_topic = stats_topic
        self.system_stats = SystemStats()

        # Initialize DAQ for sensor data
        self.daq = DAQ()

        # Try to store the device serial in the database
        self.daq.store_to_db()

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
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()

            for i in range(10):
                if self.connected:
                    break
                time.sleep(1)
                logger.info(f"Waiting for CONNACK… {i + 1}/10")
            else:
                logger.error("Failed to connect in 10s")
                sys.exit(1)

            threading.Thread(
                target=self.publish_system_stats, daemon=True
            ).start()
        except Exception:
            logger.exception("Failed to start MQTT loop")
            sys.exit(1)

    # ─── MQTT CALLBACKS ──────────────────────────────────────────────────
    def on_connect(self, client, userdata, flags, rc):
        mapping = {
            0: "OK", 1: "BAD_PROTO", 2: "BAD_ID",
            3: "UNAVAIL", 4: "BAD_AUTH", 5: "NOT_AUTH"
        }
        result = mapping.get(rc, f"UNKNOWN({rc})")
        logger.info(f"on_connect → {result}")
        if rc == 0:
            self.connected = True
            client.subscribe(self.rules_topic, qos=1)
            logger.info(f"Subscribed to rules topic `{self.rules_topic}`")
        else:
            logger.error(f"Connection refused: {result}")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected DISCONNECT (rc={rc}), will reconnect")
            threading.Timer(5.0, self.client.reconnect).start()
        else:
            logger.info("Clean disconnect")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        logger.info(f"on_subscribe → mid={mid}, qos={granted_qos}")

    def on_publish(self, client, userdata, mid):
        logger.debug(f"on_publish → mid={mid}")

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
        except Exception:
            logger.exception("Error handling rules message")

    # ─── STATS PUBLISHER ─────────────────────────────────────────────────
    def publish_system_stats(self):
        logger.info("Starting stats publisher thread")
        while True:
            try:
                if self.system_stats:
                    stats = self.system_stats.get_system_stats()
                else:
                    logger.error("System stats not available")
                    stats = {}

                # Get sensor data from DAQ
                sensor_data = self.daq.get_sensor_data()

                # Add sensor data to stats
                stats["sensor"] = {
                    "temperature": sensor_data.get("temperature"),
                    "humidity": sensor_data.get("humidity"),
                    "status": sensor_data.get("status")
                }

                # enforce device_serial - prioritize explicitly set serial,
                # then DAQ serial, then FileManager
                if self.device_serial:
                    stats["device_serial"] = self.device_serial
                elif self.daq.serial_number and self.daq.serial_number != "UNKNOWN":
                    stats["device_serial"] = self.daq.serial_number
                else:
                    # defer to FileManager's learned serial if any
                    stats["device_serial"] = self.file_manager.device_serial or "UNKNOWN"

                stats["timestamp"] = time.time()
                payload = json.dumps(stats)

                print(f"Publishing to `{self.stats_topic}`: {payload}")
                result = self.client.publish(
                    self.stats_topic, payload, qos=1
                )
                if result.rc != 0:
                    logger.error(f"Stats publish failed (rc={result.rc})")

            except Exception:
                logger.exception("Error in publish_system_stats")

            time.sleep(5)

    def cleanup(self):
        """Release all resources when done."""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            self.daq.cleanup()
            logger.info("MQTT Client resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")