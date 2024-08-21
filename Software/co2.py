import time
import busio
import adafruit_scd30
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import threading
import json

# Initialize I2C using GPIO 0 (ID_SD) and GPIO 1 (ID_SC)
i2c_0 = busio.I2C(1, 0)
scd = adafruit_scd30.SCD30(i2c_0)

# Servo motor setup
SERVO_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz
pwm.start(0)

# MQTT setup
MQTT_BROKER = "your_mqtt_broker"  # Replace with your broker address
MQTT_PORT = 1884
MQTT_USERNAME = "your_username"   # Replace with your MQTT username
MQTT_PASSWORD = "your_password"   # Replace with your MQTT password
MQTT_TOPIC_DATA = "your_topic/OPS/blow/value"  # Replace with your data topic
MQTT_TOPIC_CONTROL = "your_topic/OPS/blow"     # Replace with your control topic
MQTT_SUBSCRIBE_TOPIC = "your_topic/T90/blow/value"  # Replace with your subscription topic

client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Continuous rotation function for the servo motor
def start_continuous_rotation():
    pwm.ChangeDutyCycle(10)  # Set duty cycle for continuous rotation, adjust based on servo specs

def stop_rotation():
    pwm.ChangeDutyCycle(0)  # Stop rotation

# CO₂ threshold settings
CO2_THRESHOLD_START = 3000  # Start rotating the servo motor when this level is exceeded
CO2_THRESHOLD_STOP = 2500   # Stop rotating the servo motor when the level drops below this

servo_active = False

def mqtt_publish(topic, message):
    print(f"Publishing to {topic}: {message}")  # Added print for debugging
    client.publish(topic, message)

def read_sensor_data():
    while True:
        if scd.data_available:
            co2 = scd.CO2
            temperature = scd.temperature
            humidity = scd.relative_humidity
            print(f"CO2: {co2:.0f} ppm, Temperature: {temperature:.1f} C, Humidity: {humidity:.1f} %")

            # Send CO₂, temperature, and humidity data to MQTT
            mqtt_message = json.dumps({
                "CO2": int(co2),
                "Temperature": round(temperature, 1),
                "Humidity": round(humidity, 1)
            })
            threading.Thread(target=mqtt_publish, args=(MQTT_TOPIC_DATA, mqtt_message)).start()

            # If CO2 exceeds the threshold, send a control message
            if co2 > CO2_THRESHOLD_START:
                threading.Thread(target=mqtt_publish, args=(MQTT_TOPIC_CONTROL, "1")).start()

        time.sleep(2)  # Reduce the delay

def on_message(client, userdata, message):
    global servo_active
    try:
        data = json.loads(message.payload)
        Dco2 = data.get("CO2", 0)
        print(f"Received Dco2 value: {Dco2:.0f} ppm")

        # Start or stop the servo motor based on the received CO2 value
        if Dco2 > CO2_THRESHOLD_START and not servo_active:
            print("Dco2 level high! Starting continuous rotation...")
            start_continuous_rotation()
            servo_active = True

        elif Dco2 < CO2_THRESHOLD_STOP and servo_active:
            print("Dco2 level back to normal. Stopping rotation...")
            stop_rotation()
            servo_active = False

    except json.JSONDecodeError:
        print("Failed to decode JSON message")

client.on_message = on_message
client.subscribe(MQTT_SUBSCRIBE_TOPIC)
client.loop_start()

try:
    sensor_thread = threading.Thread(target=read_sensor_data)
    sensor_thread.start()
    sensor_thread.join()

except KeyboardInterrupt:
    print("Program stopped")

finally:
    pwm.stop()
    GPIO.cleanup()
    client.disconnect()
    client.loop_stop()
