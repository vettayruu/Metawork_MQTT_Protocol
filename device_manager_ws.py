from flask import Flask, request, jsonify, Response
from flask_socketio import SocketIO, emit
from collections import deque

import ssl
import time
import json
import paho.mqtt.client as mqtt


class DeviceManager:
    def __init__(self, host="liust.local", port=443, timeout_limit=5000):
        self.host = host
        self.port = port
        self.timeout_limit = timeout_limit

        self.devices = {}

        self.client = mqtt.Client(transport="websockets")
        self.client.tls_set(cert_reqs=ssl.CERT_NONE)
        self.client.ws_set_options(path="/mqtt")

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.running = True

    def start(self):
        try:
            print(f"🔄 Connecting to {self.host}:{self.port} via WSS...")
            self.client.connect(self.host, self.port, 60)
            self.client.loop_start()
            print("🚀 Device Manager started successfully.")
        except Exception as e:
            print(f"❌ Connection failed: {e}")

    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        print("🛑 Device Manager stopped.")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Successfully connected to {self.host} via WebSockets")
            self.client.subscribe("mgr/register")
            self.client.subscribe("mgr/unregister")
        else:
            print(f"❌ Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        str_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        try:
            payload_str = msg.payload.decode()
            data = json.loads(payload_str)
        except Exception:
            print(f"⚠️ Receive non-JSON or invalid data on {msg.topic}")
            return

        if isinstance(data, list):
            if len(data) > 0:
                data = data[0]
            else:
                print(f"⚠️ Receive an empty list on {msg.topic}")
                return

        dev_type = data.get("devType", "unknown")
        dev_id = data.get("devId", "unknown")
        dev_model = data.get("type", "unknown")
        dev_status = data.get("optStr", "unknown")

        if msg.topic == "mgr/register":
            self._handle_register(str_time, dev_type, dev_id, dev_model, dev_status)
        elif msg.topic == "mgr/unregister":
            self._handle_unregister(dev_id)

    def _handle_register(self, str_time, dev_type, dev_id, dev_model, dev_status):
        self.devices[dev_id] = {
            "time": str_time,
            "devType": dev_type,
            "devID": dev_id,
            "devModel": dev_model,
            "devStatus": dev_status,
        }
        print(f"➕ [REGISTER] {dev_type.upper()} '{dev_id}' registered. Status: {dev_status}")
        self.print_device_table()

    def _handle_unregister(self, dev_id):
        if dev_id in self.devices:
            dev_type = self.devices[dev_id].get("devType")
            del self.devices[dev_id]
            print(f"➖ [UNREGISTER] {dev_type.upper()} '{dev_id}' logged out gracefully.")
            self.print_device_table()

    def print_device_table(self):
        print("\n=== Current Active Devices ===")
        if not self.devices:
            print("No devices connected.")
        else:
            print(f"{'Time':<25} | {'ID':<45} | {'Device Type':<15} | {' Model':<25} | {'Status':<10}")
            print("-" * 110)

            for dev_id, info in self.devices.items():
                dev_time_recv = info["time"]
                d_type = info["devType"]
                d_model = info["devModel"]
                d_status = info["devStatus"]
                print(f"{dev_time_recv:<25} | {dev_id:<45} | {d_type:<15} | {d_model:<25} | {d_status:<10}")
        print("==============================\n")

        robot_dev_json = self.get_device_json()

        # Save on local
        with open("active_devices.json", "w", encoding="utf-8") as f:
            f.write(robot_dev_json)

    def get_device_json(self):
        device_list = []
        for dev_id, info in self.devices.items():
            device_node = {
                "time": info.get("time"),
                "id": dev_id,
                "type": info.get("devType"),
                "model": info.get("devModel"),
                "status": info.get("devStatus")
            }
            device_list.append(device_node)
        return json.dumps(device_list, ensure_ascii=False, indent=2)


# --- Initialize Flask & SocketIO ---
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

latest_messages = deque(maxlen=10)

manager = DeviceManager(host="liust.local", port=443, timeout_limit=5000)

@app.route('/offer', methods=['GET', 'POST'])
def handle_offer():
    if request.method == 'GET':
        robot_dev_json = manager.get_device_json()
        return Response(robot_dev_json, mimetype='application/json'), 200

    else:
        data = request.json
        if not data:
            return jsonify({"status": "error"}), 400

        print(f"📩 BTP Message: {data}")
        socketio.emit(
            'btp_action',
            data,
            namespace='/ws'
        )

        return jsonify({
            "status": "dispatched",
            "data": data
        }), 200


# --- WebSocket Connect Test ---
@socketio.on('connect', namespace='/ws')
def test_connect():
    print("🤖 Robot Connected by WebSocket.")
    emit('response', {'data': 'Connected'})


if __name__ == '__main__':
    # Start MQTT Firstly
    manager.start()

    try:
        print("🌐 Starting Flask-SocketIO server on port 8080...")
        socketio.run(app, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop()