import re
import math


class RuleEngine:
    def __init__(self):
        self.variables = {}
        self.context_dict = {
            "SUM": lambda *args: self.math_operation("SUM", *args),
            "SUB": lambda *args: self.math_operation("SUB", *args),
            "PROD": lambda *args: self.math_operation("PROD", *args),
            "MOD": lambda a, b: self.math_operation("MOD", a, b),
            "ABS": lambda x: self.math_operation("ABS", x),
            "SIN": lambda x: self.math_operation("SIN", x),
            "COS": lambda x: self.math_operation("COS", x),
            "TAN": lambda x: self.math_operation("TAN", x),
            "SQRT": lambda x: self.math_operation("SQRT", x),
            "MIN": lambda *args: self.math_operation("MIN", *args),
            "MAX": lambda *args: self.math_operation("MAX", *args),
            "AVG": lambda *args: self.math_operation("AVG", *args),
            "LOG": lambda x: self.math_operation("LOG", x),
            "LOG10": lambda x: self.math_operation("LOG10", x),
            "EXP": lambda x: self.math_operation("EXP", x),
            "ATAN": lambda x: self.math_operation("ATAN", x),
        }

    def math_operation(self, operation, *args):
        if operation == "SUM":
            result = sum(args)
        elif operation == "SUB":
            result = args[0] if len(args) == 1 else args[0] - sum(args[1:])
        elif operation == "PROD":
            result = 1
            for arg in args:
                result *= arg
        elif operation == "MOD":
            result = args[0] % args[1]
        elif operation == "ABS":
            result = abs(args[0])
        elif operation == "SIN":
            result = math.sin(args[0])
        elif operation == "COS":
            result = math.cos(args[0])
        elif operation == "TAN":
            result = math.tan(args[0])
        elif operation == "SQRT":
            result = math.sqrt(args[0])
        elif operation == "MIN":
            result = min(args)
        elif operation == "MAX":
            result = max(args)
        elif operation == "AVG":
            result = sum(args) / len(args)
        elif operation == "LOG":
            result = math.log(args[0])
        elif operation == "LOG10":
            result = math.log10(args[0])
        elif operation == "EXP":
            result = math.exp(args[0])
        elif operation == "ATAN":
            result = math.atan(args[0])
        else:
            raise ValueError(f"Unknown operation: {operation}")

        print(f"{operation}({', '.join(map(str, args))}) = {result}")
        return result

    def validate_keywords(self, line):
        valid_keywords = ['IF', 'THEN', 'ELSE', 'ELSEIF', 'ENDIF']
        words = line.split()
        for word in words:
            if '(' in word or ')' in word or '=' in word:
                continue
            if word in valid_keywords:
                if word.islower():
                    raise ValueError(f"Incorrect capitalization for keyword: {word} in line: {line}")
            else:
                if word.isupper():
                    raise ValueError(f"Invalid keyword: {word} in line: {line}")

    def get_data_for_mid(self, mid, context):
        for entry in context:
            if entry['mid'] == mid:
                return entry['data'][0]
        raise ValueError(f"MID {mid} not found in context")

    def preprocess_expression(self, expression):
        expression = expression.replace('&&', 'and').replace('||', 'or')
        return expression

    def parse_and_evaluate(self, expression, context):
        expression = self.preprocess_expression(expression)  # Preprocess logical operators
        lines = expression.split('\n')
        execute_actions = []
        block_stack = []  # Stack to manage IF/ELSEIF/ELSE blocks
        should_evaluate = True  # Track whether the current block should be evaluated
        block_executed = False  # Track if any block within an IF-ELSEIF-ELSE has executed

        for line in lines:
            line = line.strip()
            if not line:
                continue

            self.validate_keywords(line)

            for entry in context:
                mid = entry['mid']
                data_value = self.get_data_for_mid(mid, context)
                line = line.replace(mid, str(data_value))

            if line.startswith('IF'):
                if 'THEN' not in line:
                    raise ValueError(f"Missing 'THEN' keyword in: {line}")
                condition = re.search(r'\((.*?)\)', line).group(1)
                condition_value = eval(condition, {}, {**self.context_dict, **self.variables})
                print(f"Condition evaluated: {condition} = {condition_value}")

                # Push current evaluation state onto the stack
                block_stack.append((should_evaluate, block_executed))  # (current should_evaluate, block_executed)
                should_evaluate = should_evaluate and condition_value  # Update for nested block
                block_executed = should_evaluate  # Set whether the block was executed

            elif line.startswith('ELSEIF'):
                if not block_stack:
                    raise ValueError(f"ELSEIF without matching IF in: {line}")
                if 'THEN' not in line:
                    raise ValueError(f"Missing 'THEN' keyword in: {line}")

                # Check if any block before this has already executed
                _, prev_block_executed = block_stack[-1]
                if not prev_block_executed and not block_executed:  # Only evaluate if no previous block was executed
                    condition = re.search(r'\((.*?)\)', line).group(1)
                    condition_value = eval(condition, {}, {**self.context_dict, **self.variables})
                    print(f"Condition evaluated: {condition} = {condition_value}")
                    should_evaluate = condition_value
                    block_executed = should_evaluate  # Set whether this block was executed
                else:
                    should_evaluate = False

            elif line.startswith('ELSE'):
                if not block_stack:
                    raise ValueError(f"ELSE without matching IF in: {line}")

                # Check if any block before this has already executed
                _, prev_block_executed = block_stack[-1]
                should_evaluate = not block_executed and not prev_block_executed
                block_executed = should_evaluate  # Set block_executed to True if this block is executed

            elif line.startswith('ENDIF'):
                if not block_stack:
                    raise ValueError(f"ENDIF without matching IF in: {line}")
                # Pop the block state from the stack
                should_evaluate, block_executed = block_stack.pop()

            elif 'alert.' in line:
                if should_evaluate:
                    execute_actions.append(line.strip())

            elif '=' in line:
                var_name, expr = line.split('=', 1)
                var_name = var_name.strip()
                expr = expr.strip()
                self.variables[var_name] = eval(expr, {}, {**self.context_dict, **self.variables})
                print(f"Variable assignment: {var_name} = {self.variables[var_name]}")

        if block_stack:
            raise ValueError(f"Unmatched IF/ENDIF block: {block_stack}")

        for action in execute_actions:
            if action == "alert.email":
                print("Email sent")
            elif action == "alert.sms":
                print("SMS sent")
            elif action == "alert.mail":
                print("Mail sent")
            elif action == "alert.web":
                print("WEB ALERT sent")
            else:
                print("Unidentified action")

        return execute_actions



"""
Final
"""