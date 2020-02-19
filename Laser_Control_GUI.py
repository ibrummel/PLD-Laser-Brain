# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 10:01:53 2019

@author: Ian
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDockWidget, QAction)
import sys
from Laser_Hardware import CompexLaser
from RPi_Hardware import RPiHardware
from Arduino_Hardware import LaserBrainArduino
from Docked_Motor_Control import MotorControlPanel
from Docked_Laser_Status_Control import LaserStatusControl
from Deposition_Control import DepControlBox
from Instrument_Preferences import InstrumentPreferencesDialog


class PLDMainWindow(QMainWindow):

    def __init__(self, laser: CompexLaser, brain: RPiHardware):
        super().__init__()
        self.menus = {}
        self.menu_actions = {}
        self.laser = laser
        self.brain = brain
        self.settings = InstrumentPreferencesDialog()

        # Create a docked widget to hold the LSC module
        self.lsc_docked = LaserStatusControl(self.laser, self.brain)
        self.motor_control_docked = MotorControlPanel(self.brain)
        self.init_ui()

    def init_ui(self):
        self.setObjectName('Main Window')
        self.setWindowTitle('PLD Laser Control')
        self.setCentralWidget(DepControlBox(self.laser, self.brain, self))

        # self.lsc_docked.setWidget(LaserStatusControl(self.laser, self.brain))
        self.lsc_docked.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        # self.motor_control_docked.setWidget(MotorControlPanel(self.brain))
        self.motor_control_docked.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        self.setCorner(Qt.TopLeftCorner | Qt.TopRightCorner, Qt.TopDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner | Qt.BottomRightCorner, Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.TopDockWidgetArea, self.lsc_docked)
        self.addDockWidget(Qt.TopDockWidgetArea, self.motor_control_docked)

        menubar = self.menuBar()
        self.menu_actions['preferences'] = QAction('Instrument Preferences...', self)
        self.menu_actions['preferences'].setShortcut('Ctrl+Shift+P')
        self.menu_actions['preferences'].triggered.connect(self.open_preferences)
        self.menus['file'] = menubar.addMenu('&File')

    def open_preferences(self):
        self.settings.open()


def main():
    app = QApplication(sys.argv)
    # Start LaserComm and connect to laser
    # Use the following call for remote testing (without access to the laser), note that the laser.yaml file must be in
    # the working directory
    # laser = VisaLaser('ASRL3::INSTR', 'laser.yaml@sim')
    laser = CompexLaser('ASRL/dev/ttyAMA1::INSTR', '@py')
    arduino = LaserBrainArduino('/dev/ttyACM0')
    brain = RPiHardware(laser=laser, arduino=arduino)
    ex = PLDMainWindow(laser, brain)
    ex.show()

    sys.exit(app.exec_())


# =============================================================================
# Start the GUI (set up for testing for now)
# FIXME: Need to finalize main loop for proper operation
# =============================================================================
if __name__ == '__main__':
    main()
