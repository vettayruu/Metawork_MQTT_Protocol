# Web-Based VR Teleoperation System

<div align="center">
  <image src="./MQTT_Protocal.png" type="application/pdf" width="800" height="600" />
  <p><em>Figure 1: Uclab's MQTT Protocal.</em></p>
</div>

## MQTT Manager

## MQTT Client

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

To test publishing a topic, navigate to the `MQTT_Client` folder and run:

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
