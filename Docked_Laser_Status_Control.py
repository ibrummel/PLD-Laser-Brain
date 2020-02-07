from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer, QRegExp
from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QLabel, QLineEdit, QPushButton,
                             QWidget, QMessageBox, QDockWidget)
from Laser_Hardware import CompexLaser
import time
from RPi_Hardware import RPiHardware


class LaserStatusControl(QDockWidget):

    def __init__(self, laser: CompexLaser, brain: RPiHardware):
        super().__init__()

        # Load UI and discover necessary items
        uic.loadUi('./src/ui/docked_laser_status_control.ui', self)

        self.btns = {widget.objectName().split('btn_')[1]: widget
                     for widget in self.findChildren(QPushButton, QRegExp('btn_*'))}
        self.lines = {widget.objectName().split('line_')[1]: widget
                      for widget in self.findChildren(QLineEdit, QRegExp('line_*'))}
        self.labels = {widget.objectName().split('lbl_')[1]: widget
                       for widget in self.findChildren(QLabel, QRegExp('lbl_*'))}
        self.checks = {widget.objectName().split('check_')[1]: widget
                       for widget in self.findChildren(QCheckBox, QRegExp('check_*'))}
        self.combos = {widget.objectName().split('combo_')[1]: widget
                       for widget in self.findChildren(QComboBox, QRegExp('combo_*'))}

        # Set up permissible modes list
        self.inModes = {'EGY NGR': 'Energy', 'HV': 'HV'}
        self.outModes = {'Energy': 'EGY NGR', 'HV': 'HV'}
        
        # Pull in operating interfaces
        self.laser = laser
        self.brain = brain
        
        # Add items to the laser mode combo
        self.combos['laser_mode'].addItems(self.inModes.values())
        # Sets the mode again using the current mode in order to set the line edits as enabled/disabled on open
        curr_mode = self.inModes[self.laser.rd_mode()]
        self.change_mode(curr_mode)

        # ToDo: Move all of these into the CompexLaser class so that there are less calls to update them and less
        #  places to lose track of their values.
        # Create internal variables and set values
        reprate = self.laser.rd_reprate()
        self.ext_reprate_current = reprate
        self.int_reprate_current = reprate
        # Create widgets and other GUI elements
        self.current_egy = self.laser.rd_energy()
        # self.lines['energy'].setValidator(QIntValidator(50, 510))
        self.current_hv = self.laser.rd_hv()
        # self.lines['voltage'].setValidator(QDoubleValidator(18, 27, 1))
        self.update_timer = QTimer()

        # Run function to adjust widget parameters/build the LSC
        self.init_connections()

    def init_connections(self):
        # Mode Selection Box. Will default to current laser running mode
        self.combos['laser_mode'].currentTextChanged.connect(self.change_mode)

        # Energy reading/setting box: while laser is running, will display
        # last pulse avg value, otherwise will display setting for egy mode
        # and last pulse energy for hv mode.
        self.lines['energy'].returnPressed.connect(self.set_energy)

        # HV setting box: Displays currently set HV for HV mode. For EGY mode
        # displays the HV set by the laser to match energy setting.
        self.lines['voltage'].returnPressed.connect(self.set_hv)

        # Reprate setting box: Displays current reprate. Will display "EXT" if
        # the laser is set to external triggering
        self.lines['reprate'].returnPressed.connect(self.set_reprate)

        # Set up check boxes. Default set external trigger check
        # based on current laser configuration
        if self.laser.trigger_src == "EXT":
            self.checks['ext_trigger'].setChecked(True)
        self.checks['ext_trigger'].stateChanged.connect(self.change_trigger)

        # Laser start/stop button for making pew pew
        self.btns['start_stop'].clicked.connect(self.change_on_off)

        # Moved from main() into the function
        self.update_timer.timeout.connect(self.update_lsc)
        self.update_timer.start(int(1000 / int(self.laser.rd_reprate())))

    # Updater for the laser status readouts. Only updates for fields that are
    # not currently selected.
    def update_lsc(self):
        on_opmodes = ['ON', 'OFF,WAIT']
        if not self.lines['energy'].hasFocus():
            self.lines['energy'].setText(self.laser.rd_energy())

        if not self.lines['voltage'].hasFocus():
            self.lines['voltage'].setText(self.laser.rd_hv())

        if not self.lines['reprate'].hasFocus():
            if self.laser.trigger_src == 'INT':
                self.lines['reprate'].setText(self.laser.rd_reprate())
            elif self.laser.trigger_src == 'EXT':
                self.lines['reprate'].setText(self.ext_reprate_current)

        self.lines['tube_press'].setText(self.laser.rd_tube_press())

    # Sends the command that was typed into the terminal.
    def terminal_send(self):
        try:
            self.terminal.setText(self.laser.query(self.terminal.text()))
            print("Terminal Command Sent")
        except:
            print("An error occurred on sending terminal command")

    # Sends a command to the laser to change mode. Also sets which parameters
    # are editable from the LSC.
    def change_mode(self, mode):
        self.laser.set_mode(self.outModes[mode])
        if self.outModes[mode] == 'HV':
            self.lines['energy'].setDisabled(True)
            self.lines['voltage'].setDisabled(False)
        if self.outModes[mode] == 'EGY NGR':
            self.lines['energy'].setDisabled(False)
            self.lines['voltage'].setDisabled(True)

    def change_trigger(self):
        if self.checks['ext_trigger'].isChecked():
            self.laser.set_trigger('EXT')
        elif not self.checks['ext_trigger'].isChecked():
            self.laser.set_trigger('INT')

    def change_on_off(self):
        on_opmodes = ['ON', 'OFF,WAIT']
        # On button press stops the timer that updates the display so that
        # we don't see timeouts on pressing the button to stop/start
        self.update_timer.stop()
        time.sleep(0.01)

        if self.laser.rd_opmode() in on_opmodes:
            if self.laser.trigger_src == 'EXT':
                self.brain.stop_laser()

            self.btns['start_stop'].setChecked(False)
            self.btns['start_stop'].setText('Start Laser')
        elif self.laser.rd_opmode() == 'OFF:31':
            self.laser_timeout_handler()
        elif self.laser.rd_opmode() == 'OFF:21':
            # FIXME: Add a countdown timer?
            self.warmup_warn()
        # If the laser is currently in an off state
        else:
            self.brain.start_laser()
            self.btns['start_stop'].setChecked(True)
            self.btns['start_stop'].setText('Stop Laser')

        # Re-enables the updater for the LSC after handling start/stop
        time.sleep(0.05)
        self.update_timer.start(int(1000 / int(self.laser.rd_reprate())))

    def laser_timeout_handler(self):
        timeout_clear = QMessageBox.question(self, 'Laser Status: Timeout',
                                             "Press Ok to clear laser\
                                             timeout and start lasing.",
                                             QMessageBox.Ok |
                                             QMessageBox.Cancel,
                                             QMessageBox.Cancel)
        if timeout_clear == QMessageBox.Ok:
            self.laser.set_timeout(False)
            time.sleep(0.01)
            self.laser.on()
            self.btns['start_stop'].setText('Stop Laser')
        elif timeout_clear == QMessageBox.Cancel:
            pass

    def warmup_warn(self):
        warmup_clear = QMessageBox.question(self, 'Laser Status: Warm-Up',
                                            "Press retry to check again if the warmup is over, cancel to wait",
                                            QMessageBox.Retry |
                                            QMessageBox.Cancel,
                                            QMessageBox.Retry)
        if warmup_clear == QMessageBox.Ok and self.laser.rd_opmode() == 'OFF:21':
            self.warmup_warn()
        elif warmup_clear == QMessageBox.Ok and not self.laser.rd_opmode() == 'OFF:21':
            notify = QMessageBox.question(self, 'Laser Warmup Complete', 'Laser is ready for use',
                                          QMessageBox.Ok, QMessageBox.Ok)
            if notify == QMessageBox.Ok:
                pass

    # def pause_LSC(self):
    #     self.isLSCUpdating = not self.isLSCUpdating
    #     if self.isLSCUpdating:
    #         self.updateTimer.stop()
    #     elif not self.isLSCUpdating:
    #         self.updateTimer.start(1000 / int(self.laser.rd_reprate()))

    def set_energy(self):
        if 50 <= int(self.lines['energy'].text()) <= 510:
            self.current_egy = self.lines['energy'].text()
            self.laser.set_energy(self.current_egy)
        else:
            value_error = QMessageBox.question(self, 'Value Error',
                                               'The energy value entered is not within acceptable limits. Energy value\
                                                will be reset to last good value.',
                                               QMessageBox.Ok, QMessageBox.Ok)
            if value_error == QMessageBox.Ok:
                self.lines['energy'].setText(self.current_egy)
        self.lines['energy'].clearFocus()

    def set_hv(self):
        if 18.0 <= float(self.lines['voltage'].text()) <= 27.0:
            self.current_hv = self.lines['voltage'].text()
            self.laser.set_hv(self.current_hv)
        else:
            value_error = QMessageBox.question(self, 'Value Error',
                                               'The HV value entered is not within acceptable limits. HV value will\
                                               be reset to last good value.',
                                               QMessageBox.Ok, QMessageBox.Ok)
            if value_error == QMessageBox.Ok:
                self.lines['voltage'].setText(self.current_hv)
        self.lines['voltage'].clearFocus()

    def set_reprate(self):
        if self.laser.trigger_src == 'INT':
            if 1 <= int(self.lines['reprate'].text()) <= 30:
                self.int_reprate_current = self.lines['reprate'].text()
                self.laser.set_reprate(self.int_reprate_current)
            else:
                value_error = QMessageBox.question(self, 'Value Error',
                                                   'The repitition rate entered is not within acceptable limits. Repitition\
                                                   rate will be reset to last good value.',
                                                   QMessageBox.Ok, QMessageBox.Ok)
                if value_error == QMessageBox.Ok:
                    self.lines['reprate'].setText(self.int_reprate_current)
        elif self.laser.trigger_src == 'EXT':
            if 1 <= int(self.lines['reprate'].text()) <= 30:
                self.ext_reprate_current = self.lines['reprate'].text()
                self.brain.start_pulsing(self.ext_reprate_current)
            else:
                value_error = QMessageBox.question(self, 'Value Error',
                                                   'The repitition rate entered is not within acceptable limits. Repitition\
                                                   rate will be reset to last good value.',
                                                   QMessageBox.Ok, QMessageBox.Ok)
                if value_error == QMessageBox.Ok:
                    self.lines['reprate'].setText(self.ext_reprate_current)
        self.lines['reprate'].clearFocus()
