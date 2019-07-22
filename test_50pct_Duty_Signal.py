import Adafruit_BBIO.GPIO as GPIO
from time import sleep

cancel = 'P9_15'
sub_dir = "P9_19"
sub_step = "P9_17"

GPIO.setup(cancel, GPIO.IN)
GPIO.setup(sub_dir, GPIO.OUT)
GPIO.setup(sub_step, GPIO.OUT)

GPIO.output(sub_dir, GPIO.HIGH)
sdir = 1

while 1:
    GPIO.output(sub_step, GPIO.HIGH)
    sleep(0.01)
    GPIO.output(sub_step, GPIO.LOW)
    sleep(0.01)
    if not GPIO.input(cancel):
        sleep(2)
        if not GPIO.input(cancel):
            break
        elif sdir == 1:
            GPIO.output(sub_dir, GPIO.LOW)
            sdir = 0
        elif sdir == 0:
            GPIO.output(sub_dir, GPIO.HIGH)
            sdir = 1
