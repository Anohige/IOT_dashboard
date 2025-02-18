from flask import Flask, jsonify, request
from flask_cors import CORS  # Only needed if your frontend is on a different origin
from DB_Manager.db_manager import DBManager

class Server:
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS if needed
        self.db_manager = DBManager()

        @self.app.route('/devices', methods=['GET'])
        def get_devices():
            """
            Returns a list of all devices in the 'devices' table.
            """
            query = "SELECT * FROM devices"
            results = self.db_manager.execute_query(query, fetch=True)
            # If 'results' is None or empty, return an empty list
            return jsonify(results if results else []), 200

        # Example: If you want to add a route to create a new device
        # (assuming you handle form data or JSON from the frontend)
        @self.app.route('/devices', methods=['POST'])
        def create_device():
            """
            Creates a new device in the 'devices' table based on JSON data from the frontend.
            """
            data = request.json  # e.g., { "name": "...", "type": "...", etc. }
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

    def run(self, host='0.0.0.0', port=5001):
        """
        Runs the Flask server.
        """
        self.app.run(host=host, port=port, debug=True)
