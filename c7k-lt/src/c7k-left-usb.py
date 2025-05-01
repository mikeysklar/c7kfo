import board
import busio
import time
import digitalio
import usb_hid
from adafruit_mcp230xx.mcp23008 import MCP23008
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# Setup I2C for MCP23008
i2c = busio.I2C(board.SCL, board.SDA)
mcp = MCP23008(i2c)

# Set up MCP23008 pins as inputs with pull-ups (using pins 0 through 6)
pins = [mcp.get_pin(i) for i in range(7)]
for pin in pins:
    pin.direction = digitalio.Direction.INPUT
    pin.pull = digitalio.Pull.UP

# Initialize USB HID keyboard
keyboard = Keyboard(usb_hid.devices)

# Map MCP23008 physical pins to our key indices (0-6)
pin_to_key_index = {
    0: 0,  # physical pin 0 → key index 0
    1: 1,  # physical pin 1 → key index 1
    2: 2,  # physical pin 2 → key index 2
    3: 3,  # physical pin 3 → key index 3
    6: 4,  # physical pin 4 → key index 4
    5: 5,  # physical pin 5 → key index 5
    4: 6   # physical pin 6 → key index 6
}

# Variables for handling key states and chords
pressed_keys = [False] * 7  # 7 keys (indexed 0-6)
pending_combo = None
last_combo_time = 0
last_hold_time = 0
last_release_time = 0

# Timing parameters
minimum_hold_time = 0.01      # Seconds keys must be held to register a chord
combo_time_window = 0.01      # Allowed time window for chord detection
cooldown_time = 0.01          # (Unused now; replaced by repeat_delay for hold behavior)
release_time_window = 0.01    # Time window to ensure keys are released before new detection
double_press_window = 0.3     # Seconds allowed between taps for a double press
repeat_delay = 0.2            # Delay between repeats when keys are held

last_backspace_time = 0
last_space_time = 0

# Define chord mappings
chords = {
    (0,): Keycode.E,
    (1,): Keycode.I,
    (2,): Keycode.A,
    (3,): Keycode.S,
    (4,): Keycode.BACKSPACE,  # Normal mapping; now only sent on double-tap
    (0, 1): Keycode.R,
    (0, 2): Keycode.O,
    (0, 3): Keycode.C,
    (1, 2): Keycode.N,
    (1, 3): Keycode.L,
    (2, 3): Keycode.T,
    (0, 5): Keycode.M,
    (1, 5): Keycode.G,
    (2, 5): Keycode.H,
    (3, 5): Keycode.B,
    (0, 4): Keycode.SPACE,      # Normal mapping; now only sent on double-tap
    (0, 1, 5): Keycode.Y,
    (0, 2, 5): Keycode.W,
    (0, 3, 5): Keycode.X,
    (1, 2, 5): Keycode.F,
    (1, 3, 5): Keycode.K,
    (2, 3, 5): Keycode.V,
    (0, 1, 2): Keycode.D,
    (1, 2, 3): Keycode.P,
    (0, 1, 2, 5): Keycode.J,
    (1, 2, 3, 5): Keycode.Z,
    (0, 1, 2, 3): Keycode.U,
    (0, 1, 2, 3, 5): Keycode.Q,
    (0, 6): Keycode.ONE,
    (1, 6): Keycode.TWO,
    (2, 6): Keycode.THREE,
    (3, 6): Keycode.FOUR,
    (0, 1, 6): Keycode.FIVE,
    (1, 2, 6): Keycode.SIX,
    (2, 3, 6): Keycode.SEVEN,
    (0, 2, 6): Keycode.EIGHT,
    (1, 3, 6): Keycode.NINE,
    (0, 3, 6): Keycode.UP_ARROW,
    (0, 1, 2, 6): Keycode.ZERO,
    (0, 1, 3, 6): Keycode.RIGHT_ARROW,
    (0, 2, 3, 6): Keycode.LEFT_ARROW,
    (1, 2, 3, 6): Keycode.ESCAPE,
    (0, 1, 2, 3, 6): Keycode.DOWN_ARROW,
    (6,): Keycode.SPACE,  # Also mapped here; double-tap takes precedence.
    (1, 4): Keycode.TAB,
    (2, 4): Keycode.PERIOD,
    (3, 4): Keycode.MINUS,
    (0, 2, 3): Keycode.SPACE,
    (0, 1, 3): Keycode.BACKSPACE,
    (2, 3, 4): Keycode.FORWARD_SLASH,
    (0, 1, 4): Keycode.ENTER,
    (0, 2, 4): Keycode.COMMA,  # Note: In the original, this chord was also set to EQUALS.
    (1, 3, 4): Keycode.LEFT_BRACKET,
    (0, 3, 4): Keycode.RIGHT_BRACKET,
    (2, 3, 4): Keycode.BACKSLASH,
    (1, 2, 4): Keycode.BACKSPACE,
    (0, 1, 3, 4): Keycode.QUOTE,
    (0, 2, 3, 4): Keycode.SEMICOLON,
    (0, 1, 2, 3, 4): Keycode.GRAVE_ACCENT
}

def check_chords():
    global pending_combo, last_combo_time, last_hold_time, last_release_time
    global last_backspace_time, last_space_time
    current_combo = tuple(i for i, pressed in enumerate(pressed_keys) if pressed)
    current_time = time.monotonic()

    if current_combo:
        # Set initial hold time if not already set.
        if last_hold_time == 0:
            last_hold_time = current_time

        if (current_time - last_hold_time) >= minimum_hold_time:
            # Special handling for the (4,) chord (BACKSPACE)
            if current_combo == (4,):
                if last_backspace_time != 0 and (current_time - last_backspace_time) <= double_press_window:
                    # Only repeat if this is a new detection or enough time has passed.
                    if pending_combo != current_combo or (current_time - last_combo_time) >= repeat_delay:
                        keyboard.press(Keycode.BACKSPACE)
                        keyboard.release_all()
                        last_backspace_time = 0  # Reset after double-tap
                        pending_combo = current_combo
                        last_combo_time = current_time
                else:
                    last_backspace_time = current_time

            # Special handling for the (6,) chord (SPACE)
            elif current_combo == (6,):
                if last_space_time != 0 and (current_time - last_space_time) <= double_press_window:
                    if pending_combo != current_combo or (current_time - last_combo_time) >= repeat_delay:
                        keyboard.press(Keycode.SPACE)
                        keyboard.release_all()
                        last_space_time = 0  # Reset after double-tap
                        pending_combo = current_combo
                        last_combo_time = current_time
                else:
                    last_space_time = current_time

            # Normal chord handling for all other chords.
            elif current_combo in chords:
                if pending_combo == current_combo:
                    if (current_time - last_combo_time) >= repeat_delay:
                        keyboard.press(chords[current_combo])
                        keyboard.release_all()
                        last_combo_time = current_time
                else:
                    keyboard.press(chords[current_combo])
                    keyboard.release_all()
                    pending_combo = current_combo
                    last_combo_time = current_time
    else:
        # Reset states when no keys are pressed.
        if last_backspace_time != 0 and (current_time - last_backspace_time > double_press_window):
            last_backspace_time = 0
        if last_space_time != 0 and (current_time - last_space_time > double_press_window):
            last_space_time = 0
        pending_combo = None
        last_hold_time = 0
        last_release_time = current_time

while True:
    # Update pressed_keys from MCP23008.
    for pin, index in pin_to_key_index.items():
        if not mcp.get_pin(pin).value:  # Active low: pressed
            if not pressed_keys[index]:
                pressed_keys[index] = True
        else:
            if pressed_keys[index]:
                pressed_keys[index] = False

    check_chords()
    time.sleep(0.05)
