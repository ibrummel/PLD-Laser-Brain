# Imports
import RPi.GPIO as GPIO
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, pyqtSlot
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
        self.in_pins = {"sub_bot": 22, "sub_top": 23, 'sub_run': 21, 'target_run': 20, 'laser_run': 19}
        self.high_pins = {'ard_rst': 16}
        
        self.setup_pins()
        
    def setup_pins(self):
        

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