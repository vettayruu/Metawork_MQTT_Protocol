import json
import time
from datetime import datetime
import numpy as np
from paho.mqtt import client as mqtt
import multiprocessing.shared_memory as sm

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
ROBOT_MODEL = os.getenv("ROBOT_MODEL","Unitree-G1-control-LIU")
ROBOT_UUID = os.getenv("ROBOT_UUID","Unitree-G1-control-LIU")

MQTT_MANAGE_TOPIC = os.getenv("MQTT_MANAGE_TOPIC", "mgr")
MQTT_MANAGE_RCV_TOPIC = os.getenv("MQTT_MANAGE_RCV_TOPIC", "dev")
MQTT_MANAGE_EVENT_TOPIC = os.getenv("MQTT_MANAGE_EVENT_TOPIC", "mgr/event")

MQTT_CTRL_TOPIC = os.getenv("MQTT_CTRL_TOPIC", "control")
MQTT_ROBOT_STATE_TOPIC = os.getenv("MQTT_ROBOT_STATE_TOPIC", "robot")

MQTT_LOCAL_SERVER = "192.168.197.36"
MQTT_LOCAL_PORT = 8333
MQTT_UCLAB_SERVER = "sora2.uclab.jp"
MQTT_UCLAB_PORT = 1883

class MQTT_Client():
    def __init__(self, MQTT_Mode):
        self.mode = MQTT_Mode

        self.client = None
        self.USER_UUID = None
        self.MQTT_CTRL_TOPIC = f"{MQTT_CTRL_TOPIC}/{ROBOT_UUID}"
        self.MQTT_RECV_TOPIC = f"{MQTT_MANAGE_RCV_TOPIC}/{ROBOT_UUID}"

        self.left_arm_joints_ctrl = np.zeros(8)
        self.left_hand_joints_ctrl = np.zeros(8)
        self.right_arm_joints_ctrl = np.zeros(8)
        self.right_hand_joints_ctrl = np.zeros(8)

        self.shm_handles = {}
        self.shm_arrays = {}
        self.shm_name_list = ['Left_Arm', 'Left_Hand', 'Right_Arm', 'Right_Hand']

    def on_connect(self, client, userdata, flags, rc):
        # For register
        date = datetime.now().strftime('%c')
        my_info = {
            "date": date,
            "devType": "robot",
            "type": ROBOT_MODEL,
            "version": "0.1",
            "devId": ROBOT_UUID
        }
        self.client.publish("mgr/register", json.dumps(my_info))
        print("Publish Robot info to MQTT manager:", json.dumps(my_info))

        self.client.subscribe(self.MQTT_RECV_TOPIC)  # connected -> subscribe
        print(f"Subscribe Controller info from {self.MQTT_RECV_TOPIC}")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print("Unexpected disconnection.")

    def on_message(self, client, userdata, msg):
        if msg.topic == self.MQTT_RECV_TOPIC:
            try:
                controller_msg = json.loads(msg.payload.decode())
                from_dev_id = controller_msg["devId"]

                # Subscribe as first request or different robot request
                if from_dev_id and from_dev_id != self.USER_UUID:
                    print(f"------------------ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))} -------------------")
                    print(f"🎯 Capture New Control Request: {from_dev_id}")

                    # If old subscribe exists, unsubscribe
                    if self.USER_UUID:
                        self.client.unsubscribe(self.MQTT_CTRL_TOPIC)

                    self.USER_UUID = from_dev_id
                    self.MQTT_CTRL_TOPIC = f"{MQTT_CTRL_TOPIC}/{self.USER_UUID}"

                    # Subscribe control topics
                    topics_to_sub = [
                        self.MQTT_CTRL_TOPIC,
                    ]
                    for t in topics_to_sub:
                        self.client.subscribe(t)
                        print(f"📡 Subscribe Control Topic: {t}")

            except Exception as e:
                print(f"❌ Subscribe {self.MQTT_RECV_TOPIC} failed: {e}")
            return

        try:
            if msg.topic == self.MQTT_CTRL_TOPIC:
                # Message: {timestamp, devId, left: {arm, hand}, right: {arm, hand}}
                ctrl_msg = json.loads(msg.payload.decode())

                self.left_arm_joints_ctrl[0:8] = ctrl_msg['left']['arm']
                self.left_hand_joints_ctrl[0:7] = ctrl_msg['left']['hand']
                self.right_arm_joints_ctrl[0:8] = ctrl_msg['right']['arm']
                self.right_hand_joints_ctrl[0:7] = ctrl_msg['right']['hand']

                self.update_shm_ctrl("Left_Arm", self.left_arm_joints_ctrl)
                self.update_shm_ctrl("Left_Hand", self.left_hand_joints_ctrl)
                self.update_shm_ctrl("Right_Arm", self.right_arm_joints_ctrl)
                self.update_shm_ctrl("Right_Hand", self.right_hand_joints_ctrl)

        except Exception as e:
            print(f"⚠️ Data Receive Error: {msg.topic}, {e}")

    def connect_mqtt(self):
        if self.mode == "local":
            self.client = mqtt.Client(
                # callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                transport="websockets"
            )
            self.client.tls_set(cert_reqs=0)
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            self.client.connect(MQTT_LOCAL_SERVER, MQTT_LOCAL_PORT, 60)
            self.client.loop_start()

        elif self.mode == "uclab":
            self.client = mqtt.Client(
                # callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            )
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            self.client.connect(MQTT_UCLAB_SERVER, MQTT_UCLAB_PORT, 60)
            self.client.loop_start()

    def create_shared_memories(self):
        for name in self.shm_name_list:
            try:
                # 每个分配 16 * 4 bytes (float32)
                shm = sm.SharedMemory(name=name, create=True, size=16 * 4)
                print(f"✅ Shared memory '{name}' created.")
            except FileExistsError:
                shm = sm.SharedMemory(name=name)
                print(f"ℹ️ Shared memory '{name}' already exists, attached.")

            self.shm_handles[name] = shm
            # 将 numpy 数组直接绑定到字典，方便后续直接通过名字写入
            self.shm_arrays[name] = np.ndarray((16,), dtype=np.float32, buffer=shm.buf)
            self.shm_arrays[name][:] = 0  # 初始化归零

    def update_shm_ctrl(self, name, target_data):
        if name in self.shm_arrays:
            target_array = np.array(target_data, dtype=np.float32).flatten()[:8]
            self.shm_arrays[name][0:8] = target_array
        else:
            print(f"❌ Error: Shared memory '{name}' not initialized.")

    def update_shm_robot(self, name, robot_data):
        if name in self.shm_arrays:
            feedback_array = np.array(robot_data, dtype=np.float32).flatten()[:8]
            self.shm_arrays[name][8:16] = feedback_array
        else:
            print(f"❌ Error: Shared memory '{name}' not initialized.")

    def close_all_shm(self):
        """程序退出时清理"""
        for name, shm in self.shm_handles.items():
            shm.close()
            # Note：Shared Memory's Creater should use unlink()
            shm.unlink()
        print("🧹 All Shared Memory handles closed.")

    def publish_robot_state(self):
        try:
            robot_msg = {
                "header": {
                    "timestamp": int(time.time()*1000),
                    "devId": ROBOT_UUID
                },
                "left": {
                    "arm": self.shm_arrays['Left_Arm'][8:16].tolist(),
                    "hand": self.shm_arrays['Left_Hand'][8:15].tolist(),
                },
                "right": {
                    "arm": self.shm_arrays['Right_Arm'][8:16].tolist(),
                    "hand": self.shm_arrays['Right_Hand'][8:15].tolist(),
                }
            }

            # Quality of Service set as qos=0
            self.client.publish(
                f"{MQTT_ROBOT_STATE_TOPIC}/{ROBOT_UUID}",
                json.dumps(robot_msg),
                qos=0
            )
        except KeyError as e:
            print(f"⚠️ SHM Key not found: {e}")


if __name__ == '__main__':
    mode = "local" # "local" or "uclab"
    client = MQTT_Client(mode)
    client.create_shared_memories()
    client.connect_mqtt()

    try:
        # Keep MQTT Client alive
        while True:
            client.publish_robot_state()
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        client.close_all_shm()