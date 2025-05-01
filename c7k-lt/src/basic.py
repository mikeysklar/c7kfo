import time
import board
import busio
import digitalio
from adafruit_mcp230xx.mcp23008 import MCP23008

# Create the I2C bus at 400 kHz
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)

# Initialize MCP23008
mcp = MCP23008(i2c)

# Use all 8 pins (0–7)
button_pins = list(range(8))

# Set up MCP23008 pins as inputs with pull-up resistors
buttons = []
for pin_number in button_pins:
    button = mcp.get_pin(pin_number)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    buttons.append(button)

print("Monitoring buttons on MCP23008 pins 0–7...")

# Main loop
while True:
    for idx, button in enumerate(buttons):
        try:
            if not button.value:  # Button is pressed (active low)
                pin_label = button_pins[idx]
                print(f"Button on MCP23008 pin {pin_label} pressed.")

                # Debounce: wait until released
                while not button.value:
                    time.sleep(0.005)
        except OSError as e:
            if e.errno == 19:
                pass  # Ignore "No such device" errors
            else:
                raise
    time.sleep(0.1)
