# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 10:01:53 2019

@author: Ian
"""
from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAction, QFileDialog, QMessageBox, QStatusBar)
import sys
from Laser_Hardware import CompexLaser
from RPi_Hardware import RPiHardware
from Arduino_Hardware import LaserBrainArduino
from Docked_Motor_Control import MotorControlPanel
from Docked_Laser_Status_Control import LaserStatusControl
from Deposition_Control import DepControlBox
from Instrument_Preferences import InstrumentPreferencesDialog
from pathlib import Path
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta


# Adds a settings attribute to the application for use elsewhere.
class PLDControlApp(QApplication):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instrument_settings = InstrumentPreferencesDialog()


class PLDMainWindow(QMainWindow):

    def __init__(self, laser: CompexLaser, brain: RPiHardware):
        super().__init__()
        self.menus = {}
        self.menu_actions = {}
        self.laser = laser
        self.brain = brain
        self.loaded_deposition_path = None
        self.unsaved_changes = False

        # Create a docked widget to hold the LSC module
        self.lsc_docked = LaserStatusControl(self.laser, self.brain)
        self.motor_control_docked = MotorControlPanel(self.brain)
        self.dep_control = DepControlBox(self.laser, self.brain, self)
        self.statusbar = QStatusBar()
        self.timeout_counter = -9999 # Starts with the value of a completed timer.
        self.laser_running_timer = QTimer()

        self.installEventFilter(self)
        self.hotkey_disable = False

        self.init_ui()
        self.init_connections()

    def init_ui(self):
        self.setObjectName('Main Window')
        self.setWindowTitle('PLD Laser Control')
        self.setCentralWidget(self.dep_control)
        self.setStatusBar(self.statusbar)

        # self.lsc_docked.setWidget(LaserStatusControl(self.laser, self.brain))
        self.lsc_docked.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        # self.motor_control_docked.setWidget(MotorControlPanel(self.brain))
        self.motor_control_docked.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        self.setCorner(Qt.TopLeftCorner | Qt.TopRightCorner, Qt.TopDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner | Qt.BottomRightCorner, Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.TopDockWidgetArea, self.lsc_docked)
        self.addDockWidget(Qt.TopDockWidgetArea, self.motor_control_docked)
        self.tabifyDockWidget(self.lsc_docked, self.motor_control_docked)
        self.lsc_docked.raise_()

        self.init_menubar()

    def init_menubar(self):
        # Retrieve the menubar widget
        menubar = self.menuBar()

        # Create the file mennu
        file = menubar.addMenu('&File')
        # Create file actions
        file_load = self.build_menu_action('Load Deposition...', self.load_deposition, 'Ctrl+O')
        file_save = self.build_menu_action('Save Deposition', lambda: self.save_deposition(saveas=False), 'Ctrl+S')
        file_save_as = self.build_menu_action('Save Deposition As...', lambda: self.save_deposition(saveas=False),
                                              'Ctrl+Shift+S')
        file_new = self.build_menu_action('New Deposition', self.new_deposition, 'Ctrl+N')
        file_exit = self.build_menu_action('Exit', sys.exit, 'Ctrl+Q')
        file.addActions([file_new, file_load, file_save, file_save_as, file_exit])

        # Create the edit menu
        edit = menubar.addMenu('&Edit')
        # Create edit actions
        edit_preferences = self.build_menu_action('Preferences...', self.open_preferences, 'Ctrl+Alt+P')
        edit.addAction(edit_preferences)

    def init_connections(self):
        self.dep_control.deposition_changed.connect(self.set_unsaved_changes)

        self.brain.laser_time_to_completion.connect(self.start_statusbar_completion_timer)
        self.laser_running_timer.timeout.connect(self.update_statusbar_completion_timer)
        self.lsc_docked.laser_manual_stop.connect(self.manual_laser_stop_statusbar_update)

    def start_statusbar_completion_timer(self, time: int):
        self.timeout_counter = time
        if self.timeout_counter == -9999:
            self.statusbar.showMessage("Laser running without targeted number of pulses.")
        else:
            self.update_statusbar_completion_timer()
            self.laser_running_timer.start(1000)

    def manual_laser_stop_statusbar_update(self):
        if self.timeout_counter > 0:
            self.laser_running_timer.stop()
            time_left = str(timedelta(seconds=self.timeout_counter))
            self.statusbar.showMessage("Laser stopped manually, estimated time remaining {}.".format(time_left), 5000)
            self.timeout_counter = 0
        elif self.timeout_counter == -9999:
            self.statusbar.showMessage("Laser stopped.", 5000)

    def update_statusbar_completion_timer(self):
        if self.timeout_counter > 0:
            time_left = str(timedelta(seconds=self.timeout_counter))
            self.statusbar.showMessage("Laser running, estimated time remaining {}".format(time_left))
            self.timeout_counter -= 1
        elif self.timeout_counter == 0:
            self.statusbar.showMessage("Pulsing Complete.", 5000)
            self.laser_running_timer.stop()
        else:
            return

    def set_unsaved_changes(self):
        self.unsaved_changes = True

    def build_menu_action(self, actstr, connection, shortcutstr=None):
        action = QAction(actstr, self)
        action.triggered.connect(connection)
        if shortcutstr is not None:
            action.setShortcut(shortcutstr)

        return action

    def open_preferences(self):
        # Opens the app's settings dialog
        QApplication.instance().instrument_settings.open()

    def load_deposition(self):
        self.query_overwrite('Loading')
        # If the user has not loaded a file this session open home
        if self.loaded_deposition_path is None:
            load_file = QFileDialog.getOpenFileName(self, 'Select a deposition file to load...',
                                                    str(Path(os.path.expanduser('~'))),
                                                    'Deposition Files (*.depo);;XML Files (*.xml)')
        # If the user has loaded a file, attempt to open its directory
        else:
            try:
                load_file = QFileDialog.getOpenFileName(self, 'Select a deposition file to load...',
                                                        str(self.loaded_deposition_path),
                                                        'Deposition Files (*.depo);;XML Files (*.xml)')
            # if that doesn't work,
            except TypeError as err:
                print(err)
                self.loaded_deposition_path = None
                self.load_deposition()

        deposition = ET.parse(load_file[0])
        self.dep_control.load_xml_dep(deposition)
        self.loaded_deposition_path = Path(load_file[0])

    def save_deposition(self, saveas=True):
        deposition = self.dep_control.get_dep_xml()

        if not saveas and self.loaded_deposition_path is not None:
            save_file = self.loaded_deposition_path
        elif saveas and self.loaded_deposition_path is not None:
            save_file = QFileDialog.getSaveFileName(self, 'Select a Save Location...', str(self.loaded_deposition_path),
                                                    'Deposition Files (*.depo);;XML Files (*.xml)')
        else:
            save_file = QFileDialog.getSaveFileName(self, 'Select a Save Location...',
                                                    str(Path(os.path.expanduser('~'))),
                                                    'Deposition Files (*.depo);;XML Files (*.xml)')

        deposition_tree = ET.ElementTree(deposition)
        deposition_tree.write(self.return_file_dialogue_path(save_file))
        self.unsaved_changes = False

    def new_deposition(self):
        self.query_overwrite('Starting')

        self.dep_control.clear_deposition()
        self.loaded_deposition_path = None
        self.unsaved_changes = False

    def query_overwrite(self, load_or_new: str):
        if self.unsaved_changes:
            clear_current_dep = QMessageBox.question(self, 'Discard Current Deposition?',
                                                     '{} a new deposition will clear previous work, would you\n'
                                                     ' like to save the current deposition before continuing?'.format(
                                                         load_or_new),
                                                     QMessageBox.Discard | QMessageBox.Save | QMessageBox.Cancel,
                                                     QMessageBox.Save)
            if clear_current_dep == QMessageBox.Save:
                self.save_deposition(saveas=True)

        self.unsaved_changes = False

    def return_file_dialogue_path(self, file_dialogue_return: tuple):
        path_obj = Path(file_dialogue_return[0])
        extension_str = file_dialogue_return[1].split('(')[1].split(')')[0].strip('*')

        if path_obj.suffix == extension_str:
            return str(path_obj)
        else:
            path_obj = path_obj.with_suffix(extension_str)

        return str(path_obj)

    # Build custom behavior for keys that control substrate movement
    def keyReleaseEvent(self, eventQKeyEvent):
        key = eventQKeyEvent.key()
        if not eventQKeyEvent.isAutoRepeat():
            if key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Plus, Qt.Key_Minus]:
                self.motor_control_docked.sub_halt()

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if event.key() in [Qt.Key_Up, Qt.Key_Plus]:
                self.motor_control_docked.sub_up()
            elif event.key() in [Qt.Key_Down, Qt.Key_Minus]:
                self.motor_control_docked.sub_down()
            # elif event.key() == Qt.Key_Left:
            #     self.target_left()
            # elif event.key() == Qt.Key_Right:
            #     self.target_right()

        return super().eventFilter(source, event)


def main():
    app = PLDControlApp(sys.argv)
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
