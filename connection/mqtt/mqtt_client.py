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

        self.client.on_connect    = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message    = self.on_message
        self.client.on_subscribe  = self.on_subscribe
        self.client.on_publish    = self.on_publish
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
                logger.info(f"Waiting for CONNACK… {i+1}/10")
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
                    print("FAILED")

                # enforce device_serial
                if self.device_serial:
                    stats["device_serial"] = self.device_serial
                else:
                    # defer to FileManager’s learned serial if any
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