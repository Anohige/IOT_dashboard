# main.py

import time
from dependency_injector import DependencyInjector
from agents.rules.rule_agent import RuleAgent

def main():
    print("Initializing dependencies...")
    di = DependencyInjector()

    print("Starting MQTT client in non-blocking mode...")
    di.start_mqtt_client()       # now calls connect_and_loop()

    print("Connecting to DAQ...")
    di.start_daq()

    print("Starting Server...")
    di.start_server()

    print("Ready to evaluate rules.")
    agent = RuleAgent(rules_file_path=di.file_manager.rules_file)

    try:
        while True:
            choice = input("Do you want to evaluate rules (Y/N): ").strip().lower()
            if choice == "y":
                agent.start()  # loads rules.json + runs your logic
                print("Rules evaluation done. Sleeping 5 seconds...")
                time.sleep(5)
            elif choice == "n":
                print("Waiting 10 seconds...")
                time.sleep(10)
            else:
                print("Invalid input. Please type Y or N.")
    except KeyboardInterrupt:
        print("Shutting down...")

        # Cleanly stop MQTT
        di.mqtt_client.client.loop_stop()
        di.mqtt_client.client.disconnect()
        print("MQTT client stopped.")


if __name__ == "__main__":
    main()