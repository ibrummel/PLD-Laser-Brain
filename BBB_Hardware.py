# Imports
import Adafruit_BBIO.GPIO as GPIO
from PyQt5.QtCore import QObject, QTimer
from time import sleep


class BeagleBoneHardware(QObject):

    def __init__(self):
        super().__init__()

        self.allow_trigger = True  # Set this to false to stop triggering the laser
        self.triggers_sent = 0  # Will record the number of trigger pulses sent before pulsing was discontinued
        self.pulse_count_target = None
        self.trigger_timer = QTimer()
        self.trigger_timer.timeout.connect(self.trigger_pulse)

        # Define class variables for pins
        self.trigger_pin = "P8_17"

    def setup_pins(self):
        # Set up pins
        GPIO.setup(trigger_pin, GPIO.OUT)

        # Write all set up pins to LOW
        GPIO.output(trigger_pin, GPIO.LOW)

    def start_pulsing(self, reprate, pulse_count=None):
        # Reset allow_trigger so that we don't end up breaking things/needing to restart the GUI on deposition cancel.
        self.allow_trigger = True
        self.triggers_sent = 0
        rep_time = float(1000 / reprate)
        self.trigger_timer.start(rep_time)
        self.pulse_count_target = pulse_count

    def trigger_pulse(self):
        if self.allow_trigger:
            GPIO.output(self.trigger_pin, GPIO.HIGH)
            sleep(0.000015)
            GPIO.output(self.trigger_pin, GPIO.LOW)
            self.triggers_sent += 1

        if self.pulse_count_target is not None:
            if self.triggers_sent <= self.pulse_count_target:
                self.allow_trigger = False
                self.trigger_timer.stop()

    def reset_trigger(self):
        self.allow_trigger = True
        self.triggers_sent = 0

    def __del__(self):
        GPIO.cleanup()
