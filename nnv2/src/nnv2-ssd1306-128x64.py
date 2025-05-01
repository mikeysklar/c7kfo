import board
import busio
import digitalio
import microcontroller
import displayio
from i2cdisplaybus import I2CDisplayBus
import adafruit_displayio_ssd1306
from adafruit_display_text import label
import terminalio
import time

# Enable VCC for Nice Nano v2
vcc_enable = digitalio.DigitalInOut(board.VCC_OFF)
vcc_enable.direction = digitalio.Direction.OUTPUT
vcc_enable.value = True
time.sleep(0.2)

# Reset pins and display
displayio.release_displays()
digitalio.DigitalInOut(microcontroller.pin.P0_20).deinit()
digitalio.DigitalInOut(microcontroller.pin.P0_17).deinit()

# Init I2C
i2c = busio.I2C(board.SCL, board.SDA)

# Init display
display_bus = I2CDisplayBus(i2c, device_address=0x3D)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64)

# Create display group
splash = displayio.Group()
display.root_group = splash

# Create text label
text_area = label.Label(terminalio.FONT, text="Hello Nice Nano!", x=10, y=30)
splash.append(text_area)

# Keep it alive
while True:
    pass
