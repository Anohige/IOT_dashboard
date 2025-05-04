import json
import os
import logging
from DAQ.daq import DAQ

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileManager:
    """
    Handle storing/retrieving rules in rules.json.
    """

    def __init__(self, rules_file=None, daq=None):
        # Default path: one level up from this file
        if rules_file is None:
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            rules_file = os.path.join(parent_dir, "rules.json")
        self.rules_file = rules_file

        # Optional DAQ, but we won’t rely on its serial
        self.daq = DAQ()
        # Learned when first rule arrives
        self.device_serial = self.daq.get_rpi_serial()

        logger.info(f"FileManager initialized, will save to: {self.rules_file}")
        logger.info("Waiting to learn device_serial from incoming rules.")


    def append_rule(self, new_rule_obj):
        """
        Append a new rule if its device_serial matches (or learn it).
        Expects: {"expression": "...", "device_serial": "..."}
        """
        expr = new_rule_obj.get("expression", "").strip()
        rec_serial = new_rule_obj.get("device_serial", "").strip()

        if not expr:
            logger.warning("No expression, skipping rule.")
            return False
        if not rec_serial:
            logger.warning("No device_serial, skipping rule.")
            return False

        # Learn the serial on first use
        if self.device_serial is None:
            self.device_serial = rec_serial
            logger.info(f"Adopted device_serial='{self.device_serial}'")

        # If it doesn’t match, skip
        if rec_serial != self.device_serial:
            logger.warning(
                f"Ignoring rule for '{rec_serial}', expecting '{self.device_serial}'"
            )
            return False

        # Build and append
        rule_to_store = {"expression": expr}
        current = self._load_rules()
        current.append(rule_to_store)

        if self._save_rules(current):
            logger.info(f"Saved {len(current)} rule(s) to {self.rules_file}")
            return True
        return False


    def _load_rules(self):
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, "r") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
                logger.warning("rules.json malformed, resetting.")
            except Exception as e:
                logger.error(f"Read error: {e}")
        return []


    def _save_rules(self, rules_list):
        try:
            os.makedirs(os.path.dirname(self.rules_file), exist_ok=True)
            with open(self.rules_file, "w") as f:
                json.dump(rules_list, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Write error: {e}")
            return False


    def get_rules(self):
        return self._load_rules()


    def clear_rules(self):
        self._save_rules([])
        logger.info("Cleared all rules.")