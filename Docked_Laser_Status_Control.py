from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer, QRegExp, pyqtSignal
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QLabel, QLineEdit, QPushButton,
                             QWidget, QMessageBox, QDockWidget)
from Laser_Hardware import CompexLaser
from pyvisa.errors import VisaIOError
from time import sleep
import Global_Values as Global
from RPi_Hardware import RPiHardware


class LaserStatusControl(QDockWidget):

    laser_manual_stop = pyqtSignal()

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
        self.out_modes = {'Energy': 'EGY NGR', 'HV': 'HV'}

        # Pull in operating interfaces
        self.laser = laser
        self.brain = brain

        # Laser Polling/Disconnected Mode
        self.timer_laser_status_polling = QTimer()
        self.timer_laser_status_polling.setInterval(1000)
        self.failed_reads = 0
        self.laser_connected = True

        # Add items to the laser mode combo
        self.combos['laser_mode'].addItems(self.inModes.values())

        # ToDo: Move all of these into the CompexLaser class so that there are less calls to update them and less
        #  places to lose track of their values.

        # Create widgets and other GUI elements
        self.current_egy = self.laser.rd_energy()
        # self.lines['energy'].setValidator(QIntValidator(50, 510))
        self.current_hv = self.laser.rd_hv()
        # self.lines['voltage'].setValidator(QDoubleValidator(18, 27, 1))
        self.timer_lsc_update = QTimer()
        self.timer_check_warmup = QTimer()

        self.init_connections()
        self.update_pulse_counter()  # Reads the current pulse counter value

    def init_connections(self):
        # Mode Selection Box. Will default to current laser running mode
        # Sets the mode again using the current mode in order to set the line edits as enabled/disabled on open
        curr_mode = self.inModes[self.laser.rd_mode()]
        self.change_mode(curr_mode)
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
        self.lines['reprate'].returnPressed.connect(lambda: self.brain.set_reprate(int(self.lines['reprate'].text())))

        # Number of pulses line, when enter is pressed should start the laser.
        self.lines['num_pulses'].returnPressed.connect(self.change_on_off)

        # Set up check boxes. Default set external trigger check
        # based on current laser configuration
        if self.laser.trigger_src == "EXT":
            self.checks['ext_trigger'].setChecked(True)
        self.checks['ext_trigger'].stateChanged.connect(self.change_trigger)

        # Laser start/stop button for making pew pew
        self.btns['start_stop'].clicked.connect(self.change_on_off)

        # Moved from main() into the function
        self.timer_lsc_update.timeout.connect(self.update_lsc)
        self.timer_lsc_update.start(int(1000 / int(self.laser.reprate)))

        self.timer_check_warmup.setInterval(1000)
        self.timer_check_warmup.timeout.connect(self.check_warmup)

        self.timer_laser_status_polling.timeout.connect(lambda: self.update_lsc(check_connected=True))

        self.brain.laser_finished.connect(self.change_on_off)
        self.brain.laser_finished.connect(self.update_pulse_counter)

    def update_lsc(self, check_connected=False):
        # Updater for the laser status readouts. Only updates for fields that are
        # not currently selected.
        if self.laser_connected or check_connected:
            try:
                if not self.lines['energy'].hasFocus():
                    self.lines['energy'].setText(self.laser.rd_energy())
                sleep(Global.OP_DELAY)

                if not self.lines['voltage'].hasFocus():
                    self.lines['voltage'].setText(self.laser.rd_hv())
                sleep(Global.OP_DELAY)

                if not self.lines['reprate'].hasFocus():
                    self.lines['reprate'].setText(str(self.laser.reprate))
                sleep(Global.OP_DELAY)

                self.lines['tube_press'].setText(self.laser.rd_tube_press())
                sleep(Global.OP_DELAY)
            except VisaIOError as err:
                # Print error if the laser is believed to be connected
                if self.laser_connected:
                    print("{}: Error on reading status from the laser. Error message: {}".format(self.failed_reads, err),)
                # Increment number of failed reads
                self.failed_reads += 1
                # If there have been 10 consecutive failed reads move to disconnected state
                if self.failed_reads >= 10 and self.laser_connected:
                    self.laser_connected = False
                    print("Laser disconnected. Polling for reconnection...")
                    self.timer_laser_status_polling.start()
                return

            # If the status update completes set connected status to true and reset the failed read counter
            self.laser_connected = True
            self.failed_reads = 0
            if check_connected:
                print("Laser reconnected...")
                self.timer_laser_status_polling.stop()

    def update_pulse_counter(self):
        self.lines['pulse_counter'].setText(str(self.laser.rd_user_counter()))

    def terminal_send(self):
        # Sends the command that was typed into the terminal.
        try:
            self.terminal.setText(self.laser.query(self.terminal.text()))
            print("Terminal Command Sent")
        except:
            print("An error occurred on sending terminal command")

    def change_mode(self, mode):
        # Sends a command to the laser to change mode. Also sets which parameters
        # are editable from the LSC.
        self.laser.set_mode(self.out_modes[mode])
        if self.out_modes[mode] == 'HV':
            self.lines['energy'].setDisabled(True)
            self.lines['voltage'].setDisabled(False)
        if self.out_modes[mode] == 'EGY NGR':
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
        self.timer_lsc_update.stop()
        sleep(Global.OP_DELAY)

        try:
            num_pulses = int(self.lines['num_pulses'].text())
        except ValueError as err:
            num_pulses = None

        if self.laser.rd_opmode() in on_opmodes:
            self.brain.stop_laser()
            if num_pulses is not None:
                self.lines['num_pulses'].setText('')
            self.laser_manual_stop.emit()
            self.btns['start_stop'].setChecked(False)
            self.btns['start_stop'].setText('Start Laser')
        elif self.laser.rd_opmode() == 'OFF:31':
            self.laser_timeout_handler()
        elif self.laser.rd_opmode() == 'OFF:21':
            # FIXME: Add a countdown timer?
            self.btns['start_stop'].setDisabled(True)
            self.timer_check_warmup.start()  # Starts a timer that will check if the warmup is over every second
            self.warmup_warn()
        # If the laser is currently in an off state
        else:
            self.brain.start_laser(num_pulses=num_pulses)
            self.btns['start_stop'].setChecked(True)
            self.btns['start_stop'].setText('Stop Laser')

        # Re-enables the updater for the LSC after handling start/stop
        sleep(Global.OP_DELAY)
        try:
            self.timer_lsc_update.start(int(1000 / int(self.laser.rd_reprate())))
        except VisaIOError:
            # If the reprate fails to read, set timer to update at 5Hz
            self.timer_lsc_update.start(200)

    def check_warmup(self):
        curr_opmode = self.laser.rd_opmode()
        if curr_opmode == 'OFF:0':
            self.timer_check_warmup.stop()
            self.btns['start_stop'].setDisabled(False)
            self.btns['start_stop'].setChecked(False)
        elif curr_opmode == 'OFF:21':
            pass  # Nothing to do if the laser is still in warmup mode
        elif curr_opmode == 'OFF:31':
            self.laser_timeout_handler()

    def laser_timeout_handler(self):
        timeout_clear = QMessageBox.question(self, 'Laser Status: Timeout',
                                             "Press Ok to clear laser\
                                             timeout and start lasing.",
                                             QMessageBox.Ok |
                                             QMessageBox.Cancel,
                                             QMessageBox.Cancel)
        if timeout_clear == QMessageBox.Ok:
            self.laser.set_timeout(False)
            sleep(Global.OP_DELAY)
            self.laser.off()
            self.btns['start_stop'].setChecked(False)
        elif timeout_clear == QMessageBox.Cancel:
            pass

    def warmup_warn(self):
        warmup_clear = QMessageBox.question(self, 'Laser Status: Warm-Up',
                                            "Start/stop button will be enabled when the warmup ends.",
                                            QMessageBox.Ok, QMessageBox.Ok)

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
