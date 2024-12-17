import time
import machine
import network

ssid = ""
password = ""


station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(ssid, password)

timeout = 10

while not station.isconnected() and timeout > 0:
    print("Connecting to Wi-Fi")
    time.sleep(1)
    timeout -= 1
if station.isconnected():
    print("Connection success")
    print(station.ifconfig())
else:
    print("Failed to connect, restarting")
    machine.reset()