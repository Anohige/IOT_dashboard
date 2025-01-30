import json
import os

class FileManager:
    """
    A class to handle storing and retrieving rules in a JSON file.
    """

    def __init__(self, rules_file=None):
        if rules_file is None:
            # By default, store 'rules.json' in the same directory as file_manager.py
            # or wherever you prefer:
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            rules_file = os.path.join(parent_dir, "rules.json")
        self.rules_file = rules_file

        # For demonstration, let's define a "temporary device ID" we trust:
        self.temp_valid_device_id = "dev_679511e95eff96.21185485"

        print(f"FileManager initialized. Saving rules to: {self.rules_file}")

    def append_rule(self, new_rule_obj):
        """
        This method expects 'new_rule_obj' to contain:
          { "expression": "...", "device_id": "..." }

        We compare 'device_id' to our 'temp_valid_device_id'.
        If it matches, we only store { "expression": "..."} in the JSON file.
        Otherwise, we skip.
        """
        # 1) Extract fields
        device_id = new_rule_obj.get("device_id", "")
        expression = new_rule_obj.get("expression", "")

        if not expression:
            print("No 'expression' in rule object. Not appending.")
            return

        if not device_id:
            print("No 'device_id' in rule object. Not appending.")
            return

        # 2) Compare to our temporary known device ID
        if device_id != self.temp_valid_device_id:
            print(f"Received device_id='{device_id}' which doesn't match temp_valid_device_id. Skipping.")
            return

        # 3) If it matches, create a minimal object with only 'expression'
        rule_to_store = { "expression": expression }

        # 4) Load existing rules or init empty list
        rules_list = []
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, "r") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    rules_list = data
                else:
                    print("WARNING: rules.json was not a list. Reinitializing.")
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        # 5) Append the new rule
        rules_list.append(rule_to_store)

        # 6) Write the updated list back
        with open(self.rules_file, "w") as f:
            json.dump(rules_list, f, indent=2)

        print(f"Appended new rule from device_id='{device_id}' to {self.rules_file}:\n{rule_to_store}")