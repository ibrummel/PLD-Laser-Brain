# Imports
import RPi.GPIO as GPIO
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, pyqtSlot, QObject
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, QMessageBox, QDialog, QPushButton,
                             QSpacerItem, QWidget)
from pathlib import Path
from Arduino_Hardware import LaserBrainArduino
import Global_Values as Global


class RPiHardware(QWidget):
    sub_bot = pyqtSignal()
    sub_top = pyqtSignal()
    target_changed = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Define Pin Dictionaries
        self.in_pins = {22: 'sub_bot', 23: 'sub_top', 21: 'sub_run', 20: 'target_run', 19: 'laser_run'}
        self.high_pins = {16: 'ard_rst'}

        self.gpio_handler = GPIOHandler(in_pins=self.in_pins, high_pins=self.high_pins, sig_print=False)
        self.gpio_handler.sig_gpio_int_input.connect(self.print_gpio)

    @pyqtSlot
    def print_gpio(self, channel: int):
        print("GPIO Signal Emitted and acted on from channel {}".format(channel))

    # ToDo: write out motor positions and status on delete so that they can be restored
    #  on program boot
    def __del__(self):
        GPIO.cleanup()


class GPIOHandler(QObject):
    # Place signals for each pin here
    sig_gpio_int_input = pyqtSignal(int)

    def __init__(self, in_pins: dict, high_pins=None, low_pins=None, sig_print=False, parent=None):
        super().__init__(parent=parent)

        # Manage GPIO Initial Setup
        GPIO.setmode(GPIO.BCM)

        # Set a class variable to decide if signals will have print messages on emit
        self.sig_print = sig_print

        # If Low_pins is provided, check that it is a dictionary then initialize pins, else raise TypeError
        if low_pins is None:
            self.low_pins = {}
        elif isinstance(low_pins, dict):
            self.low_pins = low_pins
            for pin_num in low_pins:
                GPIO.setup(pin_num, GPIO.OUT, initial=GPIO.LOW)
        else:
            raise TypeError("Invalid type supplied for low_pins")

        # If high_pins is provided, check that it is a dictionary then initialize pins, else raise TypeError
        if high_pins is None:
            self.high_pins = {}
        elif isinstance(high_pins, dict):
            self.high_pins = high_pins
            for pin_num in high_pins:
                GPIO.setup(pin_num, GPIO.OUT, initial=GPIO.HIGH)
        else:
            raise TypeError("Invalid type supplied for low_pins")

        # Check that in_pins is a dictionary and initialize pins, else raise TypeError
        if isinstance(in_pins, dict):
            self.in_pins = in_pins
            for pin_num in self.in_pins:
                GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(pin_num, GPIO.FALLING, callback=self.gpio_callback, bouncetime=500)
        else:
            raise TypeError("Invalid type supplied for low_pins")

    def gpio_callback(self, channel):
        if channel in self.in_pins:
            if self.sig_print:
                print("Channel {} ({}) activated".format(channel, self.in_pins[channel]))
            self.sig_gpio_int_input.emit(channel)
        else:
            print("GPIO callback activated from channel {}, which is not in the list of input pins".format(channel))

    def add_gpio(self, channel: int, name: str, function, pull_up_down=None, initial=None):
        try:
            if function == GPIO.IN:
                if pull_up_down != GPIO.PUD_UP or pull_up_down != GPIO.PUD_DOWN:
                    raise ValueError("Invalid value for PUD state for GPIO.IN pin: {}".format(pull_up_down))
                GPIO.setup(channel, function, pull_up_down=pull_up_down)
                self.in_pins.update({channel: name})

            elif function == GPIO.OUT:
                if initial == GPIO.HIGH:
                    GPIO.setup(channel, function, initial=initial)
                    self.high_pins.update({channel, name})
                elif initial == GPIO.LOW:
                    GPIO.setup(channel, function, initial=initial)
                    self.low_pins.update({channel, name})
                else:
                    print("Invalid value for initial state of GPIO.OUT pin: {}".format(initial))
        except ValueError as err:
            print(err)
        except AttributeError as err:
            print(err)
        except TypeError as err:
            print(err)


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
