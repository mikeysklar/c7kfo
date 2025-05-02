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

time.sleep(0.5)  # Optional: allow power to stabilize

# Setup I2C and MCP23008 expanders
i2c = busio.I2C(scl=board.SCL, sda=board.SDA, frequency=400000)
mcp_left = MCP23008(i2c, address=0x20)
mcp_right = MCP23008(i2c, address=0x21)
mcps = [mcp_left, mcp_right]

# Configure all pins on both expanders
for mcp in mcps:
    for i in range(7):
        pin = mcp.get_pin(i)
        pin.direction = digitalio.Direction.INPUT
        pin.pull = digitalio.Pull.UP

# BLE HID setup
ble = adafruit_ble.BLERadio()
hid = HIDService()
advertisement = ProvideServicesAdvertisement(hid)
keyboard = Keyboard(hid.devices)

# Map MCP pin to key index (logical 0–6)
pin_to_key_index = {
    0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6
}

# Key state tracking for 2 hands (7 keys × 2)
pressed_keys = [False] * 14

# State variables
pending_combo = None
last_combo_time = 0
last_hold_time = 0
last_release_time = 0

# Timing parameters
minimum_hold_time = 0.01
combo_time_window = 0.01
cooldown_time = 0.01
release_time_window = 0.01

# Chord dictionary (same for both hands)
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
    (0, 2, 4): Keycode.EQUALS,
    (1, 3, 4): Keycode.LEFT_BRACKET, (0, 3, 4): Keycode.RIGHT_BRACKET,
    (2, 3, 4): Keycode.BACKSLASH, (1, 2, 4): Keycode.BACKSPACE,
    (0, 1, 3, 4): Keycode.QUOTE, (0, 2, 3, 4): Keycode.SEMICOLON,
    (0, 1, 2, 3, 4): Keycode.GRAVE_ACCENT
}

# Start BLE
ble.start_advertising(advertisement)
while not ble.connected:
    pass
ble.stop_advertising()

# Chord checker
def check_chords():
    global pending_combo, last_combo_time, last_hold_time, last_release_time
    current_combo = tuple(i % 7 for i, pressed in enumerate(pressed_keys) if pressed)
    current_time = time.monotonic()

    if current_combo:
        if last_hold_time == 0:
            last_hold_time = current_time

        if (current_time - last_hold_time) >= minimum_hold_time:
            if current_combo in chords:
                if pending_combo is None or (current_time - last_combo_time) <= combo_time_window:
                    if pending_combo != current_combo:
                        keyboard.press(chords[current_combo])
                        keyboard.release_all()
                        pending_combo = current_combo
                        last_combo_time = current_time
                        time.sleep(cooldown_time)
    else:
        if last_release_time == 0 or (current_time - last_release_time) >= release_time_window:
            pending_combo = None
            last_hold_time = 0
            last_release_time = current_time

# Main loop
while ble.connected:
    for hand_index, mcp in enumerate(mcps):
        base_index = hand_index * 7
        for pin, key_index in pin_to_key_index.items():
            # Reverse finger keys 0–3 for right hand
            if hand_index == 1 and key_index in (0, 1, 2, 3):
                key_index = 3 - key_index
            index = base_index + key_index
            pin_val = not mcp.get_pin(pin).value
            pressed_keys[index] = pin_val

    check_chords()
    time.sleep(0.01)
