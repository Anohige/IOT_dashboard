import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileManager:
    """
    A class to handle storing and retrieving rules in a JSON file.
    """

    def __init__(self, rules_file=None, device_info_file=None):
        # Set up rules file path
        if rules_file is None:
            # By default, store 'rules.json' in the same directory as file_manager.py
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            rules_file = os.path.join(parent_dir, "rules.json")
        self.rules_file = rules_file

        # Set up device info file path
        if device_info_file is None:
            # By default, look for device_info.json in the same directory as rules.json
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            device_info_file = os.path.join(parent_dir, "device_info.json")
        self.device_info_file = device_info_file

        # Try to load the device serial from device_info file
        self.device_serial = self._get_device_serial()

        logger.info(f"FileManager initialized. Saving rules to: {self.rules_file}")
        logger.info(f"Device serial: {self.device_serial or 'Not found'}")

    def _get_device_serial(self):
        """
        Read device serial from the device_info.json file.
        Returns the device serial or None if not found.
        """
        try:
            if os.path.exists(self.device_info_file):
                with open(self.device_info_file, "r") as f:
                    device_info = json.load(f)

                # Check different possible keys that might contain the serial
                for key in ["device_serial", "serial", "id", "device_id"]:
                    if key in device_info:
                        logger.info(f"Found device serial in key '{key}': {device_info[key]}")
                        return device_info[key]

                logger.warning(f"Device serial not found in {self.device_info_file}")
                return None
            else:
                # If device_info file doesn't exist, create it with a default serial
                # This is a fallback for testing - in production you'd want to handle this differently
                default_serial = "58969696969"  # Using your temp ID as default
                os.makedirs(os.path.dirname(self.device_info_file), exist_ok=True)
                with open(self.device_info_file, "w") as f:
                    json.dump({"device_serial": default_serial}, f, indent=2)
                logger.warning(f"Created device_info.json with default serial: {default_serial}")
                return default_serial

        except Exception as e:
            logger.error(f"Error reading device_info file: {e}")
            return None

    def append_rule(self, new_rule_obj):
        """
        Append or update a rule in the rules.json file.

        This method expects 'new_rule_obj' to contain:
          { "expression": "...", "device_serial": "..." }

        If the device_serial matches our device's serial,
        we store the rule in the JSON file, replacing any existing rule with
        the same rule ID or adding it if it's new.
        """
        # 1) Extract fields
        received_device_serial = new_rule_obj.get("device_serial", "")
        expression = new_rule_obj.get("expression", "")
        rule_id = new_rule_obj.get("rule_id", "default")  # Optional rule ID

        if not expression:
            logger.warning("No 'expression' in rule object. Not appending.")
            return False

        if not received_device_serial:
            logger.warning("No 'device_serial' in rule object. Not appending.")
            return False

        # Ensure we have loaded the latest device serial
        if not self.device_serial:
            self.device_serial = self._get_device_serial()

        # Compare with quotes stripped if present
        if isinstance(received_device_serial, str) and received_device_serial.startswith(
                "'") and received_device_serial.endswith("'"):
            received_device_serial = received_device_serial[1:-1]

        # 2) Compare to our device serial
        if not self.device_serial or received_device_serial != self.device_serial:
            logger.warning(
                f"Received device_serial='{received_device_serial}' which doesn't match device_serial='{self.device_serial}'. Skipping.")
            return False

        # 3) Create a rule object with expression and the optional rule_id
        rule_to_store = {"expression": expression}
        if rule_id != "default":
            rule_to_store["rule_id"] = rule_id

        # 4) Load existing rules or init empty list
        existing_rules = self._load_rules()

        # 5) Check if we need to update an existing rule or append a new one
        if rule_id != "default":
            # Try to find and update an existing rule with the same ID
            for i, rule in enumerate(existing_rules):
                if rule.get("rule_id") == rule_id:
                    existing_rules[i] = rule_to_store
                    logger.info(f"Updated existing rule with ID: {rule_id}")
                    break
            else:
                # No matching rule found, so append
                existing_rules.append(rule_to_store)
                logger.info(f"Added new rule with ID: {rule_id}")
        else:
            # No rule ID specified, so just append as a new rule
            existing_rules.append(rule_to_store)
            logger.info(f"Added new rule without ID")

        # 6) Write the updated list back
        self._save_rules(existing_rules)

        logger.info(f"Processed rule from device_serial='{received_device_serial}'")
        return True

    def _load_rules(self):
        """Load existing rules from the rules file."""
        rules_list = []
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, "r") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    rules_list = data
                else:
                    logger.warning("WARNING: rules.json was not a list. Reinitializing.")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.error(f"Error loading rules file: {e}")
        return rules_list

    def _save_rules(self, rules_list):
        """Save rules to the rules file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.rules_file), exist_ok=True)

            with open(self.rules_file, "w") as f:
                json.dump(rules_list, f, indent=2)
            logger.info(f"Saved {len(rules_list)} rules to {self.rules_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving rules file: {e}")
            return False

    def get_rules(self):
        """
        Get all rules from the rules file.
        Returns a list of rule objects.
        """
        return self._load_rules()

    def clear_rules(self):
        """
        Clear all rules from the rules file.
        """
        self._save_rules([])
        logger.info("Cleared all rules")