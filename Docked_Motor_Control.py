from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QWidget, QGroupBox, QGridLayout, QSlider, QApplication, QFormLayout, QVBoxLayout,
                             QToolButton, QShortcut)
from pathlib import Path
from RPi_Hardware import RPiHardware
import sys
import Global_Values as Global


class MotorControlPanel(QWidget):
    def __init__(self, brain: RPiHardware):
        super(MotorControlPanel, self).__init__()

        # Declare brain as RPi interface object
        self.brain = brain

        # Retrieve settings from XML

        self.target_pos_val = 200
        self.pos1_btn = QPushButton('1')
        self.pos2_btn = QPushButton('2')
        self.pos3_btn = QPushButton('3')
        self.pos4_btn = QPushButton('4')
        self.pos5_btn = QPushButton('5')
        self.pos6_btn = QPushButton('6')
        self.raster_check = QCheckBox()
        self.raster_label = QLabel('Raster target?')

        self.right_btn = QPushButton()
        self.right_btn.setAutoRepeat(False)
        self.left_btn = QPushButton()
        self.left_btn.setAutoRepeat(False)

        left_icon = QIcon()
        right_icon = QIcon()
        right_btn_path = Path('src/img').absolute() / 'right.svg'
        left_btn_path = Path('src/img').absolute() / 'left.svg'
        right_icon.addFile(str(right_btn_path))
        left_icon.addFile(str(left_btn_path))
        self.right_btn.setIcon(right_icon)
        self.left_btn.setIcon(left_icon)

        self.left_sc = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.right_sc = QShortcut(QKeySequence(Qt.Key_Right), self)

        self.tts_label = QLabel('Current TTS:')
        self.tts_line = QLineEdit()
        self.tts_line.setPlaceholderText('Go to TTS')

        self.sub_pos_val = self.brain.arduino.query_motor_parameters('sub', 'position')
        self.sub_mv_label = QLabel('Move\nSubstrate:')
        self.up_sub_btn = QPushButton()
        self.up_sub_btn.setAutoRepeat(True)
        self.up_sub_btn.setAutoRepeatInterval(Global.SUB_STEPS_PER_REV / Global.SUB_MANUAL_SPEED)
        self.up_sub_btn.setAutoRepeatDelay(Global.AUTO_REPEAT_DELAY)
        self.down_sub_btn = QPushButton()
        self.down_sub_btn.setAutoRepeat(True)
        self.down_sub_btn.setAutoRepeatInterval(Global.SUB_STEPS_PER_REV / Global.SUB_MANUAL_SPEED)
        self.down_sub_btn.setAutoRepeatDelay(Global.AUTO_REPEAT_DELAY)
        up_icon = QIcon()
        down_icon = QIcon()
        up_btn_path = Path('src/img').absolute() / 'up.svg'
        down_btn_path = Path('src/img').absolute() / 'down.svg'
        up_icon.addFile(str(up_btn_path))
        down_icon.addFile(str(down_btn_path))
        self.up_sub_btn.setIcon(up_icon)
        self.down_sub_btn.setIcon(down_icon)
        self.up_sc1 = QShortcut(QKeySequence(Qt.Key_Up), self)
        self.down_sc1 = QShortcut(QKeySequence(Qt.Key_Plus), self)
        self.up_sc2 = QShortcut(QKeySequence(Qt.Key_Down), self)
        self.down_sc2 = QShortcut(QKeySequence(Qt.Key_Minus), self)

        # ToDo: Determine how rps translates to mm in z per sec
        self.mm_speed_val = 0.5
        self.speed_label = QLabel('Up/Down Speed (mm/s):')
        self.speed_slide = QSlider(Qt.Horizontal)
        self.speed_slide.setMaximum(20)
        self.speed_slide.setMinimum(1)
        self.speed_slide.setTickPosition(QSlider.TicksBothSides)
        self.speed_slide.setTickInterval(1)
        self.speed_slide.setValue(int(self.mm_speed_val * 10))
        self.speed_line = QLineEdit(str(self.mm_speed_val))

        self.home_sub_btn = QToolButton()
        self.home_sub_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        home_icon = QIcon()
        home_icon.addFile(str(Path('src/img').absolute() / 'home.svg'))
        self.home_sub_btn.setIcon(home_icon)
        self.home_sub_btn.setText("Substrate")
        self.home_sub_btn.setMinimumSize(64, 48)
        self.home_target_btn = QToolButton()
        self.home_target_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        home_icon = QIcon()
        home_icon.addFile(str(Path('src/img').absolute() / 'home.svg'))
        self.home_target_btn.setIcon(home_icon)
        self.home_target_btn.setText("Targets")
        self.home_target_btn.setMinimumSize(64, 48)

        self.target_group = QGroupBox("Target Position:")
        self.target_group.setMinimumSize(271, 155)
        self.sub_group = QGroupBox("Substrate Position:")
        self.sub_group.setMinimumSize(271, 155)
        self.home_group = QGroupBox('Home Axes:')
        self.home_group.setMinimumSize(85, 155)
        self.hbox = QHBoxLayout()

        self.init_connections()
        self.init_layout()

    def init_connections(self):
        self.up_sub_btn.pressed.connect(self.sub_up)
        self.up_sub_btn.released.connect(self.sub_halt)
        self.down_sub_btn.pressed.connect(self.sub_down)
        self.down_sub_btn.released.connect(self.sub_halt)
        # ToDo: address these shortcuts. Need to differentiate between keypress and key release here
        self.up_sc1.activated.connect(self.sub_up)
        self.down_sc1.activated.connect(self.sub_down)
        self.up_sc2.activated.connect(self.sub_up)
        self.down_sc2.activated.connect(self.sub_down)
        # ToDo: This seems clunky and should be changed, maybe just a label denoting current target and arrows?
        self.pos1_btn.clicked.connect(lambda: self.brain.move_to_target(1))
        self.pos2_btn.clicked.connect(lambda: self.brain.move_to_target(2))
        self.pos3_btn.clicked.connect(lambda: self.brain.move_to_target(3))
        self.pos4_btn.clicked.connect(lambda: self.brain.move_to_target(4))
        self.pos5_btn.clicked.connect(lambda: self.brain.move_to_target(5))
        self.pos6_btn.clicked.connect(lambda: self.brain.move_to_target(6))
        self.left_btn.clicked.connect(self.target_left)
        self.right_btn.clicked.connect(self.target_right)
        self.left_sc.activated.connect(self.target_left)
        self.right_sc.activated.connect(self.target_right)
        # FIXME: Probably don't want this implementation of raster?
        self.raster_check.stateChanged.connect(self.raster_current_target)
        self.brain.target_changed.connect(lambda: self.raster_check.setChecked(False))  # ToDo: Changes raster to match new target
        self.speed_slide.valueChanged.connect(self.update_speed_line)
        self.speed_line.returnPressed.connect(self.update_speed_slide)
        self.home_target_btn.clicked.connect(self.brain.home_targets)
        self.home_sub_btn.clicked.connect(self.brain.home_sub)

    def init_layout(self):
        raster_form = QFormLayout()
        raster_form.addRow(self.raster_label, self.raster_check)

        target_grid = QGridLayout()
        target_grid.addWidget(self.left_btn, 0, 0)
        target_grid.addWidget(self.right_btn, 0, 1)
        target_grid.addLayout(raster_form, 0, 2)
        target_grid.addWidget(self.pos1_btn, 1, 0)
        target_grid.addWidget(self.pos2_btn, 1, 1)
        target_grid.addWidget(self.pos3_btn, 1, 2)
        target_grid.addWidget(self.pos4_btn, 2, 0)
        target_grid.addWidget(self.pos5_btn, 2, 1)
        target_grid.addWidget(self.pos6_btn, 2, 2)

        sub_grid = QGridLayout()
        sub_grid.addWidget(self.tts_label, 0, 0, 1, 2)
        sub_grid.addWidget(self.tts_line, 0, 2)
        sub_grid.addWidget(self.sub_mv_label, 1, 0)
        sub_grid.addWidget(self.speed_label, 1, 1, 1, 2)
        sub_grid.addWidget(self.up_sub_btn, 2, 0)
        sub_grid.addWidget(self.down_sub_btn, 3, 0)
        sub_grid.addWidget(self.speed_slide, 2, 1, 1, 2)
        sub_grid.addWidget(self.speed_line, 3, 1, 1, 2)

        home_vbox = QVBoxLayout()
        home_vbox.addWidget(self.home_target_btn)
        home_vbox.addWidget(self.home_sub_btn)

        self.target_group.setLayout(target_grid)
        self.sub_group.setLayout(sub_grid)
        self.home_group.setLayout(home_vbox)

        self.hbox.addWidget(self.target_group)
        self.hbox.addWidget(self.sub_group)
        self.hbox.addWidget(self.home_group)
        self.setLayout(self.hbox)

    def parse_xml_settings(self):
        # ToDo: Read an XML file to determine target types/compositons/sizes
        pass

    def write_xml_settings(self):
        # ToDo: dump all settings to a file. Should be edited in memory using ElementTree
        pass

    def sub_up(self):
        self.brain.arduino.update_motor_param('sub', 'start', Global.SUB_UP)

    def sub_down(self):
        self.brain.arduino.update_motor_param('sub', 'start', Global.SUB_DOWN)

    def sub_halt(self):
        self.brain.arduino.halt_motor('sub')

    def target_right(self):
        self.brain.move_to_target((self.brain.current_target + 1) % 6)

    def target_left(self):
        self.brain.move_to_target((self.brain.current_target - 1) % 6)

    def get_speed_val(self):
        return self.mm_speed_val

    def update_speed_line(self):
        self.mm_speed_val = float(self.speed_slide.value() / 10)
        self.speed_line.setText(str(self.mm_speed_val))
        self.set_sub_speed()

    def update_speed_slide(self):
        self.mm_speed_val = float(self.speed_line.text())
        self.speed_slide.setValue(self.mm_speed_val * 10)
        self.set_sub_speed()

    def set_sub_speed(self):
        # ToDo: convert this to be a mm/s value rather than an rps value
        self.brain.arduino.update_laser_param('sub', 'speed', self.mm_speed_val)

    def raster_current_target(self):
        if self.raster_check.isChecked():
            # ToDo: Need to set up an XML to store settings, positions, and target sizes.
            target_size = self.parent.settings['carousel'][self.brain.current_target]['size']
            self.brain.arduino.update_motor_param('target', 'raster', target_size)
        else:
            # self.brain.raster_target(False, self.get_current_target())
            print('Raster Off')
        pass

def main():
    app = QApplication(sys.argv)

    ex = MotorControlPanel()
    ex.show()

    sys.exit(app.exec_())


# =============================================================================
# Start the GUI (set up for testing for now)
# FIXME: Need to finalize main loop for proper operation
# =============================================================================
if __name__ == '__main__':
    main()
