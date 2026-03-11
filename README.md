# Uclab's Metawork MQTT Protocol

<div align="center">
  <image src="./MQTT_Protocol.png" type="application/pdf" width="1000" height="600" />
  <p><em>Figure 1: Uclab's Metawork MQTT Protocol.</em></p>
</div>

## Quick Start
- [Protocal Architecture](#protocol-architecture)
- [Build Your MQTT Broker](#build-your-mqtt-broker)
- [Communication and Deployment](#communication-and-deployment)
- [How to use shared memory](#how-to-use-shared-memory)
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
* **Key Topics:** `robot/{robot-id}`, `control/{user-id}`

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

---

## How to use shared memory
The scripts `MQTT_Simulation_Left.py` and `MQTT_Simulation_Right.py` demonstrate how to interface with the robot using shared memory.

In `MQTT_Client.py`, four shared memory segments are initialized: `Left_Arm`, `Left_Hand`, `Right_Arm`, `Right_Hand`. 
Each segment acts as a zero-copy bridge between the MQTT network layer and the local control loop.

### 1. Accessing Shared Memory
To access an existing memory segment created by another process, use the `name` identifier:

```Python
from multiprocessing import shared_memory
import numpy as np

# Attach to the existing memory segments
shm_left_arm = shared_memory.SharedMemory(name='Left_Arm')
shm_left_hand = shared_memory.SharedMemory(name='Left_Hand')
```

### 2. Mapping to NumPy Arrays
Map the raw memory buffer to a NumPy array for easy manipulation. 
In this project, we use a 16-element float32 array (64 bytes total) where the data is typically split into Target and Actual states.

```Python
# Create numpy arrays mapped directly to the shared buffer
# Shape (16,) allows for 8 target values and 8 feedback values
arm_data = np.ndarray((16,), dtype=np.float32, buffer=shm_left_arm.buf)
hand_data = np.ndarray((16,), dtype=np.float32, buffer=shm_left_hand.buf)
```

**Shared Memory Mapping** is the most critical step. It does **not** "copy" the data; instead, it creates a NumPy array **mapping directly** onto the shared memory segment.
* Shape `(16,)`: Defines the array structure. It tells NumPy that this memory segment contains a sequence of 16 numbers.
* `dtype=np.float32`: Defines the data type. Since each `float32` occupies 4 bytes, the 16 numbers together consume exactly 64 bytes of memory.
* `buffer=shm_left_arm.buf`: The most vital parameter. It instructs NumPy **not** to allocate its own new memory, but to use the raw binary stream (`buf`) of the shared memory block as its data source.

### 3. Data Layout & Usage
The data within the 16-element array is organized by index offsets:

| Index Range | Purpose | Description |
| :--- | :--- | :--- |
| `[0:8]` | **Target** | Joint Positions received from MQTT |
| `[8:16]` | **Actual** | Real-time feedback from the robot |

**Reading Targets (Input to Control)**
In your control loop, copy the target data to avoid race conditions during calculations:

```Python
# Extract target positions
thetaBody_Target = arm_data[0:8].copy() # 0 for waist, 1-7 for arm. The waist joint is currently not used.
thetaTool_Target = hand_data[0:7].copy() # 0-2 for thumb, 3-4 for middle, 5-6 for index
```

**Writing Feedback (Output to Monitor)**
```Python
# Update robot feedback to shared memory
arm_data[8:16] = sim.get_joint_position()  # Expecting 8 values
hand_data[8:15] = sim.get_tool_position()   # Expecting 7 values
```

**Clean Up**
When the process exits, remember to close the connection to the shared memory:
```Python
shm_left_arm.close()
shm_left_hand.close()
```
**Note**: The array size and offsets must be strictly consistent across all processes. 
If you change the robot's DOF (Degrees of Freedom), ensure the ndarray shape and the buffer size in `MQTT_Client.py` are updated accordingly.
