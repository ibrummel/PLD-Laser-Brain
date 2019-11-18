# Imports
import RPi.GPIO as GPIO
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, QMessageBox, QDialog, QPushButton,
                             QSpacerItem, QWidget)
from pathlib import Path
from Arduino_Hardware import LaserBrainArduino
import Global_Values as Global


class RPiHardware(QWidget):

    sub_home = pyqtSignal()
    target_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Set the numbering scheme for GPIO pins to the Broadcom numbers (all pins designated by an integer)
        GPIO.setmode(GPIO.BCM)

        # Create arduino object for motor and laser control
        self.arduino = LaserBrainArduino('/dev/ttyACM0')

        # Create an instance of the HomeTargetsDialog for later use
        self.home_target_dialog = HomeTargetsDialog(self)

        # Create class variables for laser operation
        self.pulse_count_target = None
        self.triggers_sent = 0

        # Define limits/constants for substrate motion
        self.sub_position = 24000
        self.sub_rps = float(self.arduino.query_motor_parameters('sub', 'speed')) / Global.SUB_STEPS_PER_REV
        self.stored_sub_pos = 0

        self.current_target = round(float(self.arduino.query_motor_parameters('target', 'position')) / (Global.TARGET_STEPS_PER_REV / 6)) % 6
        self.move_to_target(self.current_target)
        self.target_rps = float(self.arduino.query_motor_parameters('target', 'speed')) / Global.TARGET_STEPS_PER_REV

        # Define class variables for
        self.in_pins = {"sub_home": 23, "aux": 17, 'laser_running': 19, 'targets_running': 20, 'sub_running': 21}
        self.low_pins = {}
        self.hi_pins = {"sub_home_hi": 22, 'arduino_reset': 16}

        self.setup_pins()

    def setup_pins(self):
        GPIO.setwarnings(False)
        # Set up pins (output pins are split by initialization value)
        for key in self.in_pins:
            # FIXME: not sure I want pull down here
            GPIO.setup(self.in_pins[key], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        # Build the event detect for the sub home switch
        GPIO.add_event_detect(self.in_pins['sub_home'], GPIO.RISING,
                              callback=self.gpio_emit,
                              bouncetime=200)

        for key in self.low_pins:
            GPIO.setup(self.low_pins[key], GPIO.OUT, initial=GPIO.LOW)

        for key in self.hi_pins:
            GPIO.setup(self.hi_pins[key], GPIO.OUT, initial=GPIO.HIGH)

    def gpio_emit(self, channel):
        if channel == self.in_pins['sub_home']:
            self.sub_home.emit()
        # Add other GPIO signals here with an elif then an emit for
        # the new signal

    def start_pulsing(self, reprate, pulse_count=None):
        # Update the laser reprate as appropriate
        self.arduino.update_laser_param('reprate', reprate)
        # Keep track of the pulse count and target
        self.pulse_count_target = pulse_count
        # If we have a pulse count target, feed it to the laser.
        # This will begin pulsing automatically.
        if pulse_count is not None:
            self.arduino.update_laser_param('goal', pulse_count)
        # If there is no pulse count target, start the laser manually
        elif pulse_count is None:
            self.arduino.update_laser_param('start')

    def stop_pulsing(self):
        # Stop the laser Note: this clears the goal position stored on the arduino
        self.arduino.halt_laser()
        # Get the number of pulses completed so we know how far off we were
        self.triggers_sent = self.arduino.query_laser_parameters('pulses')
        # ToDo: Consider setting pulses to zero in the arduino

    def home_sub(self):
        self.sub_home.connect(self.set_sub_home)

        # Start moving the substrate upward, will be stopped and home position
        # set by the function connected to the event switch
        self.arduino.update_motor_param('sub', 'start', 0)

    def set_sub_home(self):
        self.arduino.halt_motor('sub')
        # May be useful if I want to return to the previous position after homing
        self.stored_sub_pos = self.arduino.query_motor_parameters('sub', 'position')
        self.arduino.update_motor_param('sub', 'position', 0)
        self.sub_home.disconnect(self.set_sub_home)
        # Use this to return after homing
        # self.arduino.update_motor_param('sub', 'goal', self.stored_sub_pos)

    def move_sub_to(self, position):
        if Global.SUB_TOP < position < Global.SUB_BOTTOM:
            self.arduino.update_motor_param('sub', 'goal', position)
        else:
            print('Substrate position is out of range, sub max = {}, provided position = {}'.format(self.sub_bottom,
                                                                                                    position))

    def set_sub_speed(self, rps):
        self.sub_rps = rps
        # Send a speed update to the arduino based on the requested rps and steps per rev
        self.arduino.update_motor_param('sub', 'v', int(rps * Global.SUB_STEPS_PER_REV))

    def halt_sub(self):
        self.arduino.halt_motor('sub')

    def home_carousel(self):
        self.home_target_dialog.exec_()

        if self.home_target_dialog.result() == QDialog.Accepted:
            # Set pertinent variables to the home positions
            self.current_target = 0
            self.arduino.update_motor_param('target', 'position', 0)

            target_home_info = QMessageBox.information(self, 'Home Set',
                                                       'New target carousel home position set',
                                                       QMessageBox.Ok, QMessageBox.Ok)
        elif self.home_target_dialog.result() == QDialog.Rejected:
            target_home_info = QMessageBox.warning(self, 'Home Canceled',
                                                   'Target carousel home cancelled by user.',
                                                   QMessageBox.Ok, QMessageBox.Ok)

    def move_to_target(self, target_goal: int):
        # NOTE: No checking if we are already at the goal target because
        # we want the target to recenter in case of raster getting off
        # Note that range is not inclusive of last value so this checks if target goal is 0-5
        # ToDo: need to make sure that the laser stops before targets move and rastering is at least paused.
        #  otherwise it will mess up positional set.

        if target_goal in range(0, 6):
            self.arduino.update_motor_param('target', 'raster', 0)
            self.target_changed.emit()
            position = target_goal * (Global.TARGET_STEPS_PER_REV / 6)
            self.arduino.update_motor_param('target', 'goal', position)
            # Set current target based on the goal
            self.current_target = target_goal
        else:
            print('Invalid goal target supplied to move_to_target: {}'.format(target_goal))

    def raster_current_target(self):
        self.arduino.update_motor_param('target',
                                        'raster',
                                        self.parent.settings.lines_carousel_size[str(self.current_target)])

    def set_target_speed(self, rps):
        self.target_rps = rps
        # Send a speed update to the arduino based on the requested rps and steps per rev
        self.arduino.update_motor_param('target', 'speed', rps * Global.TARGET_STEPS_PER_REV)

    def halt_target(self):
        self.arduino.halt_motor('target')

    def targets_running(self):
        if GPIO.input(self.in_pins['targets_running']):
            return True
        else:
            return False

    def substrate_running(self):
        if GPIO.input(self.in_pins['substrate_running']):
            return True
        else:
            return False

    def laser_running(self):
        if GPIO.input(self.in_pins['laser_running']):
            return True
        else:
            return False

    def anything_running(self):
        if self.targets_running() or self.substrate_running() or self.laser_running():
            return True
        else:
            return False

    # ToDo: write out motor positions and status on delete so that they can be restored
    #  on program boot
    def __del__(self):
        GPIO.cleanup()


class HomeTargetsDialog(QDialog):
    def __init__(self, brain: RPiHardware):
        super().__init__()

        self.brain = brain
        self.setWindowTitle('Home Target Carousel')

        self.moving_right = False
        self.moving_left = False
        # Store the old speed and then set speed to a lower value so the
        # position is easier to control by hand.
        self.stored_speed = brain.arduino.query_motor_parameters('target', 'speed')
        self.brain.arduino.update_motor_param('target', 'speed', Global.TARGET_MANUAL_SPEED)

        self.right_btn = QPushButton()
        self.right_btn.setAutoRepeat(True)
        self.right_btn.setAutoRepeatInterval(Global.TARGET_STEPS_PER_REV / Global.TARGET_MANUAL_SPEED)
        self.right_btn.setAutoRepeatDelay(Global.AUTO_REPEAT_DELAY)

        self.left_btn = QPushButton()
        self.left_btn.setAutoRepeat(True)
        self.left_btn.setAutoRepeatInterval(Global.TARGET_STEPS_PER_REV / Global.TARGET_MANUAL_SPEED)
        self.left_btn.setAutoRepeatDelay(Global.AUTO_REPEAT_DELAY)

        self.left_icon = QIcon()
        self.right_icon = QIcon()
        right_btn_path = Path('src/img').absolute() / 'right.svg'
        left_btn_path = Path('src/img').absolute() / 'left.svg'
        self.right_icon.addFile(str(right_btn_path))
        self.left_icon.addFile(str(left_btn_path))
        self.right_btn.setIcon(self.right_icon)
        self.left_btn.setIcon(self.left_icon)

        self.apply_btn = QPushButton("Apply")
        self.cancel_btn = QPushButton("Cancel")

        # Install event filter on all buttons to make sure that arrow
        # keys are processed as target carousel move commands
        self.installEventFilter(self)
        self.right_btn.installEventFilter(self)
        self.right_btn.installEventFilter(self)
        self.apply_btn.installEventFilter(self)
        self.cancel_btn.installEventFilter(self)

        self.instruction_label = QLabel('Use the buttons below or the left and right arrow keys to align the ' +
                                        '"home mark" on the motor and coupling, then press Accept to confirm ' +
                                        'the new home position. Pressing reject will cancel the home routine ' +
                                        'and preserve current settings.')
        self.instruction_label.setWordWrap(True)

        self.hbox = QHBoxLayout()
        self.vbox = QVBoxLayout()

        self.init_layout()
        self.init_connections()

    def init_connections(self):
        self.right_btn.pressed.connect(self.right)
        self.right_btn.released.connect(self.halt)
        self.left_btn.pressed.connect(self.left)
        self.left_btn.released.connect(self.halt)

        self.apply_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def init_layout(self):
        self.setFixedWidth(700)
        self.setFixedHeight(230)
        self.hbox.addWidget(self.left_btn)
        self.hbox.addWidget(self.right_btn)
        self.hbox.addSpacerItem(QSpacerItem(220, 20))
        self.hbox.addWidget(self.apply_btn)
        self.hbox.addWidget(self.cancel_btn)

        self.vbox.addWidget(self.instruction_label)
        self.vbox.addSpacerItem(QSpacerItem(700, 28))
        self.vbox.addLayout(self.hbox)

        self.setLayout(self.vbox)

    def right(self):
        # ToDo: Check the if 0 or 1 goes left or right.
        self.brain.arduino.update_motor_param('target', 'start', Global.TARGET_CW)
        self.moving_right = True
        self.moving_left = False

    def left(self):
        self.brain.arduino.update_motor_param('target', 'start', Global.TARGET_CCW)
        self.moving_left = True
        self.moving_right = False

    def halt(self):
        self.brain.halt_target()
        self.moving_right = False
        self.moving_left = False

    # Override the accept and reject methods to reset speed after homing/cancelling
    def accept(self):
        self.brain.arduino.update_motor_param('target', 'speed', self.stored_speed)
        super().accept()

    def reject(self):
        self.brain.arduino.update_motor_param('target', 'speed', self.stored_speed)
        super().reject()

    # Override the event filter and the key release event to handle arrow keys
    # as movement controls
    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Right and self.moving_right is False:
                self.right()
            elif event.key() == Qt.Key_Left and self.moving_left is False:
                self.left()
        return super().eventFilter(source, event)

    def keyReleaseEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key_Right or key == Qt.Key_Left and not event.isAutoRepeat():
            self.halt()

