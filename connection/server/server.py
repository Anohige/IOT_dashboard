from flask import Flask, jsonify, request
from flask_cors import CORS
from DB_Manager.db_manager import DBManager

class Server:
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for cross-origin requests
        self.db_manager = DBManager()

        # GET endpoint for devices
        @self.app.route('/devices', methods=['GET'])
        def get_devices():
            query = "SELECT * FROM devices"
            results = self.db_manager.execute_query(query, fetch=True)
            return jsonify(results if results else []), 200

        # POST endpoint to create a new device in the "devices" table
        @self.app.route('/devices', methods=['POST'])
        def create_device():
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400

            query = """
                INSERT INTO devices (name, type, device_serial, area, building, floor)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                data.get('name'),
                data.get('type'),
                data.get('device_serial'),
                data.get('area'),
                data.get('building'),
                data.get('floor')
            )
            self.db_manager.execute_query(query, values=values, fetch=False)
            return jsonify({"message": "Device created successfully"}), 201

        # Endpoint to fetch available device serials from the "iot_devices" table
        @self.app.route('/iot_devices', methods=['GET'])
        def get_iot_devices():
            query = "SELECT * FROM iot_devices"
            results = self.db_manager.execute_query(query, fetch=True)
            return jsonify(results if results else []), 200

    def run(self, host='0.0.0.0', port=5001):
        self.app.run(host=host, port=port, debug=True)
