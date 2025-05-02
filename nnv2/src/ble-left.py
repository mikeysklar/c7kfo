import board
import busio
import time
import digitalio
from adafruit_mcp230xx.mcp23008 import MCP23008
import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# --- Turn on external VCC (P0.13 high) ---
vcc_enable = digitalio.DigitalInOut(board.VCC_OFF)
vcc_enable.direction = digitalio.Direction.OUTPUT
vcc_enable.value = True

# Optional: let power stabilize
time.sleep(0.5)

# Setup I2C for MCP23008
i2c = busio.I2C(scl=board.SCL, sda=board.SDA, frequency=400000)
mcp = MCP23008(i2c)

# Set up MCP23017 pins as inputs with pull-ups
pins = [mcp.get_pin(i) for i in range(7)]
for pin in pins:
    pin.direction = digitalio.Direction.INPUT
    pin.pull = digitalio.Pull.UP

# Initialize BLE and HID services
ble = adafruit_ble.BLERadio()
hid = HIDService()
advertisement = ProvideServicesAdvertisement(hid)
keyboard = Keyboard(hid.devices)

# Dictionary to map pins to specific key indices
pin_to_key_index = {
    0: 0,  # physical pin 0 → key index 0
    1: 1,  # physical pin 1 → key index 1
    2: 2,  # physical pin 2 → key index 2
    3: 3,  # physical pin 3 → key index 3
    4: 4,  # physical pin 4 → key index 4
    5: 5,  # physical pin 5 → key index 5
    6: 6   # physical pin 6 → key index 6
}

# Variables for handling key states and chords
pressed_keys = [False] * 7  # 7 keys mapped from MCP23017 (indexed 0-6)
pending_combo = None
last_combo_time = 0
last_hold_time = 0
last_release_time = 0

# Timing parameters
minimum_hold_time = 0.01  # Minimum time keys must be held to register a chord (in seconds)
combo_time_window = 0.01  # Time window for combo detection (in seconds)
cooldown_time = 0.01      # Cooldown time to prevent accidental repeats (in seconds)
release_time_window = 0.01 # Time window to ensure all keys are released before new detection (in seconds)

# Define chord mappings from the original zibn.py
chords = {
    (0,): Keycode.E, (1,): Keycode.I, (2,): Keycode.A, (3,): Keycode.S, (4,): Keycode.SPACE,
    (0, 1): Keycode.R, (0, 2): Keycode.O, (0, 3): Keycode.C, (1, 2): Keycode.N, 
    (1, 3): Keycode.L, (2, 3): Keycode.T, (0, 5): Keycode.M, (1, 5): Keycode.G, 
    (2, 5): Keycode.H, (3, 5): Keycode.B, (0, 4): Keycode.SPACE,
    (0, 1, 5): Keycode.Y, (0, 2, 5): Keycode.W, (0, 3, 5): Keycode.X,
    (1, 2, 5): Keycode.F, (1, 3, 5): Keycode.K, (2, 3, 5): Keycode.V,
    (0, 1, 2): Keycode.D, (1, 2, 3): Keycode.P, 
    (0, 1, 2, 5): Keycode.J, (1, 2, 3, 5): Keycode.Z,
    (0, 1, 2, 3): Keycode.U, (0, 1, 2, 3, 5): Keycode.Q,
    (0, 6): Keycode.ONE, (1, 6): Keycode.TWO, (2, 6): Keycode.THREE, (3, 6): Keycode.FOUR,
    (0, 1, 6): Keycode.FIVE, (1, 2, 6): Keycode.SIX, (2, 3, 6): Keycode.SEVEN, 
    (0, 2, 6): Keycode.EIGHT, (1, 3, 6): Keycode.NINE, 
    (0, 3, 6): Keycode.UP_ARROW, (0, 1, 2, 6): Keycode.ZERO, 
    (0, 1, 3, 6): Keycode.RIGHT_ARROW, (0, 2, 3, 6): Keycode.LEFT_ARROW, 
    (1, 2, 3, 6): Keycode.ESCAPE, (0, 1, 2, 3, 6): Keycode.DOWN_ARROW,
    (6,): Keycode.BACKSPACE, (1, 4): Keycode.TAB, (2, 4): Keycode.PERIOD, 
    (3, 4): Keycode.MINUS, (0, 2, 3): Keycode.SPACE, (0, 1, 3): Keycode.BACKSPACE, 
    (2, 3, 4): Keycode.FORWARD_SLASH, (0, 1, 4): Keycode.ENTER, 
    (0, 2, 4): Keycode.COMMA, (0, 2, 4): Keycode.EQUALS, 
    (1, 3, 4): Keycode.LEFT_BRACKET, (0, 3, 4): Keycode.RIGHT_BRACKET, 
    (2, 3, 4): Keycode.BACKSLASH, (1, 2, 4): Keycode.BACKSPACE, 
    (0, 1, 3, 4): Keycode.QUOTE, (0, 2, 3, 4): Keycode.SEMICOLON,
    (0, 1, 2, 3, 4): Keycode.GRAVE_ACCENT
}

# Connect BLE HID
ble.start_advertising(advertisement)
while not ble.connected:
    pass
ble.stop_advertising()

# Function to check key combinations
def check_chords():
    global pending_combo, last_combo_time, last_hold_time, last_release_time
    current_combo = tuple(i for i, pressed in enumerate(pressed_keys) if pressed)
    current_time = time.monotonic()

    if current_combo:
        # Check if the keys are held for the minimum required time
        if last_hold_time == 0:
            last_hold_time = current_time

        if (current_time - last_hold_time) >= minimum_hold_time:
            if current_combo in chords:
                # Ensure keys are pressed within a short time window
                if pending_combo is None or (current_time - last_combo_time) <= combo_time_window:
                    if pending_combo != current_combo:  # Only register if it's a new combo
                        keyboard.press(chords[current_combo])
                        keyboard.release_all()
                        pending_combo = current_combo
                        last_combo_time = current_time
                        time.sleep(cooldown_time)  # Cooldown to prevent accidental repeats
    else:
        # Reset pending combo and hold time when all keys are released
        if last_release_time == 0 or (current_time - last_release_time) >= release_time_window:
            pending_combo = None
            last_hold_time = 0
            last_release_time = current_time

# Main loop to monitor MCP23017 pin presses
while ble.connected:
    for pin, index in pin_to_key_index.items():
        if not mcp.get_pin(pin).value:  # Pin is pressed
            if not pressed_keys[index]:
                pressed_keys[index] = True
        else:
            if pressed_keys[index]:
                pressed_keys[index] = False

    # Check for key combinations and chords
    check_chords()
    time.sleep(0.05)

