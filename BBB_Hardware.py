# Imports
import Adafruit_BBIO.GPIO as GPIO
from PyQt5.QtCore import QObject
from time import sleep

# Pin Names
trigger_pin = "P9_12"  # GPIO60

# Set up pins
GPIO.setup(trigger_pin, GPIO.OUT)

# Write all set up pins to LOW
GPIO.output(trigger_pin, GPIO.LOW)


class BeagleBoneHardware(QObject):

    def __int__(self):
        super().__init__()

        self.allow_trigger = True  # Set this to false to stop triggering the laser
        self.triggers_sent = 0  # Will record the number of trigger pulses sent before pulsing was discontinued

    def trigger_pulses(self, reprate, pulse_count):
        # Reset allow_trigger so that we don't end up breaking things/needing to restart the GUI on deposition cancel.
        self.allow_trigger = True
        sleep_time = 1000.0/float(reprate)

        for pulse in range(0, pulse_count):
            if not self.allow_trigger:
                self.triggers_sent = pulse
                break
            GPIO.output(trigger_pin, GPIO.HIGH)
            sleep(0.000015)
            GPIO.output(trigger_pin, GPIO.LOW)
            sleep(sleep_time)

    def __del__(self):
        GPIO.cleanup()
