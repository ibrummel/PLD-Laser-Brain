# Imports
from gpiozero import OutputDevice, Button
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, pyqtSlot, QObject, QThread
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, QMessageBox, QDialog, QPushButton,
                             QSpacerItem, QWidget)
from pathlib import Path
from Arduino_Hardware import LaserBrainArduino
import Global_Values as Global
from time import sleep
import threading

# Subclass gpiozero devices to add a device name field for later references
class NamedOutputDevice(OutputDevice):
    def __init__(self, *args, **kwargs):
        try:
            self.dev_name = kwargs.pop('dev_name')
        except KeyError as err:
            print("No dev_name supplied, set to none")
            self.dev_name=None
        super().__init__(*args, **kwargs)

class NamedButton(Button):
    def __init__(self, *args, **kwargs):
        try:
            self.dev_name = kwargs.pop('dev_name')
        except KeyError as err:
            print("No dev_name supplied, set to none")
            self.dev_name=None
        super().__init__(*args, **kwargs)
        

class RPiHardware(QWidget):
    sub_bot = pyqtSignal()
    sub_top = pyqtSignal()
    target_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Define Pin Dictionaries
        hold_time = 0.01
        self.buttons = {'sub_bot': NamedButton(22, pull_up=False, hold_time=hold_time, dev_name='sub_bot'),
                        'sub_top': NamedButton(18, pull_up=False, hold_time=hold_time, dev_name='sub_top'),
                        'sub_run': NamedButton(21, pull_up=True, hold_time=hold_time, dev_name='sub_run'),
                        'target_run': NamedButton(20, pull_up=True, hold_time=hold_time, dev_name='target_run'),
                        'laser_run': NamedButton(19, pull_up=True, hold_time=hold_time, dev_name='laser_run')}
        
        self.high_pins = {'ard_rst': NamedOutputDevice(16, initial_value=True, dev_name='ard_rst'),
                          'top_hi': NamedOutputDevice(27, initial_value=True, dev_name='top_hi'),
                          'bot_hi': NamedOutputDevice(23, initial_value=True, dev_name='bot_hi')}

        self.gpio_handler = GPIOHandler(buttons=self.buttons, high_pins=self.high_pins,
                                        sig_print=False, parent=self)
        
        sleep(1)
        self.gpio_handler.sig_gpio_int_input.connect(self.print_gpio)
        print("RPi thread: ", threading.get_ident())
        print("Sleeping 5 after setup")
        sleep(5)
        self.gpio_handler.sig_gpio_int_input.emit(-9999)

    @pyqtSlot(int)
    def print_gpio(self, channel):
        print("GPIO Signal Emitted and acted on from channel {}".format(channel))

    # ToDo: write out motor positions and status on delete so that they can be restored
    #  on program boot


class GPIOHandler(QObject):
    # Place signals for each pin here
    sig_gpio_int_input = pyqtSignal(int)

    def __init__(self, buttons: dict, high_pins=None, comm_pins=None, low_pins=None, sig_print=False, parent=None):
        super().__init__()
        # Set a class variable to decide if signals will have print messages on emit
        self.sig_print = sig_print
        self.parent = parent
        print("GPIO Handler thread: ", threading.get_ident())

        # If Low_pins is provided, check that it is a dictionary then set it to a class variable,
        # else raise TypeError
        if low_pins is None:
            self.low_pins = {}
        elif isinstance(low_pins, dict):
            self.low_pins = low_pins
        else:
            raise TypeError("Invalid type supplied for low_pins, should be a dict")

        # If high_pins is provided, check that it is a dictionary then set it to a class variable,
        # else raise TypeError
        if high_pins is None:
            self.high_pins = {}
        elif isinstance(high_pins, dict):
            self.high_pins = high_pins
        else:
            raise TypeError("Invalid type supplied for high_pins, should be a dict")
        
        # Check that in_pins is a dictionary then set it to a class variable, else raise TypeError
        if isinstance(buttons, dict):
            self.buttons = buttons
            for key, button in self.buttons.items():
                button.when_held = self.gpio_callback
        else:
            raise TypeError("Invalid type supplied for buttons, should be a dict")

    def gpio_callback(self, device):
        print("Device {} thread: ".format(device.dev_name), threading.get_ident())
        if device in self.buttons.values():
            if self.sig_print:
                print("Device on {} ({}) activated".format(device.pin, device.dev_name))
            self.sig_gpio_int_input.emit(int(str(device.pin).strip("GPIO")))
        else:
            print("GPIO callback activated from channel {}, which is not in the list of input pins".format(device.pin))

    def add_gpio(self, channel: int, name: str, function, pull_up_down=None, initial=None):
        # Needs to be rewritten to use gpiozero
        pass


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
