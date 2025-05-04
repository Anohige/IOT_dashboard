from flask import Flask, jsonify, request
from flask_cors import CORS
from DB_Manager.db_manager import DBManager
import logging
import os
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Server:
    def __init__(self, db_manager=None, daq=None):
        self.app = Flask(__name__)

        # Enable CORS for all origins with more options
        CORS(self.app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

        # Use provided DB manager or create a new one
        self.db_manager = db_manager if db_manager else DBManager()

        # Store DAQ instance
        self.daq = daq

        # Device info file path
        self.device_info_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "device_info.json"
        )

        # GET endpoint for devices
        @self.app.route('/devices', methods=['GET'])
        def get_devices():
            logger.info("GET /devices endpoint was called")
            # Log request information for debugging
            logger.info(f"Request headers: {request.headers}")

            # Check if there's a device_serial query parameter
            device_serial = request.args.get('device_serial')

            try:
                if device_serial:
                    # Get specific device
                    query = "SELECT * FROM devices WHERE device_serial = %s"
                    results = self.db_manager.execute_query(query, values=(device_serial,), fetch=True)
                else:
                    # Get all devices
                    query = "SELECT * FROM devices"
                    results = self.db_manager.execute_query(query, fetch=True)

                logger.info(f"Query returned {len(results) if results else 0} results")
                return jsonify(results if results else []), 200
            except Exception as e:
                logger.error(f"Error in get_devices: {e}")
                return jsonify({"error": str(e)}), 500

        # POST endpoint to create a new device in the "devices" table
        @self.app.route('/devices', methods=['POST'])
        def create_device():
            logger.info("POST /devices endpoint was called")
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400

            # If no device_serial is provided, try to get it from DAQ
            if 'device_serial' not in data and self.daq:
                data['device_serial'] = self.daq.get_rpi_serial()
                logger.info(f"Using device serial from DAQ: {data['device_serial']}")

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

            try:
                self.db_manager.execute_query(query, values=values, fetch=False)
                return jsonify({"message": "Device created successfully"}), 201
            except Exception as e:
                logger.error(f"Error creating device: {e}")
                return jsonify({"error": str(e)}), 500

        # PUT endpoint to update device details
        @self.app.route('/devices/<device_serial>', methods=['PUT'])
        def update_device(device_serial):
            logger.info(f"PUT /devices/{device_serial} endpoint was called")
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
                logger.error(f"Error updating device: {e}")
                return jsonify({"error": f"Failed to update device: {str(e)}"}), 500

        # DELETE endpoint to remove a device from the "devices" table
        @self.app.route('/devices/<device_serial>', methods=['DELETE'])
        def delete_device(device_serial):
            logger.info(f"DELETE /devices/{device_serial} endpoint was called")
            if not device_serial:
                return jsonify({"error": "No device serial provided"}), 400

            query = "DELETE FROM devices WHERE device_serial = %s"
            values = (device_serial,)

            try:
                self.db_manager.execute_query(query, values=values, fetch=False)
                return jsonify({"message": f"Device {device_serial} deleted successfully"}), 200
            except Exception as e:
                logger.error(f"Error deleting device: {e}")
                return jsonify({"error": f"Failed to delete device: {str(e)}"}), 500

        # Endpoint to fetch available device serials from the "iot_devices" table
        @self.app.route('/iot_devices', methods=['GET'])
        def get_iot_devices():
            logger.info("GET /iot_devices endpoint was called")
            try:
                query = "SELECT * FROM iot_devices"
                results = self.db_manager.execute_query(query, fetch=True)
                return jsonify(results if results else []), 200
            except Exception as e:
                logger.error(f"Error getting IoT devices: {e}")
                return jsonify({"error": str(e)}), 500

        # Get current device info
        @self.app.route('/device_info', methods=['GET'])
        def get_device_info():
            logger.info("GET /device_info endpoint was called")
            try:
                # Get device serial from DAQ if available
                device_serial = None
                if self.daq:
                    device_serial = self.daq.get_rpi_serial()
                    logger.info(f"Got device serial from DAQ: {device_serial}")

                # Build response object
                device_info = {}

                if device_serial:
                    device_info["device_serial"] = device_serial

                    # Try to get device details from database
                    query = "SELECT * FROM devices WHERE device_serial = %s"
                    device_results = self.db_manager.execute_query(
                        query,
                        values=(device_serial,),
                        fetch=True
                    )

                    if device_results and len(device_results) > 0:
                        # Add device details to response
                        device_info.update(device_results[0])

                # If we don't have a device_serial yet, try the device_info.json file
                if "device_serial" not in device_info and os.path.exists(self.device_info_file):
                    try:
                        with open(self.device_info_file, 'r') as f:
                            file_info = json.load(f)
                            if "device_serial" in file_info:
                                device_info.update(file_info)
                    except Exception as e:
                        logger.error(f"Error reading device_info.json: {e}")

                if device_info:
                    return jsonify(device_info), 200
                else:
                    return jsonify({"error": "No device information available"}), 404

            except Exception as e:
                logger.error(f"Error getting device info: {e}")
                return jsonify({"error": f"Failed to get device info: {str(e)}"}), 500

        @self.app.after_request
        def after_request(response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response

    def run(self, host='0.0.0.0', port=5001, debug=True):
        logger.info(f"Starting server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

