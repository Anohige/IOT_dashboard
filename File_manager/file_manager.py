# File_manager.py
import json
import os
import logging
from DAQ.daq import DAQ

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileManager:
    """
    A class to handle storing and retrieving rules in a JSON file.
    """

    def __init__(self, rules_file=None, daq=None):
        # 1) Determine where to store rules.json
        if rules_file is None:
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            rules_file = os.path.join(parent_dir, "rules.json")
        self.rules_file = rules_file

        # 2) DAQ is optional; we won’t rely on its serial
        self.daq = daq or DAQ()
        # start off with no “known” serial
        self.device_serial = None

        logger.info(f"FileManager initialized. Saving rules to: {self.rules_file}")
        logger.info("Device serial will be learned from the first incoming rule.")


    def append_rule(self, new_rule_obj):
        """
        Append or update a rule in the rules.json file.

        Expects new_rule_obj:
          { "expression": "...", "device_serial": "..." }
        """
        # 1) Extract incoming fields
        received_device_serial = new_rule_obj.get("device_serial", "").strip()
        expression = new_rule_obj.get("expression", "").strip()

        if not expression:
            logger.warning("No 'expression' in rule object. Skipping.")
            return False
        if not received_device_serial:
            logger.warning("No 'device_serial' in rule object. Skipping.")
            return False

        # 2) If we haven't yet locked in our serial, adopt this one
        if self.device_serial is None:
            self.device_serial = received_device_serial
            logger.info(f"Adopted device_serial = '{self.device_serial}'")

        # 3) If it still doesn't match, skip
        if received_device_serial != self.device_serial:
            logger.warning(
                f"Ignoring rule for serial='{received_device_serial}' "
                f"(we handle '{self.device_serial}')."
            )
            return False

        # 4) Build the rule structure
        rule_to_store = {"expression": expression}

        # 5) Load existing list (or start fresh)
        existing_rules = self._load_rules()

        # 6) Just append every time (no rule_id logic needed)
        existing_rules.append(rule_to_store)
        logger.info("Appending new rule to list")

        # 7) Save back out
        success = self._save_rules(existing_rules)
        if success:
            logger.info(f"Saved {len(existing_rules)} rule(s) to {self.rules_file}")
        return success


    def _load_rules(self):
        """Load existing rules from the rules file."""
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, "r") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
                else:
                    logger.warning("rules.json not a list—overwriting.")
            except Exception as e:
                logger.error(f"Error reading rules file: {e}")
        return []


    def _save_rules(self, rules_list):
        """Save rules to the rules file, creating directories if needed."""
        try:
            os.makedirs(os.path.dirname(self.rules_file), exist_ok=True)
            with open(self.rules_file, "w") as f:
                json.dump(rules_list, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving rules file: {e}")
            return False


    def get_rules(self):
        """Return the current list of rules."""
        return self._load_rules()


    def clear_rules(self):
        """Erase all rules."""
        self._save_rules([])
        logger.info("Cleared all rules.")