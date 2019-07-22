import Adafruit_BBIO.GPIO as GPIO
from time import sleep
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

app = QApplication(sys.argv)

on_timer = QTimer()
off_timer = QTimer()
dir_timer = QTimer()
on_timer.setSingleShot(True)
off_timer.setSingleShot(True)

cancel = 'P9_15'
sub_dir = "P9_19"
sub_step = "P9_17"

GPIO.setup(cancel, GPIO.IN)
GPIO.setup(sub_dir, GPIO.OUT)
GPIO.setup(sub_step, GPIO.OUT)

GPIO.output(sub_dir, GPIO.HIGH)
sdir = 1


def start_step():
    GPIO.output(sub_step, GPIO.HIGH)
    off_timer.start(3)


def finish_step():
    GPIO.output(sub_step, GPIO.LOW)
    on_timer.start(3)


def dir_check():
    global sdir
    sleep(1)
    if GPIO.input(cancel):
        exit()
    elif sdir == 1:
        GPIO.output(sub_dir, GPIO.LOW)
        sdir = 0
    elif sdir == 0:
        GPIO.output(sub_dir, GPIO.HIGH)
        sdir = 1


on_timer.timeout.connect(start_step)
off_timer.timeout.connect(finish_step)
dir_timer.timeout.connect(dir_check)

dir_timer.start(2)
on_timer.start(3)
