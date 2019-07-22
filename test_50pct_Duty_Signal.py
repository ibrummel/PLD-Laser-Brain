import Adafruit_BBIO.GPIO as GPIO
from time import sleep

cancel = 'P9_15'
sub_dir = "P9_19"
sub_step = "P9_17"

GPIO.setup(cancel, GPIO.IN)
GPIO.setup(sub_dir, GPIO.OUT)
GPIO.setup(sub_step, GPIO.OUT)

GPIO.output(sub_dir, GPIO.HIGH)

while not GPIO.input(cancel):
    GPIO.output(sub_step, GPIO.HIGH)
    sleep(0.003)
    GPIO.output(sub_step, GPIO.LOW)
    sleep(0.003)
