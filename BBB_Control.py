# -*- coding: utf-8 -*-
"""
Created on Thu May 15 20:49:53 2019

@author: Ian
"""

# Imports
import Adafruit_BBIO as gpio
from PyQt5.QtCore import QObject

# Pin Names
trigger_pin = "P9_12"  # GPIO60

# Set up Pins
gpio.setup(trigger_pin, gpio.OUT)

class BBB(QObject):

	def __init__(self):
		super().__init__()

		# Set this to false to stop triggering the laser
		self.allow_trigger = True

	def trigger_pulses(pulse_count, reprate):
		
