# Imports
import Adafruit_BBIO.GPIO as GPIO
from PyQt5.QtCore import Qt, QObject, QTimer
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, QMessageBox, QDialog, QPushButton, QShortcut,
                             QSpacerItem, QWidget)
from time import sleep
from pathlib import Path


class BeagleBoneHardware(QWidget):

    def __init__(self):
        # Fixme: need to evaluate if using self.parent() returns a widget for this object for use in
        #  calling popups
        super().__init__()

        self.allow_trigger = True  # Set this to false to stop triggering the laser
        self.triggers_sent = 0  # Will record the number of trigger pulses sent before pulsing was discontinued
        self.pulse_count_target = None
        self.trigger_timer = QTimer()
        self.trigger_timer.timeout.connect(self.trigger_pulse)
        self.sub_step_timer = QTimer()
        self.sub_step_timer.timeout.connect(self.step_sub)
        self.target_step_timer = QTimer()
        self.target_step_timer.timeout.connect(self.step_target)
        self.home_target_dialog = HomeTargetsDialog(self)

        # Define limits for substrate motion
        # FIXME: All limit values are guesses and need to be set.
        self.sub_bottom = 0
        self.sub_top = 24000
        self.sub_position = 24000
        self.sub_goal = None
        self.sub_dir = 'up'

        self.current_target = 1
        self.target_goal = None
        self.target_position = 0
        self.target_pos_goal = None
        self.target_dir = 'ccw'

        # Define class variables for
        # FIXME: Determine/setup pin designations
        self.out_pins = {"trigger": "P8_17", "sub_dir": "P9_19",
                         "sub_step": "P9_17", "target_dir": "P9_25",
                         "target_step": "P9_23"}
        self.in_pins = {"sub_home": "P8_9"}
        self.hi_pins = {"sub_home": "P8_10"}

        self.setup_pins()

    def setup_pins(self):
        # Set up pins (all output pins default to low (0))
        for key in self.out_pins:
            GPIO.setup(self.out_pins[key], GPIO.OUT)
            GPIO.output(self.out_pins[key], GPIO.LOW)

        for key in self.in_pins:
            GPIO.setup(self.in_pins[key], GPIO.IN)

        for key in self.hi_pins:
            GPIO.setup(self.hi_pins[key], GPIO.OUT)
            GPIO.output(self.hi_pins[key], GPIO.HIGH)

    def start_pulsing(self, reprate, pulse_count=None):
        # Reset allow_trigger so that we don't end up breaking things/needing to restart the GUI on deposition cancel.
        print('Starting pulsing')
        rep_time = int(1000 / int(reprate))
        self.trigger_timer.start(rep_time)
        print('Started Timer with timeout of {}'.format(rep_time))
        self.pulse_count_target = pulse_count

    def stop_pulsing(self):
        self.trigger_timer.stop()
        print('Stop signal sent to timer')

    def trigger_pulse(self):
        if self.allow_trigger:
            print('Pulse {} was sent'.format(self.triggers_sent))
            GPIO.output(self.out_pins["trigger"], GPIO.HIGH)
            sleep(0.000015)
            GPIO.output(self.out_pins["trigger"], GPIO.LOW)
            self.triggers_sent += 1

        if self.pulse_count_target is not None:
            print('Checking Pulse ({}) vs triggers sent ({})'.format(self.triggers_sent, self.pulse_count_target))
            if self.triggers_sent <= self.pulse_count_target:
                self.allow_trigger = False
                self.trigger_timer.stop()
                print('Stop signal sent. (Number of triggers ({}) >= target pulse count ({})'.format(self.triggers_sent,
                                                                                                     self.pulse_count_target))

    def reset_trigger(self):
        print('Initiating trigger reset. Triggers sent: {}, Allow Trigger: {}'.format(self.triggers_sent,
                                                                                      self.allow_trigger))
        self.allow_trigger = True
        self.triggers_sent = 0
        print('Triggering reset. Triggers sent: {}, Allow Trigger: {}'.format(self.triggers_sent, self.allow_trigger))

    def home_sub(self):
        self.sub_goal = 'home'

        if not GPIO.input(self.in_pins['sub_home']):
            self.set_sub_dir('up')
            # FIXME: this delay sets the speed of the substrate movement, fine tune speed
            if not self.sub_step_timer.isActive():
                self.start_sub()
        if GPIO.input(self.in_pins['sub_home']):
            self.sub_goal = 0
            self.sub_position = 0

    def move_sub_to(self, position):
        self.sub_goal = position

        if self.sub_goal > self.sub_position:
            self.set_sub_dir('up')
        elif self.sub_goal < self.sub_position:
            self.set_sub_dir('down')

        # FIXME: this delay sets the speed of the substrate movement, fine tune speed
        self.start_sub()

    def step_sub(self):
        def step_pulse():
            if self.get_sub_dir() == 'up':
                self.sub_position -= 1
            elif self.get_sub_dir() == 'down':
                self.sub_position += 1

            GPIO.output(self.out_pins['sub_step'], GPIO.HIGH)
            sleep(0.000001)
            GPIO.output(self.out_pins['sub_step'], GPIO.LOW)

        if self.sub_goal is None:
            if not GPIO.input(self.in_pins['sub_home']) or self.sub_position > 0:
                step_pulse()
            elif self.sub_position == 0 or GPIO.input(self.in_pins['sub_home']):
                # If the substrate is at end of range warn user and offer to rehome stage if there are issues.
                max_range = QMessageBox.question(QWidget, 'Substrate End of Range',
                                                 'Press ok to continue or press reset to home the substrate',
                                                 QMessageBox.Ok | QMessageBox.Reset,
                                                 QMessageBox.Ok)
                if max_range == QMessageBox.Ok:
                    pass
                elif max_range == QMessageBox.Reset:
                    self.home_sub()
        elif self.sub_goal is not None:
            if self.sub_goal != self.sub_position or self.sub_goal == 'home':
                step_pulse()
                if self.sub_goal == 'home':
                    self.home_sub()
            elif self.sub_goal == self.sub_position:
                # Clear the goal position if the substrate is in that position
                self.sub_goal = None
                self.sub_step_timer.stop()

    def set_sub_dir(self, direction):
        if direction.lower() == "up":
            # Set direction pin so that the substrate will be driven up (CCW)
            # FIXME: Don't know which direction is which
            self.sub_dir = 'up'
            GPIO.output(self.out_pins['sub_dir'], GPIO.LOW)
        elif direction.lower() == "down":
            # Set direction pin so that the substrate will be driven down (CW)
            self.sub_dir = 'down'
            GPIO.output(self.out_pins['sub_dir'], GPIO.HIGH)
        else:
            print('Invalid direction argument for the substrate motor supplied.')

    def get_sub_dir(self):
        return self.sub_dir

    def stop_sub(self):
        self.sub_step_timer.stop()

    def start_sub(self):
        self.sub_step_timer.start(1)

    def home_targets(self):
        self.home_target_dialog.exec_()

        print(self.home_target_dialog, ',', type(self.home_target_dialog))
        if self.home_target_dialog == QDialog.Accepted:
            self.target_position = 0
            self.current_target = 1
            target_home_info = QMessageBox.information(self, 'Home Set',
                                                       'New target carousel home position set',
                                                       QMessageBox.Ok, QMessageBox.Ok)
        elif self.home_target_dialog == QDialog.Rejected:
            target_home_info = QMessageBox.warning(self, 'Home Canceled',
                                                   'Target carousel home cancelled by user.',
                                                   QMessageBox.Ok, QMessageBox.Ok)

    def move_to_target(self, target_goal):
        self.target_goal = target_goal

        if self.target_goal != self.current_target:
            delta_pos = abs(target_goal - self.current_target)

            if delta_pos > 3:
                delta_pos = ((delta_pos - 3) * 2) - delta_pos

            if delta_pos < 0:
                self.set_target_dir('cw')
            elif delta_pos > 0:
                self.set_target_dir('ccw')
            else:
                print('Target already in position {}'.format(self.target_goal))
                return

            # FIXME: Timing and movement speed yada yada
            self.start_target()

    def step_target(self):
        def step_pulse():
            if self.get_target_dir() == 'cw':
                self.target_position += 1
            elif self.get_target_dir() == 'ccw':
                self.target_position -= 1

            self.target_position = self.target_position % 6000
            GPIO.output(self.out_pins['target_step'], GPIO.HIGH)
            sleep(0.000001)
            GPIO.output(self.out_pins['target_step'], GPIO.LOW)

        if self.target_goal is None and self.target_pos_goal is None:
            step_pulse()
        elif self.target_goal is not None:  # If there is a goal target
            # Set the target position goal if that has not already been done
            if self.target_pos_goal is None:
                self.target_pos_goal = 1000 * self.target_goal

            if self.target_position != self.target_pos_goal:
                step_pulse()
                # FIXME: Come up with logic so that the targets rotate the CW or CCW
                #  direction to minimize positioning time: WAIT DID I Already do that in the move to?
            elif self.target_position == self.target_pos_goal:
                self.target_pos_goal = None
                self.target_goal = None
                self.target_step_timer.stop()

    def set_target_dir(self, direction):
        if direction.lower() == "ccw":
            # Set direction pin so that the substrate will be driven up (CCW)
            # FIXME: Don't know which direction is which
            self.target_dir = 'ccw'
            GPIO.output(self.out_pins['target_dir'], GPIO.LOW)
        elif direction.lower() == "cw":
            # Set direction pin so that the substrate will be driven down (CW)
            self.target_dir = 'cw'
            GPIO.output(self.out_pins['target_dir'], GPIO.HIGH)
        else:
            print('Invalid direction argument for the target motor supplied')

    def get_target_dir(self):
        return self.target_dir

    def start_target(self):
        self.target_step_timer.start(1)

    def stop_target(self):
        self.target_step_timer.stop()

    def __del__(self):
        GPIO.cleanup()


class HomeTargetsDialog(QDialog):
    def __init__(self, brain: BeagleBoneHardware):
        super().__init__()

        self.brain = brain
        self.setWindowTitle('Home Target Carousel')

        self.right_btn = QPushButton()
        self.right_btn.setAutoRepeat(True)
        self.right_btn.setAutoRepeatInterval(10)
        self.right_btn.setAutoRepeatDelay(200)

        self.left_btn = QPushButton()
        self.left_btn.setAutoRepeat(True)
        self.left_btn.setAutoRepeatInterval(10)
        self.left_btn.setAutoRepeatDelay(200)

        self.left_icon = QIcon()
        self.right_icon = QIcon()
        right_btn_path = Path('src/img').absolute() / 'right_btn.svg'
        left_btn_path = Path('src/img').absolute() / 'left_btn.svg'
        self.right_icon.addFile(str(right_btn_path))
        self.left_icon.addFile(str(left_btn_path))
        self.right_btn.setIcon(self.right_icon)
        self.left_btn.setIcon(self.left_icon)

        self.apply_btn = QPushButton("Apply")
        self.cancel_btn = QPushButton("Cancel")

        self.left_sc = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.right_sc = QShortcut(QKeySequence(Qt.Key_Right), self)

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
        self.right_btn.clicked.connect(self.right)
        self.left_btn.clicked.connect(self.left)
        self.left_sc.activated.connect(self.left)
        self.right_sc.activated.connect(self.right)
        self.apply_btn.clicked.connect(self.apply_home)
        self.cancel_btn.clicked.connect(self.cancel_home)

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
        if self.brain.get_target_dir() != 'cw':
            self.brain.set_target_dir('cw')
        self.brain.step_target()

    def left(self):
        if self.brain.get_target_dir() != 'ccw':
            self.brain.set_target_dir('ccw')
        self.brain.step_target()

    def apply_home(self):
        self.accept()

    def cancel_home(self):
        self.reject()
