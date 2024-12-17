import paho.mqtt.client as mqtt
from time import sleep

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, )
mqtt_server = "192.168.43.12"
mqtt_port = 1883
client_id = "ESP-32"
topic_pub = b"iot3"
data = "Hej med dig"
while True:
        try:
                client.connect("192.168.43.12", 1883, 60)
                client.publish(topic_pub, str(data))
                print("Published data:", data)
        except Exception as e:
            print("Failed to publish data:", e)
        sleep(5)