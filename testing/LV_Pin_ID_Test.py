from gpiozero import LED
from time import sleep

lv_pins = [18, 27, 22, 23, 24, 25, 5, 6]
LEDs = {}

for pin in lv_pins:
    LEDs.update({pin: LED(pin)})

try:
    while True:
        for channel, led in LEDs.items():
            led.on()
            print("Pin {} high".format(channel))
            sleep(2)
            led.off()
            print("---------")
except KeyboardInterrupt:
    print("Loop exited by user")
