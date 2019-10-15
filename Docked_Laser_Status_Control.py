from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import (QCheckBox, QComboBox,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
                             QWidget, QMessageBox, QFormLayout)
from VISA_Communications import VisaLaser
import time
from RPi_Hardware import RPiHardware


class LaserStatusControl(QWidget):

    def __init__(self, laser: VisaLaser, brain: RPiHardware):
        super().__init__()

        # Set up permissible modes list
        self.inModes = {'EGY NGR': 'Energy', 'HV': 'HV'}
        self.outModes = {'Energy': 'EGY NGR', 'HV': 'HV'}

        # Pull in parameters
        self.laser = laser
        self.brain = brain

        # Create internal variables and set values
        self.ext_reprate_current = self.laser.rd_reprate()

        # Create widgets and other GUI elements
        self.modeSelLabel = QLabel('Mode: ')
        self.modeSel = QComboBox()

        self.egyLabel = QLabel('Energy: ')
        self.current_egy = self.laser.rd_energy()
        self.egy_val = QLineEdit(self.current_egy)
        self.egy_val.setValidator(QIntValidator(50, 510))

        self.hvLabel = QLabel('HV: ')
        self.current_hv = self.laser.rd_hv()
        self.hv_val = QLineEdit(self.current_hv)
        self.hv_val.setValidator(QDoubleValidator(18, 27, 1))

        self.reprateLabel = QLabel('Reprate: ')
        self.int_reprate_current = self.laser.rd_reprate()
        self.reprate_val = QLineEdit(self.int_reprate_current)
        self.reprate_val.setValidator(QIntValidator(0, 20))  # Laser caps at 50, but >20 needs cooling water

        self.extTriggerCheck = QCheckBox()

        self.checkForm = QFormLayout()
        self.checkForm.addRow('EXT Trig?', self.extTriggerCheck)

        self.btnOnOff = QPushButton("Start Laser")

        self.terminal = QLineEdit()
        self.hbox = QHBoxLayout()
        self.vbox = QVBoxLayout()
        self.updateTimer = QTimer()

        # Define/Create widgets for laser status and control
        self.title = QLabel('Laser Status')

        # Run function to adjust widget parameters/build the LSC
        self.init_ui()

    def init_ui(self):
        """Manipulate and adjust laser status and manual control widgets"""
        # Create and format title for LSC block
        self.title.setAlignment(Qt.AlignCenter)
        # FIXME: Change how this is handled to be general to other instances
        self.title.setFont(QFont('Arial', 24, QFont.Bold))

        # Mode Selection Box. Will default to current laser running mode
        self.modeSel.addItems(self.inModes.values())
        # FIXME: Might want to force the laser into EGY NGR or HV mode if any
        # other mode is detected (i.e. index=-1)
        index = self.modeSel.findText(self.inModes[self.laser.rd_mode()])
        self.modeSel.setCurrentIndex(index)
        self.modeSel.currentTextChanged.connect(self.change_mode)

        # Energy reading/setting box: while laser is running, will display
        # last pulse avg value, otherwise will display setting for egy mode
        # and last pulse energy for hv mode.
        self.egy_val.returnPressed.connect(self.set_energy)

        # HV setting box: Displays currently set HV for HV mode. For EGY mode
        # displays the HV set by the laser to match energy setting.
        self.hv_val.returnPressed.connect(self.set_hv)

        # Reprate setting box: Displays current reprate. Will display "EXT" if
        # the laser is set to external triggering
        self.reprate_val.returnPressed.connect(self.set_reprate)

        # Set up check boxes. Default set external trigger check
        # based on current laser configuration
        if self.laser.rd_trigger() == "EXT":
            self.extTriggerCheck.setChecked(True)
        self.extTriggerCheck.stateChanged.connect(self.change_trigger)

        # Start Stop Button
        # self.btnOnOff.setAlignment(Qt.AlignCenter)
        self.btnOnOff.clicked.connect(self.change_on_off)

        # Terminal box for debug
        self.terminal.setPlaceholderText('Enter a command here')
        self.terminal.returnPressed.connect(self.terminal_send)

        # Create a Horizontal Layout to contain the value and setting boxes
        self.hbox.addWidget(self.modeSelLabel)
        self.hbox.addWidget(self.modeSel)
        self.hbox.addWidget(self.egyLabel)
        self.hbox.addWidget(self.egy_val)
        self.hbox.addWidget(self.hvLabel)
        self.hbox.addWidget(self.hv_val)
        self.hbox.addWidget(self.reprateLabel)
        self.hbox.addWidget(self.reprate_val)
        self.hbox.addLayout(self.checkForm)

        # Create a vertical box to set up title and LSC boxes
        self.vbox.addWidget(self.title)
        self.vbox.addLayout(self.hbox)
        self.vbox.addWidget(self.btnOnOff)
        # self.vbox.addWidget(self.btnPauseUpdate)
        self.vbox.addWidget(self.terminal)

        self.setLayout(self.vbox)
        self.change_mode(self.modeSel.currentText())

        # Moved from main() into the function
        self.updateTimer.timeout.connect(self.update_lsc)
        self.updateTimer.start(int(1000 / int(self.laser.rd_reprate())))

    # Updater for the laser status readouts. Only updates for fields that are
    # not currently selected.
    def update_lsc(self):
        on_opmodes = ['ON', 'OFF,WAIT']
        if not self.egy_val.hasFocus():
            self.egy_val.setText(self.laser.rd_energy())

        if not self.hv_val.hasFocus():
            self.hv_val.setText(self.laser.rd_hv())

        if not self.reprate_val.hasFocus():
            if self.laser.rd_trigger() == 'INT':
                self.reprate_val.setText(self.laser.rd_reprate())
            elif self.laser.rd_trigger() == 'EXT':
                self.reprate_val.setText(self.ext_reprate_current)

        if self.laser.rd_opmode() in on_opmodes:
            if self.laser.rd_trigger() == 'INT':
                self.btnOnOff.setText('Stop Laser (INT Trigger)')
            elif self.laser.rd_trigger() == 'EXT':
                self.btnOnOff.setText('Stop Laser (EXT Trigger)')
        else:
            self.btnOnOff.setText('Start Laser')

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
            self.egy_val.setDisabled(True)
            self.hv_val.setDisabled(False)
        if self.outModes[mode] == 'EGY NGR':
            self.egy_val.setDisabled(False)
            self.hv_val.setDisabled(True)

    def change_trigger(self):
        if self.extTriggerCheck.isChecked():
            self.laser.set_trigger('EXT')
        elif not self.extTriggerCheck.isChecked():
            self.laser.set_trigger('INT')

    def change_on_off(self):
        on_opmodes = ['ON', 'OFF,WAIT']
        # On button press stops the timer that updates the display so that
        # we don't see timeouts on pressing the button to stop/start
        self.updateTimer.stop()
        time.sleep(0.01)

        if self.laser.rd_opmode() in on_opmodes:
            if self.laser.rd_trigger() == 'INT':
                self.laser.off()
            elif self.laser.rd_trigger() == 'EXT':
                self.brain.stop_pulsing()
                self.laser.off()

            self.btnOnOff.setText('Start Laser')

        elif self.laser.rd_opmode() == 'OFF:31':
            self.laser_timeout_handler()

        elif self.laser.rd_opmode() == 'OFF:21':
            # FIXME: Add a countdown timer?
            self.warmup_warn()

        else:
            if self.laser.rd_trigger() == 'EXT':
                self.laser.on()
                time.sleep(0.01)
                print('Sent laser on. Laser Status: {}'.format(self.laser.rd_opmode()))
                QTimer.singleShot(3000, lambda: self.brain.start_pulsing(self.ext_reprate_current))
                self.btnOnOff.setText('Stop External Trigger')
            elif self.laser.rd_trigger() == 'INT':
                self.laser.on()
                self.btnOnOff.setText('Stop Internal Trigger')

        # Re-enables the updater for the LSC
        time.sleep(0.01)
        self.updateTimer.start(int(1000 / int(self.laser.rd_reprate())))

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
            self.btnOnOff.setText('Stop Laser')
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
        if 50 <= int(self.egy_val.text()) <= 510:
            self.current_egy = self.egy_val.text()
            self.laser.set_energy(self.current_egy)
        else:
            value_error = QMessageBox.question(self, 'Value Error',
                                               'The energy value entered is not within acceptable limits. Energy value\
                                                will be reset to last good value.',
                                               QMessageBox.Ok, QMessageBox.Ok)
            if value_error == QMessageBox.Ok:
                self.egy_val.setText(self.current_egy)
        self.egy_val.clearFocus()

    def set_hv(self):
        if 18.0 <= float(self.hv_val.text()) <= 27.0:
            self.current_hv = self.hv_val.text()
            self.laser.set_hv(self.current_hv)
        else:
            value_error = QMessageBox.question(self, 'Value Error',
                                               'The HV value entered is not within acceptable limits. HV value will\
                                               be reset to last good value.',
                                               QMessageBox.Ok, QMessageBox.Ok)
            if value_error == QMessageBox.Ok:
                self.hv_val.setText(self.current_hv)
        self.hv_val.clearFocus()

    def set_reprate(self):
        if self.laser.rd_trigger() == 'INT':
            if 1 <= int(self.reprate_val.text()) <= 30:
                self.int_reprate_current = self.reprate_val.text()
                self.laser.set_reprate(self.int_reprate_current)
            else:
                value_error = QMessageBox.question(self, 'Value Error',
                                                   'The repitition rate entered is not within acceptable limits. Repitition\
                                                   rate will be reset to last good value.',
                                                   QMessageBox.Ok, QMessageBox.Ok)
                if value_error == QMessageBox.Ok:
                    self.reprate_val.setText(self.int_reprate_current)
        elif self.laser.rd_trigger() == 'EXT':
            if 1 <= int(self.reprate_val.text()) <= 30:
                self.ext_reprate_current = self.reprate_val.text()
                self.brain.start_pulsing(self.ext_reprate_current)
            else:
                value_error = QMessageBox.question(self, 'Value Error',
                                                   'The repitition rate entered is not within acceptable limits. Repitition\
                                                   rate will be reset to last good value.',
                                                   QMessageBox.Ok, QMessageBox.Ok)
                if value_error == QMessageBox.Ok:
                    self.reprate_val.setText(self.ext_reprate_current)
        self.reprate_val.clearFocus()