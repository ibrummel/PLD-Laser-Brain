from PyQt5.QtCore import Qt, QTimer, QObject
from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator, QIcon
from PyQt5.QtWidgets import (QSpacerItem, QCheckBox, QComboBox, QFileDialog,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
                             QWidget, QMessageBox, QFormLayout, QGroupBox,
                             QFrame, QMainWindow, QDockWidget, QSlider, QGridLayout)
import sys
import os
import pickle
from VISA_Communications import VisaLaser
import time
from math import trunc


class MotorControlPanel(QWidget):
    def __init__(self):
        super(MotorControlPanel, self).__init__()

        self.pos1_btn = QPushButton('1')
        self.pos2_btn = QPushButton('2')
        self.pos3_btn = QPushButton('3')
        self.pos4_btn = QPushButton('4')
        self.pos5_btn = QPushButton('5')
        self.pos6_btn = QPushButton('6')
        self.raster_check = QCheckBox()
        self.raster_label = QLabel('Raster?')

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
        self.speed_slide = QSlider(Qt.Vertical)
        self.speed_slide.setMaximum(10)
        self.speed_slide.setMinimum(0.1)
        self.speed_slide.setTickPosition(QSlider.TicksRight)
        self.speed_slide.setTickInterval(1)
        self.speed_slide.setValue(self.speed_val)

        self.speed_line = QLineEdit(str(self.speed_val))

        self.target_group = QGroupBox("Target Position:")
        self.sub_group = QGroupBox("Substrate Position:")
        self.hbox = QHBoxLayout
        self.init_connect_controls()
        self.init_layout()

    def init_connect_controls(self):
        self.up_sub_btn.clicked.connect(self.move_sub_up)
        self.down_sub_btn.clicked.connect(self.move_sub_down)
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
        target_grid.addWidget(self.raster_label, 2, 0, 1, 2)
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

        self.setLayout(self.hbox)

    def move_sub_up(self):
        pass

    def move_sub_down(self):
        pass

    def update_speed_line(self):
        pass

    def update_speed_slide(self):
        pass

