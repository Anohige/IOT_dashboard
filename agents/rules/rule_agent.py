# rule_agent.py

import os
import json
from agents.rules.ruleEngine import RuleEngine

class RuleAgent:
    def __init__(self, rules_file_path="rules.json"):
        self.rules_file_path = rules_file_path
        self.rules = []  # Will hold a list of rule objects, e.g. [{"expression": "..."}]
        self.rule_engine = RuleEngine()

        # Example context data. 
        self.context = [
            {'mid': 'sensor1', 'data': [5], 'ts': '1627395600'},
            {'mid': 'sensor2', 'data': [8], 'ts': '1627392000'},
            {'mid': 'sensor3', 'data': [10], 'ts': '1627392001'}
        ]

    def start(self):
        """
        Main entry point: load rules from file and evaluate each rule.
        """
        self.rules = self.load_rules()
        self.evaluate_rules()

    def load_rules(self):
        """
        Load rules.json if it exists. Expecting an array of objects like:
        [
          {"expression": "..."},
          {"expression": "..."}
        ]
        """
        if os.path.exists(self.rules_file_path):
            try:
                with open(self.rules_file_path, "r") as f:
                    rules = json.load(f)

                # Make sure it's a list
                if not isinstance(rules, list):
                    print("WARNING: rules.json is not an array. Resetting to empty list.")
                    rules = []

                print(f"Loaded {len(rules)} rules from {self.rules_file_path}.")
                return rules

            except Exception as e:
                print(f"Error reading or parsing {self.rules_file_path}: {e}")
                return []
        else:
            print(f"{self.rules_file_path} does not exist. Returning empty rules list.")
            return []

    def evaluate_rules(self):
        """
        For each rule, pass the 'expression' to RuleEngine for evaluation.
        """
        if not self.rules:
            print("No rules to evaluate.")
            return

        for idx, rule in enumerate(self.rules, start=1):
            expression = rule.get("expression", "")
            print(f"\nEvaluating Rule #{idx}:\n{expression}")

            try:
                # parse_and_evaluate is assumed to take a string expression and a context
                action = self.rule_engine.parse_and_evaluate(expression, self.context)
                print(f"Result of Rule #{idx}: {action}")
            except Exception as err:
                print(f"Error evaluating Rule #{idx}: {err}")