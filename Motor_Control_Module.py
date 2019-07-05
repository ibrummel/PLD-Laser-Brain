from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QWidget, QGroupBox, QGridLayout, QSlider)


class MotorControlPanel(QWidget):
    def __init__(self):
        super(MotorControlPanel, self).__init__()

        self.target_pos_val = 200
        self.pos1_btn = QPushButton('1')
        self.pos2_btn = QPushButton('2')
        self.pos3_btn = QPushButton('3')
        self.pos4_btn = QPushButton('4')
        self.pos5_btn = QPushButton('5')
        self.pos6_btn = QPushButton('6')
        self.raster_check = QCheckBox()
        self.raster_label = QLabel('Raster target?')

        self.tts_label = QLabel('Current TTS:')
        self.tts_line = QLineEdit()
        self.tts_line.setPlaceholderText('Go to TTS')

        self.sub_pos_val = 5000
        self.sub_mv_label = QLabel('Move\nSubstrate:')
        self.up_sub_btn = QPushButton()
        self.up_sub_btn.setAutoRepeat(True)
        self.up_sub_btn.setAutoRepeatInterval(150)
        self.up_sub_btn.setAutoRepeatDelay(500)
        self.down_sub_btn = QPushButton()
        self.down_sub_btn.setAutoRepeat(True)
        self.down_sub_btn.setAutoRepeatInterval(150)
        self.down_sub_btn.setAutoRepeatDelay(500)
        self.up_icon = QIcon()
        self.down_icon = QIcon()
        self.up_icon.addFile('.\\src\\img\\up_btn.svg')
        self.down_icon.addFile('.\\src\\img\\down_btn.svg')
        self.up_sub_btn.setIcon(self.up_icon)
        self.down_sub_btn.setIcon(self.down_icon)

        self.speed_val = 5
        self.speed_label = QLabel('Up/Down Speed (mm/s):')
        self.speed_slide = QSlider(Qt.Horizontal)
        self.speed_slide.setMaximum(10)
        self.speed_slide.setMinimum(0.1)
        self.speed_slide.setTickPosition(QSlider.TicksBothSides)
        self.speed_slide.setTickInterval(1)
        self.speed_slide.setValue(self.speed_val)

        self.speed_line = QLineEdit(str(self.speed_val))
        self.pos_line = QLineEdit(str(self.target_pos_val) + ':' + str(self.sub_pos_val))

        self.target_group = QGroupBox("Target Position:")
        self.sub_group = QGroupBox("Substrate Position:")
        self.hbox = QHBoxLayout()
        self.connect_controls()
        self.init_layout()

    def connect_controls(self):
        self.up_sub_btn.clicked.connect(lambda: self.move_sub_up(1))
        self.down_sub_btn.clicked.connect(lambda: self.move_sub_down(1))

        self.pos1_btn.clicked.connect(lambda: self.set_target_pos(1))
        self.pos2_btn.clicked.connect(lambda: self.set_target_pos(2))
        self.pos3_btn.clicked.connect(lambda: self.set_target_pos(3))
        self.pos4_btn.clicked.connect(lambda: self.set_target_pos(4))
        self.pos5_btn.clicked.connect(lambda: self.set_target_pos(5))
        self.pos6_btn.clicked.connect(lambda: self.set_target_pos(6))
        self.raster_check.stateChanged.connect(self.raster_current_target)
        self.speed_slide.valueChanged.connect(self.update_speed_line)
        self.speed_line.returnPressed.connect(self.update_speed_slide)

    def init_layout(self):
        target_grid = QGridLayout()
        target_grid.addWidget(self.pos1_btn, 0, 0)
        target_grid.addWidget(self.pos2_btn, 0, 1)
        target_grid.addWidget(self.pos3_btn, 0, 2)
        target_grid.addWidget(self.pos4_btn, 1, 0)
        target_grid.addWidget(self.pos5_btn, 1, 1)
        target_grid.addWidget(self.pos6_btn, 1, 2)
        target_grid.addWidget(self.raster_label, 2, 0, 1, 2, Qt.AlignRight)
        target_grid.addWidget(self.raster_check, 2, 2)

        sub_grid = QGridLayout()
        sub_grid.addWidget(self.tts_label, 0, 0, 1, 2)
        sub_grid.addWidget(self.tts_line, 0, 2)
        sub_grid.addWidget(self.sub_mv_label, 1, 0)
        sub_grid.addWidget(self.speed_label, 1, 1, 1, 2)
        sub_grid.addWidget(self.up_sub_btn, 2, 0)
        sub_grid.addWidget(self.down_sub_btn, 3, 0)
        sub_grid.addWidget(self.speed_slide, 2, 1, 1, 2)
        sub_grid.addWidget(self.speed_line, 3, 1, 1, 2)

        self.target_group.setLayout(target_grid)
        self.sub_group.setLayout(sub_grid)

        self.hbox.addWidget(self.target_group)
        self.hbox.addWidget(self.sub_group)
        self.hbox.addWidget(self.pos_line) # Debug
        self.setLayout(self.hbox)

    def move_sub_up(self, pulses=1):
        for i in range(0, pulses):
            self.sub_pos_val += 1
            # self.brain.move_sub(self.sub_pos_val, self.get_speed_val())
        self.update_pos_line() # Debug

    def move_sub_down(self, pulses=1):
        for i in range(0, pulses):
            self.sub_pos_val -= 1
            # self.brain.move_sub(self.sub_pos_val, self.get_speed_val())
        self.update_pos_line()

    def get_speed_val(self):
        return self.speed_val

    def update_pos_line(self):
        self.pos_line.setText(str(self.target_pos_val) + ':' + str(self.sub_pos_val))

    def update_speed_line(self):
        self.speed_val = self.speed_slide.value()
        self.speed_line.setText(str(self.speed_val))

    def update_speed_slide(self):
        self.speed_val = float(self.speed_line.text())
        self.speed_slide.setValue(self.speed_val)

    def set_target_pos(self, position):
        self.target_pos_val = 100 * position  # FIXME: Fix these values
        # self.brain.move_to_target(position)
        self.update_pos_line()

    def raster_current_target(self):
        if self.raster_check.isChecked():
            # self.brain.raster_target(True, self.get_current_target())
            print('Raster On')
        else:
            # self.brain.raster_target(False, self.get_current_target())
            print('Raster Off')
        pass

    def get_current_target(self):
        return self.target_pos_val
