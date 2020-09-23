# Imports
from Named_gpiozero import NamedButton, NamedOutputDevice
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, pyqtSlot, QObject, QTimer
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, QDialog, QPushButton,
                             QSpacerItem, QWidget)
from pathlib import Path
from Laser_Hardware import CompexLaser
from Arduino_Hardware import LaserBrainArduino
from time import sleep
import numpy as np
import threading
from warnings import warn
import Global_Values as Global
from math import ceil


class RPiHardware(QWidget):
    sub_bot = pyqtSignal()
    sub_top = pyqtSignal()
    target_changed = pyqtSignal()
    laser_finished = pyqtSignal()
    laser_time_to_completion = pyqtSignal(int)

    def __init__(self, laser: CompexLaser, arduino: LaserBrainArduino):
        super().__init__()
        # Set up access to the passed laser control object and get current params
        self.laser = laser
        self.arduino = arduino

        # Set up class variables
        self.homing_sub = False  # Status flag that indicates if the substrate is being homed.
        self.laser_start_delay_msec = 4500
        # Setup timer to check when external trigger pulses finish.
        self.timer_check_laser_finished = QTimer()
        self.timer_check_laser_finished.timeout.connect(self.check_laser_finished)

        # Define Pin Dictionaries
        hold_time = 0.01
        self.buttons = {'sub_bot': NamedButton(22, pull_up=False, hold_time=hold_time, dev_name='sub_bot'),
                        'sub_top': NamedButton(18, pull_up=False, hold_time=hold_time, dev_name='sub_top'),
                        'sub_run': NamedButton(21, pull_up=False, hold_time=hold_time, dev_name='sub_run'),
                        'target_run': NamedButton(20, pull_up=False, hold_time=hold_time, dev_name='target_run'),
                        'laser_run': NamedButton(19, pull_up=False, hold_time=hold_time, dev_name='laser_run')}

        self.high_pins = {'ard_rst': NamedOutputDevice(16, initial_value=True, dev_name='ard_rst'),
                          'top_hi': NamedOutputDevice(27, initial_value=True, dev_name='top_hi'),
                          'bot_hi': NamedOutputDevice(23, initial_value=True, dev_name='bot_hi')}

        self.gpio_handler = GPIOHandler(buttons=self.buttons, high_pins=self.high_pins,
                                        sig_print=False, parent=self)

        self.gpio_handler.sig_gpio_input.connect(self.gpio_act)

    def start_laser(self, num_pulses=None):
        self.laser.on()  # All cases need the laser in on mode.
        if num_pulses is None:
            self.laser_time_to_completion.emit(-9999)
        else:
            self.laser_time_to_completion.emit(ceil(self.laser_start_delay_msec/1000 + num_pulses / self.laser.reprate))
        if self.laser.trigger_src == 'INT':
            if num_pulses is None:
                pass
            elif isinstance(num_pulses, int):
                time = float(num_pulses / self.laser.reprate)
                warn("The number of pulses parameter can only be used accurately with an external trigger, internal "
                     "triggering of the laser will continue for {time} seconds then cease.".format(time=time))
                QTimer.singleShot(self.laser_start_delay_msec - 500 + time * 1000, self.laser_finished.emit)
            else:
                raise TypeError("Num pulses was not an integer, partial pulses are not possible.")
        elif self.laser.trigger_src == 'EXT':
            # Turn the laser on so that it can be ready for when pulses start
            # Set the reprate on the arduino first so that we don't have any issues with that.
            self.arduino.update_laser_param('reprate', self.laser.reprate)
            if num_pulses is None:
                self.arduino.update_laser_param('start')
            elif isinstance(num_pulses, int):
                # Start the laser after 3 seconds of warmup
                QTimer.singleShot(self.laser_start_delay_msec,
                                  lambda: self.arduino.update_laser_param('goal', num_pulses))
                QTimer.singleShot(self.laser_start_delay_msec,
                                  lambda: print("laser pulsing started"))
                # Start a timer that will kick off looking for the laser to go dormant
                self.timer_check_laser_finished.start(self.laser_start_delay_msec + 500)
            else:
                raise TypeError("Num pulses was not an integer, partial pulses are not possible.")

    def check_laser_finished(self):
        if self.buttons['laser_run'].is_active and self.timer_check_laser_finished.interval() > 1000:
            self.timer_check_laser_finished.setInterval(200)
        elif self.buttons['laser_run'].is_active:
            pass
        elif not self.buttons['laser_run'].is_active:
            print("Laser activity finished, emitting signal")
            self.laser_finished.emit()
            self.timer_check_laser_finished.stop()

    def stop_laser(self):
        # Stop the laser from generating or accepting trigger pulses.
        self.laser.off()
        if self.laser.trigger_src == 'EXT':
            self.arduino.halt_laser()

    def set_reprate(self, reprate):
        self.laser.set_reprate(reprate)
        self.arduino.update_laser_param('reprate', reprate)

    # def set_energy(self, ):

    def substrate_limit(self, channel=None):
        # Halt the substrate if it is at the limit
        self.arduino.halt_motor('substrate')

    def home_sub(self):
        self.arduino.update_motor_param('substrate', 'start',
                                        Global.SUB_DOWN)  # Start moving the substrate down without a goal
        self.homing_sub = True

    def set_sub_home(self):
        # ToDo: connect this to the sub bot signal so that it runs when the bottom is hit
        # If the user was running the substrate home routine, set zero position and reset homing_sub flag
        self.substrate_limit()
        if self.homing_sub:
            self.arduino.update_motor_param('substrate', 'position', 0)
            sleep(Global.OP_DELAY)
            self.arduino.update_motor_param('substrate', 'goal', 40350)
            self.homing_sub = False
        # else warn that the substrate has bottomed out
        else:
            # ToDo: Find a way to constrain substrate to only positive values in arduino code?
            warn("Substrate has reached its lower limit and will not move further.")

    def move_sub_to(self, mm_tts: float):
        goal_position = (mm_tts - Global.SUB_D0) * Global.SUB_STEPS_PER_MM
        self.arduino.update_motor_param('substrate', 'goal', int(goal_position))

    def set_sub_speed(self, mm_spd: float):
        sub_spd = mm_spd * Global.SUB_STEPS_PER_MM
        self.arduino.update_motor_param('substrate', 'max speed', sub_spd)

    def set_sub_acceleration(self, mmpss: float):
        sub_acc = mmpss * Global.SUB_STEPS_PER_MM
        self.arduino.update_motor_param('substrate', 'acceleration', sub_acc)

    def set_carousel_home(self):
        home_carousel = HomeTargetCarouselDialog(self)
        home_carousel.exec_()
        if home_carousel == QDialog.accepted:
            self.arduino.update_motor_param('carousel', 'position', 0)
        elif home_carousel == QDialog.rejected:
            warn("User canceled target carousel homing process, previous home value is preserved.")

    def set_carousel_rps(self, rps_speed: float):
        carousel_spd = rps_speed * Global.CAROUSEL_STEPS_PER_REV
        self.arduino.update_motor_param('carousel', 'max speed', carousel_spd)

    def set_carousel_acceleration(self, rpss: float):
        carousel_acc = rpss * Global.CAROUSEL_STEPS_PER_REV
        self.arduino.update_motor_param('carousel', 'acceleration', carousel_acc)


    def move_to_target(self, target_num: int):
        """
        Moves to the target indicated by target_num. Target numbers are zero indexed and can be kept track of
        of in the upper level GUI
        """
        goal = (target_num % 6) * (Global.CAROUSEL_STEPS_PER_REV/6)
        self.arduino.update_motor_param('carousel', 'goal', goal)

    def current_target(self):
        # This calculates the current position as a fraction of the total rotation, then multiplies by the number of
        #  of steps and rounds to get to an integer target positon, finally takes the modulus by the number of positions
        #  to account for the circle (position 6 = position 0)
        # print(self.arduino.query_motor_parameters('carousel', 'position'))
        current_pos = int(self.arduino.query_motor_parameters('carousel', 'position'))
        return int(np.around(((current_pos % Global.CAROUSEL_STEPS_PER_REV) / Global.CAROUSEL_STEPS_PER_REV) * 6) % 6)

    def raster_target(self):
        # ToDo: implement this and test the arduino code attached to it.
        pass

    def set_target_carousel_speed(self, dps: float):
        # ToDo: move these hardcoded values somewhere else so they are easier to change
        speed = (Global.CAROUSEL_STEPS_PER_REV) * (dps / 360)  # (steps per rev) * (degrees per second / degrees per rev)
        # Naming convention in arduino stepper library uses max speed as target speed and "speed" as instantaneous speed
        self.arduino.update_motor_param('carousel', 'max speed', speed)

    def is_sub_running(self):
        return self.buttons['sub_run'].is_active

    def is_carousel_running(self):
        return self.buttons['target_run'].is_active

    def is_laser_running(self):
        return self.buttons['laser_run'].is_active

    def is_idle(self):
        return not (self.is_carousel_running() or self.is_laser_running() or self.is_sub_running())

    @pyqtSlot(str)
    def gpio_act(self, channel):
        # {'sub_bot': 22,
        #  'sub_top': 18,
        #  'sub_run': 21,
        #  'target_run': 20,
        #  'laser_run': 19}
        if channel == 'GPIO22':
            self.set_sub_home()
        elif channel == 'GPIO18':
            self.substrate_limit()
            warn("Substrate has reached upper limit, make sure your entered position is within bounds "
                 "and that the substrate is homed correctly.")
        print("GPIO Signal Emitted and acted on from channel {}".format(channel))

    # ToDo: write out motor positions and status on delete so that they can be restored
    #  on program boot


class GPIOHandler(QObject):
    # Place signals for each pin here
    sig_gpio_input = pyqtSignal(str)

    def __init__(self, buttons: dict, high_pins=None, low_pins=None, sig_print=False, parent=None):
        super().__init__()
        # Set a class variable to decide if signals will have print messages on emit
        self.sig_print = sig_print
        self.parent = parent

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
            self.sig_gpio_input.emit(str(device.pin))
        else:
            print("GPIO callback activated from channel {}, which is not in the list of input pins".format(device.pin))

    def add_gpio(self, channel: int, name: str, function, pull_up_down=None, initial=None):
        # Needs to be rewritten to use gpiozero
        pass


class HomeTargetCarouselDialog(QDialog):
    def __init__(self, brain: RPiHardware):
        super().__init__()
        self.brain = brain
        self.setWindowTitle('Home Target Carousel')

        self.moving_right = False
        self.moving_left = False
        # Store the old speed and then set speed to a lower value so the
        # position is easier to control by hand.
        self.stored_speed = brain.arduino.query_motor_parameters('carousel', 'speed')
        self.brain.arduino.update_motor_param('carousel', 'speed', Global.CAROUSEL_MANUAL_SPEED)

        self.right_btn = QPushButton()
        self.right_btn.setAutoRepeat(True)
        self.right_btn.setAutoRepeatInterval(Global.CAROUSEL_STEPS_PER_REV / Global.CAROUSEL_MANUAL_SPEED)
        self.right_btn.setAutoRepeatDelay(Global.AUTO_REPEAT_DELAY)

        self.left_btn = QPushButton()
        self.left_btn.setAutoRepeat(True)
        self.left_btn.setAutoRepeatInterval(Global.CAROUSEL_STEPS_PER_REV / Global.CAROUSEL_MANUAL_SPEED)
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
        self.brain.arduino.update_motor_param('carousel', 'start', Global.CAROUSEL_CW)
        self.moving_right = True
        self.moving_left = False

    def left(self):
        self.brain.arduino.update_motor_param('carousel', 'start', Global.CAROUSEL_CCW)
        self.moving_left = True
        self.moving_right = False

    def halt(self):
        self.brain.arduino.halt_motor('carousel')
        self.moving_right = False
        self.moving_left = False

    # Override the accept and reject methods to reset speed after homing/cancelling
    def accept(self):
        self.brain.arduino.update_motor_param('carousel', 'speed', self.stored_speed)
        self.brain.arduino.update_motor_param('carousel', 'position', 0)
        super().accept()

    def reject(self):
        self.brain.arduino.update_motor_param('carousel', 'speed', self.stored_speed)
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
