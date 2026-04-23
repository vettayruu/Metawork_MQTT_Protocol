import paho.mqtt.client as mqtt
import time
import ssl


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Successfully connected to liust.local via WebSockets")
        # 订阅所有主题
        client.subscribe("#")
    else:
        print(f"Connection failed with code {rc}")


def on_message(client, userdata, msg):
    # 获取毫秒级时间戳
    time_MQTT = int(time.time() * 1000)
    try:
        payload = msg.payload.decode()
    except:
        payload = "[Binary Data]"

    print(f"Time_Receive: {time_MQTT} | Topic: {msg.topic} | Payload: {payload}")


# --- 核心修改部分 ---

# 1. 必须指定使用 websockets 传输
client = mqtt.Client(transport="websockets")

# 2. 启用 TLS (因为你 Nginx 开启了 HTTPS/WSS)
# cert_reqs=ssl.CERT_NONE 表示忽略自签名证书的验证错误（非常关键，否则会连接失败）
client.tls_set(cert_reqs=ssl.CERT_NONE)

# 3. 设置 Nginx 对应的 WebSocket 路径
# 如果你在 Nginx 中配置的是 location /mqtt，那么这里必须对应
client.ws_set_options(path="/mqtt")

client.on_connect = on_connect
client.on_message = on_message

# 4. 连接到你的域名，端口使用 Nginx 的 443
# 注意：不需要填 1883 或 9001，因为 Nginx 会帮你转发
try:
    client.connect("liust.local", 443, 60)
except Exception as e:
    print(f"Could not connect: {e}")

client.loop_forever()