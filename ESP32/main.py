# https://microcontrollerslab.com/esp32-micropython-mqtt-publish-subscribe/


from umqttsimple import MQTTClient
import machine
from machine import I2C, Pin, ADC, Timer, PWM
import time
import mpu6050
import json
# Objects for sensorer og variabler
i2c = I2C(scl=Pin(22), sda=Pin(21))
mpu = mpu6050.MPU6050(i2c) 

battery_pin = ADC(Pin(34)) 
battery_pin.atten(ADC.ATTN_11DB) 

adc = ADC(Pin(35)) 
adc.atten(ADC.ATTN_11DB) 
# Vibrationsmotor
vibr = PWM(Pin(27), freq=1000)
vibr.duty(0)
last_execution = time.time()
vibration_running = False


# Variabler
mqtt_server = "192.168.43.12"
mqtt_port = 1883
client_id = "ESP-32"
topic_pub = "iot3"
# Batteri
R1 = 6000
R2 = 8000
v_ref = 3.3
maxadc = 4095
v_min = 3.0
v_max = 4.2
# Puls variabler
history = []
beats = []
beat = False
bpm = None
MAX_HISTORY = 200
TOTAL_BEATS = 30
#Funktioner:

def calculate_bpm(beats):
    if beats:
        beat_time = beats[-1] - beats[0]
        if beat_time:
            return (len(beats) / (beat_time)) * 60
    
def get_batteryprocent(): 
    raw = battery_pin.read()
    v_out = raw * (v_ref / maxadc)
    vbat = v_out * ((R1 + R2) / R2)
    procent = (vbat - v_min) / (v_max - v_min) * 100
    procent = max(0, min(procent, 100))
    return procent


def stabilizer_against_flunct(buffer):
    return sum(buffer) / len(buffer)


def gyrometer():
    gyrodata = mpu.get_values()
    data = {
        "GyroX": gyrodata["GyroX"],
        "GyroY": gyrodata["GyroY"],
        "GyroZ": gyrodata["GyroZ"]
    }
    return data
        
def connect():
    print("Connecting to MQTT Broker")
    client = MQTTClient(client_id=client_id, server = mqtt_server, port = mqtt_port)
    client.connect()
    print("Connected to %s MQTT Broker" %(mqtt_server))
    return client
    


def publishdata(client, data):
    try:
        json_data = json.dumps(data)
        client.publish(topic_pub, json_data)
    except Exception as e:
        print("Failed to publish data:", e)
def vibmotor():
    global last_execution, vibration_running
    current_time = time.time()
    #sæt til 86400 for at få 24 timer
    if current_time - last_execution >= 60:  
        vibration_running = True
        vibr.duty(1023)  
        time.sleep(15)   
        vibr.duty(0)     
        
        last_execution = current_time
        vibration_running = False

try:
    client = connect()
except OSError as e:
    print("Failed to connect to MQTT. Retrying")
    time.sleep(5)
    client = connect()
    
while True:
    try:
        v = adc.read()
        history.append(v)
        history = history[-MAX_HISTORY:]
        minima, maxima = min(history), max(history)
        threshold_on = (minima + maxima * 3) // 4   # 3/4
        threshold_off = (minima + maxima) // 2      # 1/2
        if v > threshold_on and beat == False:
            beat = True
            beats.append(time.time())
            beats = beats[-TOTAL_BEATS:]
            bpm = calculate_bpm(beats)
            batprocent = get_batteryprocent()
            gyro = gyrometer()
            data = {
            "BatteryPercentage": batprocent,
            "HeartRate": bpm,
            "Gyroscope": gyro
            }

            publishdata(client, data)
            time.sleep(0.5)
        if v < threshold_off and beat == True:
            beat = False
        vibmotor()

    except KeyboardInterrupt:
        print("Ctrl-C detected, exiting...")
        break
    except Exception as e:
        print("Error reading sensors or publishing data:", e)
        time.sleep(1)