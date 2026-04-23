# Guide: Setting up Nginx as a Reverse Proxy for MQTT & WebRTC

Using Nginx as a reverse proxy allows you to use a consistent domain name (like `liust.local`), eliminating the need to update the IP address in your robot or VR client every time it changes.

## 1. Installation and Management (Windows)

Download the Nginx Windows version and extract it. Open a terminal in the installation folder:

- **Start Nginx**
```bash
start nginx
```

- **Stop Nginx**
```
taskkill /f /im nginx.exe
```

- **Apply Config Changes:**
Nginx must be restarted or reloaded every time the `nginx.conf` is modified.

- **Troubleshooting:**
If the `nginx.exe` process disappears after a restart, there is a configuration error. Check `\logs\error.log` for details.

## 2.Setting Up a Local Domain (.local)
To use a custom local domain, you must change your PC's hostname:
1. Press `Win + I` to open Settings.
2. Go to System -> About -> Rename this PC.
3. Note: It may take some time for the new name to propagate through the local network (mDNS). A restart is usually required.

## 3.SSL Certificate Trust (Critical for VR)
Browsers (especially on VR headsets like Quest 3) will block WebSocket connections (wss://) if the SSL certificate is self-signed or not trusted.

- **For MQTT (via WebSockets):** Open https://liust.local/mqtt (or your specific path) in the VR browser first. Click "Advanced" and "Proceed" to manually trust the certificate for that session.
- **For WebRTC (Sora):** Similarly, visit https://sora2.uclab.jp/signaling to authorize the connection before launching your application.
- 
