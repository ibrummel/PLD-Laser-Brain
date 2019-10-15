# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 10:01:53 2019

@author: Ian
"""
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDockWidget, QFileDialog)
import sys
import xml.etree.ElementTree as ET
from VISA_Communications import VisaLaser
from RPi_Hardware import RPiHardware
from Docked_Motor_Control import MotorControlPanel
from Docked_Laser_Status_Control import LaserStatusControl
from Deposition_Control import DepControlBox


class MainWindow(QMainWindow):

    def __init__(self, laser: VisaLaser, brain: RPiHardware):
        super().__init__()
        self.laser = laser
        self.brain = brain

        # Create a docked widget to hold the LSC module
        self.lsc_docked = QDockWidget()
        self.motor_control_docked = QDockWidget()
        self.settings_file_path = 'settings.xml'
        self.settings_dict = self.parse_xml_to_settings_dict(self.settings_file_path)
        self.init_ui()

    def init_ui(self):
        self.setObjectName('Main Window')
        self.setWindowTitle('PLD Laser Control')
        self.setCentralWidget(DepControlBox(self.laser))

        self.lsc_docked.setWidget(LaserStatusControl(self.laser, self.brain))
        self.lsc_docked.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        self.motor_control_docked.setWidget(MotorControlPanel(self.brain))
        self.motor_control_docked.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        self.setCorner(Qt.TopLeftCorner | Qt.TopRightCorner, Qt.TopDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner | Qt.BottomRightCorner, Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.TopDockWidgetArea, self.lsc_docked)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.motor_control_docked)

    def parse_xml_to_settings_dict(self, file: str):
        try:
            parsed = ET.parse(file)
        except FileNotFoundError:
            file_name = QFileDialog.getOpenFileName(self,
                                                    'Select valid settings file...',
                                                    os.getcwd(),
                                                    "xml Files (*.xml)")
            self.settings_file_path = file_name[0]
            self.parse_xml_to_settings_dict(self.settings_file_path)

        pld = parsed.getroot()
        settings = {'carousel': {}, 'target': {}, 'substrate': {}, 'laser': {}}

        for item in pld.findall('./target_carousel/target'):
            item_id = item.get('ID')
            settings['carousel'][item_id] = {}
            settings['carousel'][item_id]['size'] = item.find('Size').text
            settings['carousel'][item_id]['composition'] = item.find('Composition').text

        for item in pld.findall('./target/'):
            settings['target'][item.tag] = item.text

        for item in pld.findall('./substrate/'):
            settings['substrate'][item.tag] = item.text

        for item in pld.findall('./laser/'):
            settings['laser'][item.tag] = item.text

        return settings


def main():
    app = QApplication(sys.argv)
    # Start LaserComm and connect to laser
    # Use the following call for remote testing (without access to the laser), note that the laser.yaml file must be in
    # the working directory
    # laser = VisaLaser('ASRL3::INSTR', 'laser.yaml@sim')
    laser = VisaLaser('ASRL/dev/ttyS1::INSTR', '@py')
    brain = RPiHardware()

    ex = MainWindow(laser, brain)
    ex.show()

    sys.exit(app.exec_())


# =============================================================================
# Start the GUI (set up for testing for now)
# FIXME: Need to finalize main loop for proper operation
# =============================================================================
if __name__ == '__main__':
    main()
