import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BCM)

pins = [24, 25, 5, 6]

for pin in pins:
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

try:
    while True:
        for pin in pins:
            GPIO.output(pin, GPIO.HIGH)
            print("{} set to high".format(pin))
            sleep(2)
            GPIO.output(pin, GPIO.LOW)
except KeyboardInterrupt:
    print("Exited by user interrupt")

GPIO.cleanup()