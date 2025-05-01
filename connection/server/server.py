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
            print("DEBUG: GET /devices endpoint was called")

            # Check if there's a device_serial query parameter
            device_serial = request.args.get('device_serial')

            if device_serial:
                # Get specific device
                query = "SELECT * FROM devices WHERE device_serial = %s"
                results = self.db_manager.execute_query(query, values=(device_serial,), fetch=True)
            else:
                # Get all devices
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

        # PUT endpoint to update device details
        @self.app.route('/devices/<device_serial>', methods=['PUT'])
        def update_device(device_serial):
            print(f"DEBUG: PUT /devices/{device_serial} endpoint was called")
            data = request.json

            if not data:
                return jsonify({"error": "No data provided"}), 400

            query = """
                UPDATE devices 
                SET name = %s, type = %s, area = %s, building = %s, floor = %s
                WHERE device_serial = %s
            """
            values = (
                data.get('name'),
                data.get('type'),
                data.get('area'),
                data.get('building'),
                data.get('floor'),
                device_serial
            )

            try:
                self.db_manager.execute_query(query, values=values, fetch=False)
                return jsonify({"message": f"Device {device_serial} updated successfully"}), 200
            except Exception as e:
                print(f"Error updating device: {e}")
                return jsonify({"error": f"Failed to update device: {str(e)}"}), 500

        # DELETE endpoint to remove a device from the "devices" table
        @self.app.route('/devices/<device_serial>', methods=['DELETE'])
        def delete_device(device_serial):
            print(f"DEBUG: DELETE /devices/{device_serial} endpoint was called")
            if not device_serial:
                return jsonify({"error": "No device serial provided"}), 400

            query = "DELETE FROM devices WHERE device_serial = %s"
            values = (device_serial,)

            try:
                self.db_manager.execute_query(query, values=values, fetch=False)
                return jsonify({"message": f"Device {device_serial} deleted successfully"}), 200
            except Exception as e:
                print(f"Error deleting device: {e}")
                return jsonify({"error": f"Failed to delete device: {str(e)}"}), 500

        # Endpoint to fetch available device serials from the "iot_devices" table
        @self.app.route('/iot_devices', methods=['GET'])
        def get_iot_devices():
            query = "SELECT * FROM iot_devices"
            results = self.db_manager.execute_query(query, fetch=True)
            return jsonify(results if results else []), 200

    def run(self, host='0.0.0.0', port=5001):
        self.app.run(host=host, port=port, debug=True)