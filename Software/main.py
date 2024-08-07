import pygame
import threading
import time
import nfc
import sys
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import skywriter
import math
import random
from queue import Queue

# Function to initialize NFC reader
def initialize_nfc_reader():
    try:
        clf = nfc.ContactlessFrontend('usb')
        return clf
    except Exception as e:
        print(f"Error initializing NFC reader: {e}")
        return None

# Initialize Pygame and set fullscreen mode
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
screen_width, screen_height = screen.get_size()
pygame.display.set_caption('Bridge Space Dashboard')
clock = pygame.time.Clock()

# Load and scale background image
background_image = pygame.image.load('./dashbg1_c.png')
bg_width, bg_height = background_image.get_size()
info_image = pygame.image.load('./infodark.png')
info_image = pygame.transform.scale(info_image, (screen_width, screen_height))

# Load game images
game_bg_image = pygame.image.load("gamebg.png")
game_bg_image = pygame.transform.scale(game_bg_image, (screen_width, screen_height))
overlay_image = pygame.image.load("overlay.png")
overlay_image = pygame.transform.scale(overlay_image, (screen_width, screen_height))
PRC = pygame.image.load("player-C.png")
PRC = pygame.transform.scale(PRC, (PRC.get_width() // 2, PRC.get_height() // 2))
PRE = pygame.image.load("player-E.png")
PRE = pygame.transform.scale(PRE, (PRE.get_width() // 2, PRE.get_height() // 2))
PRU = pygame.image.load("player-U.png")
PRU = pygame.transform.scale(PRU, (PRU.get_width() // 2, PRU.get_height() // 2))

# Load food wheel images
fd_bg_image = pygame.image.load("spinbg.png")
fd_bg_image = pygame.transform.scale(fd_bg_image, (screen_width, screen_height))
food_overlay_image = pygame.image.load("food.png")
food_overlay_image = pygame.transform.scale(food_overlay_image, (screen_width, screen_height))

# Load drink wheel images
drink_overlay_image = pygame.image.load("drink.png")
drink_overlay_image = pygame.transform.scale(drink_overlay_image, (screen_width, screen_height))

# Load room background image
room_bg_image = pygame.image.load("roombg.png")
room_bg_image = pygame.transform.scale(room_bg_image, (screen_width, screen_height))

# Calculate the scaling factor to maintain aspect ratio
scale_factor = min(screen_width / bg_width, screen_height / bg_height)
new_width = int(bg_width * scale_factor)
new_height = int(bg_height * scale_factor)

# Scale and position the background image
background_image = pygame.transform.scale(background_image, (new_width, new_height))
bg_x = (screen_width - new_width) // 2
bg_y = (screen_height - new_height) // 2

# Define colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
TEAL = (0, 128, 128)
YELLOW = (249, 172, 23)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
BROWN = (117, 76, 36)
PURPLE = (127, 71, 219)

# Define font
font_path = "./font/static/RobotoCondensed-Bold.ttf"
font = pygame.font.Font(font_path, 38)
font0 = pygame.font.Font(font_path, 42)
font1 = pygame.font.Font(font_path, 90)
game_font = pygame.font.Font(font_path, 48)
food_font = pygame.font.Font(font_path, 30)
drink_font = pygame.font.Font(font_path, 30)
room_font = pygame.font.Font(font_path, 30)

# InfluxDB settings
bucket = "YOUR_BUCKET"  
org = "YOUR_ORG"
token = "YOUR_TOKEN"
url = "YOUR_URL"
influx_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
query_api = influx_client.query_api()

def load_announcements():
    query = f"""
    from(bucket: "{bucket}")
      |> range(start: -14d)
      |> filter(fn: (r) => r["_measurement"] == "YOUR_MEASUREMENT")
      |> filter(fn: (r) => r["notice-topic"] == "YOUR_TOPIC")
      |> filter(fn: (r) => r["_field"] == "message")
      |> filter(fn: (r) => r["date"] >= "2024-07-01")
      |> filter(fn: (r) => r["type"] == "announcement" or r["type"] == "event")
      |> aggregateWindow(every: 1d, fn: last, createEmpty: false)
      |> yield(name: "last")
    """
    result = query_api.query(org=org, query=query)
    announcements = [
        {
            "type": record["type"],
            "date": record["date"],
            "location": record["location"],
            "value": record["_value"]
        }
        for table in result for record in table.records
    ]
    return announcements

TOPIC1_pos = None
TOPIC2_pos = None
dco2 = None
dtem = None
dhum = None

def load_positions_from_influxdb():
    global TOPIC1_pos, TOPIC2_pos, team1_pos, team2_pos
    query = f'''
    from(bucket: "{bucket}")
        |> range(start: -14d)
        |> filter(fn: (r) => r["_measurement"] == "YOUR_MEASUREMENT")
        |> filter(fn: (r) => r["BridgeS"] == "YOUR_TOPIC1" or r["BridgeS"] == "YOUR_TOPIC2" or r["blow-topics"] == "YOUR_TOPIC3")
        |> filter(fn: (r) => r["_field"] == "value")
        |> last()
    '''
    result = query_api.query(org=org, query=query)
    for table in result:
        for record in table.records:
            if record.values.get("BridgeS") == "YOUR_TOPIC1":
                TOPIC1_pos = int(record.get_value())
                team1_pos = TOPIC1_pos  # Set team1_pos
            elif record.values.get("BridgeS") == "YOUR_TOPIC2":
                TOPIC2_pos = int(record.get_value())
                team2_pos = TOPIC2_pos  # Set team2_pos

# Load data
announcements = load_announcements()
load_positions_from_influxdb()

# Define page content
def draw_home_page():
    screen.fill(BLACK)  # Clear screen
    screen.blit(background_image, (bg_x, bg_y))
    large_rect = pygame.Rect(65, 115, 570, 350)
    small_rect1 = pygame.Rect(660, 115, 300, 180)
    small_rect2 = pygame.Rect(660, 325, 300, 140)

    # Adjust rectangles to fit screen
    large_rect_scaled = pygame.Rect(
        large_rect.x * screen_width / 1024,
        large_rect.y * screen_height / 600,
        large_rect.width * screen_width / 1024,
        large_rect.height * screen_height / 600,
    )
    small_rect1_scaled = pygame.Rect(
        small_rect1.x * screen_width / 1024,
        small_rect1.y * screen_height / 600,
        small_rect1.width * screen_width / 1024,
        small_rect1.height * screen_height / 600,
    )
    small_rect2_scaled = pygame.Rect(
        small_rect2.x * screen_width / 1024,
        small_rect2.y * screen_height / 600,
        small_rect2.width * screen_width / 1024,
        small_rect2.height * screen_height / 600,
    )

    # Content in large_rect
    y_offset = large_rect_scaled.y + 60
    for announcement in announcements:
        type_text = font.render(f'[{announcement["type"]}]', True, GRAY)
        date_text = font0.render(f'{announcement["date"]}', True, TEAL)
        location_text = font0.render(f'{announcement["location"]}', True, GRAY)
        value_text = font0.render(f'{announcement["value"]}', True, TEAL)

        x_offset = large_rect_scaled.x + 10
        screen.blit(type_text, (x_offset, y_offset))
        x_offset += type_text.get_width() + 10  
        screen.blit(date_text, (x_offset, y_offset))
        x_offset += date_text.get_width() + 20
        screen.blit(location_text, (x_offset, y_offset))
        x_offset += location_text.get_width() + 20
        screen.blit(value_text, (x_offset, y_offset))

        y_offset += 60

    # Data from InfluxDB in small_rect1
    score1_text = font1.render(f'{TOPIC1_pos}', True, TEAL)
    score2_text = font1.render(f'{TOPIC2_pos}', True, TEAL)
    screen.blit(score1_text, (small_rect1_scaled.x + 102, small_rect1_scaled.y + 195))
    screen.blit(score2_text, (small_rect1_scaled.x + 418, small_rect1_scaled.y + 195))

    # Data from sensor in small_rect2
    co2_text = font.render(f'{dco2}', True, YELLOW)
    temp_text = font.render(f'{dtem}', True, YELLOW)
    hum_text = font.render(f'{dhum}', True, YELLOW)
    screen.blit(co2_text, (small_rect2_scaled.x + 110, small_rect2_scaled.y + 144))
    screen.blit(temp_text, (small_rect2_scaled.x + 295, small_rect2_scaled.y + 144))
    screen.blit(hum_text, (small_rect2_scaled.x + 428, small_rect2_scaled.y + 144))

def draw_info_page():
    screen.fill(BLACK)
    screen.blit(info_image, (0, 0))

def draw_game_page():
    screen.blit(game_bg_image, (0, 0))
    draw_roulette()
    draw_tracks()
    screen.blit(overlay_image, (0, 0))

def draw_food_page():
    screen.blit(fd_bg_image, (0, 0))
    draw_food_roulette()
    screen.blit(food_overlay_image, (0, 0))

def draw_drink_page():
    screen.blit(fd_bg_image, (0, 0))
    draw_drink_roulette()
    screen.blit(drink_overlay_image, (0, 0))

def draw_room_page():
    screen.blit(room_bg_image, (0, 0))

    # Render and display the status for each room at specific positions
    for room, (status, color) in room_statuses.items():
        position = room_positions.get(room, (50, 50))  # Default position if not found
        status_text = room_font.render(f"{status}", True, color)
        screen.blit(status_text, position)

# MQTT settings
mqtt_broker = "YOUR_BROKER"
mqtt_port = 1884
mqtt_info = "/Dashboard/info"
mqtt_food = "/Dashboard/food"
mqtt_drink = "/Dashboard/drink"
mqtt_room = "/Dashboard/room"
mqtt_home = "/Dashboard/announcement"
mqtt_username = "YOUR_USERNAME"
mqtt_password = "YOUR_PASSWORD"
mqtt_co2 = "/Team_2/blow/value"
mqtt_topic_game = "/Team_2/game"
mqtt_topic_demo = "/Team_1/game"
mqtt_topic_dashboard = "/Dashboard/game/"
mqtt_topic_wins = "/Dashboard/game/wins/"
mqtt_topic_base_team2 = "/Team_2/room/"
mqtt_topic_base_team1 = "/Team_1/room/"

client = mqtt.Client()

# Room statuses and positions
room_statuses = {
    "R201a": ("unknown", (255, 255, 255)),
    "R201b": ("unknown", (255, 255, 255)),
    "R206a": ("unknown", (255, 255, 255)),
    "R206b": ("unknown", (255, 255, 255)),
    "R219b": ("unknown", (255, 255, 255)),
    "R105": ("unknown", (255, 255, 255)),
    "R110": ("unknown", (255, 255, 255)),
    "R111": ("unknown", (255, 255, 255))
}

room_positions = {
    "R201a": (250, 320),
    "R201b": (520, 320),
    "R206a": (250, 380),
    "R206b": (520, 380),
    "R219b": (250, 436),
    "R105": (1215, 524),
    "R110": (1215, 580),
    "R111": (1215, 638)
}

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe([(mqtt_topic_base_team2 + room, 0) for room in room_statuses.keys() if "Team_2" in mqtt_topic_base_team2 + room])
    client.subscribe([(mqtt_topic_base_team1 + room, 0) for room in room_statuses.keys() if "Team_1" in mqtt_topic_base_team1 + room])
    client.subscribe(mqtt_co2)

def on_message(client, userdata, message):
    global room_statuses, dco2, dtem, dhum
    topic = message.topic
    payload = message.payload.decode()

    if topic.startswith(mqtt_topic_base_team1) or topic.startswith(mqtt_topic_base_team2):
        topic = topic.split('/')[-1]
        
        # Set color based on the status
        if payload == "available":
            color = YELLOW  # yellow
        elif payload == "occupied":
            color = PURPLE  # Purple
        else:
            color = WHITE  # White for unknown or other statuses

        room_statuses[topic] = (payload, color)
    
    elif topic == mqtt_co2:
            data = json.loads(payload)
            dco2 = data.get("CO2", dco2)
            dtem = data.get("Temperature", dtem)
            dhum = data.get("Humidity", dhum)
            print(f"Received data: CO2={dco2}, Temperature={dtem}, Humidity={dhum}")
        


client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(mqtt_username, mqtt_password)
client.connect(mqtt_broker, mqtt_port, 60)
client.loop_start()

# Define NFC read function
def read_nfc(clf):
    try:
        tag = clf.connect(rdwr={'on-connect': lambda tag: False})
        if hasattr(tag, 'ndef'):
            for record in tag.ndef.records:
                return record.text
        return ""
    except Exception as e:
        print(f"Error during NFC read: {e}")
        return None

# NFC reading thread
clf = initialize_nfc_reader()
if clf is None:
    print("NFC reader not connected. Exiting program.")
    sys.exit(1)
    
def nfc_reader_thread(nfc_queue):
    previous_tag_text = ""
    retry_count = 0
    while running:
        try:
            new_tag_text = read_nfc(clf)
            if new_tag_text is not None and new_tag_text != previous_tag_text:
                previous_tag_text = new_tag_text
                nfc_queue.put(new_tag_text)
            time.sleep(1)  # Control read frequency
        except Exception as e:
            print(f"Error reading NFC: {e}")
            retry_count += 1
            if retry_count >= 5:
                retry_count = 0
                time.sleep(10)  # Wait longer before retrying
            else:
                time.sleep(2)  # Wait a while before retrying

def draw_current_time():
    current_time = datetime.now().strftime('%H:%M:%S')
    time_text = font.render(current_time, True, TEAL)
    screen.blit(time_text, (screen_width - time_text.get_width() - 110, 80))

def publish_result(result):
    global team2_pos, team1_pos
    team2_pos += result
    team2_pos = max(0, team2_pos)
    print(f"New position for Team2: {team2_pos}")
    client.publish(mqtt_topic_game, team2_pos)
    check_winner_and_publish_status()

def publish_status():
    if team1_pos > team2_pos:
        status = "Team1 is faster"
    elif team2_pos > team1_pos:
        status = "Team2 is faster"
    else:
        status = "Both teams are tied"
    client.publish(mqtt_topic_dashboard, status)

def check_winner_and_publish_status():
    global team1_wins, team2_wins, team1_pos, team2_pos
    if team1_pos >= 20.0:
        team1_wins += 1
        client.publish(mqtt_topic_dashboard, "Team1 won!")
        client.publish(mqtt_topic_wins, f"Team1 wins: {team1_wins}, Team2 wins: {team2_wins}")
        team1_pos = 0
        team2_pos = 0
        client.publish(mqtt_topic_demo, 0)
        client.publish(mqtt_topic_game, 0)
    elif team2_pos >= 20.0:
        team2_wins += 1
        client.publish(mqtt_topic_dashboard, "Team2 won!")
        client.publish(mqtt_topic_wins, f"Team1 wins: {team1_wins}, Team2 wins: {team2_wins}")
        team1_pos = 0
        team2_pos = 0
        client.publish(mqtt_topic_demo, 0)
        client.publish(mqtt_topic_game, 0)
    else:
        publish_status()

def draw_roulette():
    screen.blit(game_bg_image, (0, 0))
    pygame.draw.circle(screen, BROWN, center, radius + 10)
    pygame.draw.circle(screen, WHITE, center, radius)

    for i in range(num_slots):
        slot_angle = angle_step * i + angle
        next_slot_angle = angle_step * (i + 1) + angle
        mid_angle = (slot_angle + next_slot_angle) / 2

        x = center[0] + radius * math.cos(math.radians(slot_angle))
        y = center[1] + radius * math.sin(math.radians(slot_angle))
        pygame.draw.line(screen, YELLOW, center, (x, y), 3)

        text_x = center[0] + (radius - 40) * math.cos(math.radians(mid_angle))
        text_y = center[1] + (radius - 40) * math.sin(math.radians(mid_angle))

        text = game_font.render(str(numbers[i]), True, BROWN)
        text_rect = text.get_rect(center=(text_x, text_y))
        screen.blit(text, text_rect)

def draw_tracks():
    track_height = 100
    track_width = screen_width - 855
    track_y_start = center[1] - track_y_offset // 2 - track_height

    for i in range(2):
        track_y = track_y_start + i * (track_height + track_y_offset)
        if i == 0:
            team_x = 100 + track_width / track_length * team1_pos
            PRE_rect = PRE.get_rect(center=(team_x, track_y + track_height // 2))
            screen.blit(PRE, PRE_rect)
        else:
            team_x = 100 + track_width / track_length * team2_pos
            PRE_rect = PRU.get_rect(center=(team_x, track_y + track_height // 2))
            screen.blit(PRU, PRE_rect)

def draw_food_roulette():
    center_food = (screen_width // 2, screen_height // 2)
    radius_food = 300
    screen.blit(fd_bg_image, (0, 0))
    pygame.draw.circle(screen, BROWN, center_food, radius_food + 10)
    pygame.draw.circle(screen, WHITE, center_food, radius_food)

    for i in range(num_slots):
        slot_angle = angle_step * i + angle
        next_slot_angle = angle_step * (i + 1) + angle
        mid_angle = (slot_angle + next_slot_angle) / 2

        x = center_food[0] + radius_food * math.cos(math.radians(slot_angle))
        y = center_food[1] + radius_food * math.sin(math.radians(slot_angle))
        pygame.draw.line(screen, BROWN, center_food, (x, y), 3)

        text_x = center_food[0] + (radius_food - 90) * math.cos(math.radians(mid_angle))
        text_y = center_food[1] + (radius_food - 90) * math.sin(math.radians(mid_angle))

        text = food_font.render(labels_food[i], True, BROWN)
        text = pygame.transform.rotate(text, -mid_angle)
        text_rect = text.get_rect(center=(text_x, text_y))
        screen.blit(text, text_rect)

def draw_drink_roulette():
    center_drink = (screen_width // 2, screen_height // 2)
    radius_drink = 300
    screen.blit(fd_bg_image, (0, 0))
    pygame.draw.circle(screen, BROWN, center_drink, radius_drink + 10)
    pygame.draw.circle(screen, WHITE, center_drink, radius_drink)

    for i in range(num_slots):
        slot_angle = angle_step * i + angle
        next_slot_angle = angle_step * (i + 1) + angle
        mid_angle = (slot_angle + next_slot_angle) / 2

        x = center_drink[0] + radius_drink * math.cos(math.radians(slot_angle))
        y = center_drink[1] + radius_drink * math.sin(math.radians(slot_angle))
        pygame.draw.line(screen, BROWN, center_drink, (x, y), 3)

        text_x = center_drink[0] + (radius_drink - 90) * math.cos(math.radians(mid_angle))
        text_y = center_drink[1] + (radius_drink - 90) * math.sin(math.radians(mid_angle))

        text = drink_font.render(labels_drink[i], True, BROWN)
        text = pygame.transform.rotate(text, -mid_angle)
        text_rect = text.get_rect(center=(text_x, text_y))
        screen.blit(text, text_rect)

def spin_roulette():
    global angle, spin_speed, spinning, result_number
    angle += spin_speed
    angle %= 360
    if spinning:
        if spin_speed < 22.3:
            spin_speed -= 1
        else:
            spin_speed -= 0.2
        if spin_speed <= 0:
            spin_speed = 0
            spinning = False
            result_angle = (360 - angle) % 360
            result_number = int((result_angle) / angle_step) % num_slots
            result_message = numbers[result_number]
            print(result_message)
            publish_result(result_message)

def spin_fd_roulette():
    global angle, spin_speed, spinning
    angle += spin_speed
    angle %= 360
    if spinning:
        if spin_speed < 22.3:
            spin_speed -= 1
        else:
            spin_speed -= 0.2
        if spin_speed <= 0:
            spin_speed = 0
            spinning = False

@skywriter.airwheel()
def airwheel(delta):
    global spinning, spin_speed, airwheel_values
    if current_page not in ["game", "food", "drink"]:
        return  # Avoid changing page when using skywriter
    print(f"Airwheel detected, delta: {delta}")

    airwheel_values.append(abs(delta))
    if len(airwheel_values) > 10:
        airwheel_values.pop(0)

    avg_delta = sum(airwheel_values) / len(airwheel_values)
    spin_speed = 20 + (avg_delta / 100.0) * 10

    print(f"Average delta: {avg_delta}, spin speed: {spin_speed}")

    if not spinning:
        spinning = True

# Initialize game variables
radius = 230
center = (screen_width - radius - 100, screen_height // 2)
num_slots = 8
angle_step = 360 / num_slots
fixed_numbers = [0, -1, 1, 2, 5, -2]
unique_random_numbers = set()

while len(unique_random_numbers) < num_slots - len(fixed_numbers):
    unique_random_numbers.add(random.randint(1, 10))

numbers = fixed_numbers + list(unique_random_numbers)

track_length = 20
team1_pos = 0
team2_pos = 0
track_y_offset = 45

team1_wins = 0
team2_wins = 0
airwheel_values = []

# Food and drink labels
labels_food = ["Sandwiches", "Sushi", "Fish & Chips", "Curry", "Pasta", "Noodles", "Kebab", "Pizza"]
labels_drink = ["Espresso", "Americano", "Tea", "Beer", "Latte", "Flat White", "Cappuccino", "Filter"]

# Initialize current page and timer
running = True
spinning = False
angle = 0
spin_speed = 0
result_number = None
page_timer_start = time.time()
current_page = "home"
last_tag_text = ""
# Queue for NFC events
nfc_queue = Queue()

# Start NFC reading thread
thread = threading.Thread(target=nfc_reader_thread, args=(nfc_queue,), daemon=True)
thread.start()

# Main loop
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # Handle NFC events
    while not nfc_queue.empty():
        new_tag_text = nfc_queue.get()
        if new_tag_text != last_tag_text:
            last_tag_text = new_tag_text
            page_timer_start = time.time()  # Reset the timer
            if new_tag_text == "game":
                current_page = "game"
                load_positions_from_influxdb()  # Load positions when switching to game page
            elif new_tag_text == "info":
                current_page = "info"
                client.publish(mqtt_info, "1")
            elif new_tag_text == "food":
                current_page = "food"
                client.publish(mqtt_food, "1")
            elif new_tag_text == "drink":
                current_page = "drink"
                client.publish(mqtt_drink, "1")
            elif new_tag_text == "room":
                current_page = "room"
                client.publish(mqtt_room, "1")
            elif new_tag_text == "home":
                current_page = "home"
                client.publish(mqtt_home, "1")
                load_positions_from_influxdb()  # Load positions when switching to home page

    # Check if timer exceeds 15 minutes
    if time.time() - page_timer_start > 15 * 60:
        current_page = "home"  # Switch back to home page
        page_timer_start = time.time()  # Reset timer

    if current_page == "home":
        draw_home_page()
    elif current_page == "info":
        draw_info_page()
    elif current_page == "game":
        spin_roulette()
        draw_game_page()
    elif current_page == "food":
        spin_fd_roulette()
        draw_food_page()
    elif current_page == "drink":
        spin_fd_roulette()
        draw_drink_page()
    elif current_page == "room":
        draw_room_page()

    draw_current_time()

    pygame.display.flip()
    clock.tick(30)

client.loop_stop()
client.disconnect()
pygame.quit()
sys.exit()
