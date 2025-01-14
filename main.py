# main.py

import time
from dependency_injector import DependencyInjector  # or however you set it up
from agents.rules.rule_agent import RuleAgent

def main():
    print("Initializing dependencies...")
    di = DependencyInjector()  # This creates MqttClient & FileManager, etc.

    print("Starting MQTT client in non-blocking mode...")
    di.mqtt_client.connect_and_loop()  # This will call loop_start()

    # Create or instantiate your RuleAgent.
    # (If the agent depends on incoming MQTT data,
    #  make sure that data is stored or accessible.)
    agent = RuleAgent(rules_file_path="rules.json")

    try:
        while True:
            # Evaluate rules every 5 seconds
            agent.start()  # load_rules() + evaluate_rules()
            print("Rules evaluation done. Sleeping 5 seconds...")
            time.sleep(10)
    except KeyboardInterrupt:
        print("Shutting down...")

        # Stop the MQTT loop gracefully
        di.mqtt_client.client.loop_stop()
        di.mqtt_client.client.disconnect()
        print("MQTT client stopped.")


if __name__ == "__main__":
    main()