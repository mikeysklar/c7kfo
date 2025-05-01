import board
import busio
import digitalio
import time

# --- Turn on external VCC (P0.13 high) ---
vcc_enable = digitalio.DigitalInOut(board.VCC_OFF)
vcc_enable.direction = digitalio.Direction.OUTPUT
vcc_enable.value = True

# Optional: let power stabilize
time.sleep(0.25)

# --- Set up I2C using default SCL/SDA pins ---
i2c = busio.I2C(scl=board.SCL, sda=board.SDA)

# --- Scan for I2C devices ---
while not i2c.try_lock():
    pass

try:
    print("Scanning I2C bus...")
    devices = i2c.scan()
    if devices:
        print("Found I2C device(s):", [hex(addr) for addr in devices])
    else:
        print("No I2C devices found.")
finally:
    i2c.unlock()
