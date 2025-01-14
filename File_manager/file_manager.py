# File_manager/file_manager.py

import json
import os

class FileManager:
    def __init__(self, rules_file=None):
        if rules_file is None:
            # Place rules.json in python/ directory (one level up from File_manager).
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            rules_file = os.path.join(parent_dir, "rules.json")

        self.rules_file = rules_file
        print(f"FileManager initialized. Saving rules to: {self.rules_file}")

    def append_rule(self, new_rule_obj):
        rules_list = []
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, "r") as f:
                    existing_data = json.load(f)
                if isinstance(existing_data, list):
                    rules_list = existing_data
                else:
                    print("WARNING: Existing data is not a list. Reinitializing.")
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        rules_list.append(new_rule_obj)

        with open(self.rules_file, "w") as f:
            json.dump(rules_list, f, indent=2)

        print(f"Appended rule to {self.rules_file}:\n{new_rule_obj}")