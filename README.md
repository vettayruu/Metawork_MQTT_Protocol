# Uclab's Metawork MQTT Protocol

<div align="center">
  <image src="./MQTT_Protocol.png" type="application/pdf" width="1000" height="600" />
  <p><em>Figure 1: Uclab's Metawork MQTT Protocol.</em></p>
</div>

## Quick Start
- [Protocal Architecture](#protocol-architecture)
- [Build Your MQTT Broker](#build-your-mqtt-broker)
- [Communication and Deployment](#communication-and-deployment)

---

## Protocol Architecture
The communication and control architecture consists of four primary components designed to decouple high-level user input from low-level robot execution.

### 1. MQTT Manager
* **Role:** Orchestrator & Handshake Provider.
* **Responsibility:** Manages the registration of available robots and active users. It performs the **handshake** logic to pair a User Client with a compatible Robot based on robot type and availability.

### 2. User Client (e.g., Quest 3 / VR Interface)
* **Role:** High-Level Controller.
* **Responsibility:** Captures user intent (e.g., hand tracking or controller input), calculates the necessary control targets (such as **Inverse Kinematics** or joint positions), and publishes these control messages to the MQTT broker.

### 3. MQTT Client
* **Role:** Communication Bridge & Data Relay.
* **Responsibility:** Subscribes to the control topics from the User Client. It extracts the incoming data and writes it directly into **Shared Memory**, acting as a high-speed interface between the asynchronous network layer and the synchronous robot control layer.

### 4. Robot (Physical/Simulated)
* **Role:** Low-Level Controller.
* **Responsibility:** Reads the control setpoints from **Shared Memory** at a fixed frequency. It executes the motor commands (Low-Level Control) to drive the physical hardware or the simulation engine, ensuring stable and deterministic motion.

---

## Communication Sequence

### Phase 1: Registration & Handshake
The **User Client** and the **MQTT Client** (Robot side) register their metadata with the **Manager** upon startup. The Manager validates the connection based on the robot model and requested hardware capabilities to ensure compatibility.
* **Key Topics:** `mgr/register`, `mgr/unregister`

### Phase 2: Session Initialization
The User sends a specific robot request to the Manager. Once a match is confirmed, the Manager assigns designated MQTT topics for the session. 
* **State Feedback:** The MQTT Client begins broadcasting the robot's real-time state at a **1 Hz** heartbeat.
* **Synchronization:** To ensure a smooth start, the system syncs the robot's current physical pose with the User's initial control pose (e.g., VR hand tracking origin).
* **Key Topics:** `mgr/request`, `dev/{user-id}`, `dev/{robot-id}`

### Phase 3: High-Level Command Transmission
The User Client transmits high-level control packets (e.g., **Joint Positions** or **IK Targets**) to the MQTT Client. The Client decodes these asynchronous messages and updates the corresponding segments in the **Shared Memory** buffer.
* **Key Topics:** `robot/{robot-id}`, `control/{robot-id}`

### Phase 4: Low-Level Control & Buffering
The **Shared Memory** acts as a critical decoupling layer between the volatile network environment and the deterministic robot hardware.

* **Jitter Mitigation & Stability:** Since network signals are inherently unstable, the buffer allows the **Low-Level Controller** to sample commands at a **fixed high frequency**. This ensures smooth interpolation and prevents jerky movements caused by network latency.
* **Architectural Decoupling:** By separating the communication logic (MQTT) from the execution logic, the system remains **language-agnostic**. The robot controller can be implemented in C++, Python, or any SDK-supported language without refactoring the network stack.

---

## Build Your MQTT Broker

### 1. Install Mosquitto

Download Mosquitto from the official website: [https://mosquitto.org/download/](https://mosquitto.org/download/)

On Windows, Mosquitto is usually installed in:
```
C:\Program Files\mosquitto
```

### 2. Configure Mosquitto

Open `mosquitto.conf` in the installation folder and add the following settings:

**WebSocket (non-secure, ws):**
```
listener 9001
protocol websockets
```
This enables WebSocket connections on port 9001.

**Secure WebSocket (wss):**

First, generate `.pem` certificates.

To generate self-certification files, in the folder `MQTT_Client` run
```bash
node .\generate-ssl-cert.js 
```

Then you can get `cert.pem` and `key.pem` self-certification files.

Copy `cert.pem` and `key.pem` to the installation folder, add the following lines to `mosquitto.conf`:
```
listener 8333
protocol websockets
certfile C:\Program Files\mosquitto\cert.pem
keyfile C:\Program Files\mosquitto\key.pem
allow_anonymous true
```
Port numbers (e.g., 9001, 8333) can be customized.

### 3. Verify the MQTT Broker

**Find your server address:**  
On Windows, run `ipconfig` in the terminal, and look for:

```
IPv4 Address. . . . . . . . . . . : 192.168.197.39
```

Use this IP together with your MQTT port. For example:
```
192.168.197.39:9001   (for ws)
192.168.197.39:8333   (for wss)
```

> ⚠️ **Important: Verify the MQTT port before MQTT communication.**  
> To verify, open your browser and go to your MQTT port. For example:
> ```
> https://192.168.197.39:8333
> ```

### 4. Start the MQTT Broker

After verifying, you can use your local MQTT server for communication in your local network.

**Run Mosquitto as Administrator:**
```
cd "C:\Program Files\mosquitto"
mosquitto -v
```

### 5. Test Your MQTT Broker

To test publishing a topic, navigate to the `MQTT` folder and run:

**Publish a test message:**
```bash
python local_mqtt_test_pub.py
```

**Subscribe to the test message:**
```bash
python local_mqtt_test_sub.py
```

To check all topics in MQTT, run:
```bash
python MQTT_Topic_list.py
```

---

## Communication and Deployment

### 1. Starting the Infrastructure
To initialize the communication layer, navigate to the `MQTT` directory and launch the components in the following order:
* **Start the Manager:**
```bash
  python MQTT_Manager.py
```

The Manager acts as the central orchestrator for user-robot pairing.
* **Start the Client:**
```bash
  python MQTT_Client.py
```
*The Client creates shared memories and establishes the bridge between the MQTT Client and the Robot Low-Level Controller.*

### 2. Lifecycle & Heartbeat Monitoring
The MQTT Client maintains a persistent heartbeat to ensure system reliability:

* **State Broadcasting:**
The Client publishes robot state messages at a 1 Hz. This serves as a "keep-alive" signal and a monitor of the robot's connectivity and health.

### 3. User Client Synchronization
On the User Client side (e.g., Quest 3 / VR interface):

* **Session Initialization:** Upon every new Robot Request, the system performs an automatic state synchronization. This ensures the virtual control environment (initial pose) aligns with the robot's current physical configuration before teleoperation begins.

* **Live Updates:** The interface consumes the 1 Hz state messages to reflect the current robot status to the user.


