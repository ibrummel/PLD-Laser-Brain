from PyQt5.QtCore import Qt, QRegExp, QEvent
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QCheckBox, QLabel, QLineEdit, QPushButton,
                             QWidget, QSlider, QShortcut, QDockWidget)
from RPi_Hardware import RPiHardware
from PyQt5 import uic
import Global_Values as Global


class MotorControlPanel(QDockWidget):
    def __init__(self, brain: RPiHardware):
        super(MotorControlPanel, self).__init__()

        # Declare brain as RPi interface object
        self.brain = brain

        # Load the ui file and discover all necessary items
        uic.loadUi('./src/ui/docked_motor_control.ui', self)

        self.btns = {widget.objectName().split('btn_')[1]: widget
                     for widget in self.findChildren(QPushButton, QRegExp('btn_*'))}
        self.lines = {widget.objectName().split('line_')[1]: widget
                      for widget in self.findChildren(QLineEdit, QRegExp('line_*'))}
        self.labels = {widget.objectName().split('lbl_')[1]: widget
                       for widget in self.findChildren(QLabel, QRegExp('lbl_*'))}
        self.checks = {widget.objectName().split('check_')[1]: widget
                       for widget in self.findChildren(QCheckBox, QRegExp('check_*'))}
        self.sliders = {widget.objectName().split('slide_')[1]: widget
                        for widget in self.findChildren(QSlider, QRegExp('slide_*'))}

        self.sc_left = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.sc_right = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.installEventFilter(self)
        self.hotkey_disable = False

        # Retrieve settings from XML
        self.target_pos_val = 200
        self.sub_pos_val = self.brain.arduino.query_motor_parameters('sub', 'position')
        # ToDo: Determine how rps translates to mm in z per sec
        self.mm_speed_val = 0.5

        self.init_connections()
        self.init_fields()

    def init_connections(self):
        self.btns['sub_up'].pressed.connect(self.sub_up)
        self.btns['sub_up'].released.connect(self.sub_halt)
        self.btns['sub_down'].pressed.connect(self.sub_down)
        self.btns['sub_down'].released.connect(self.sub_halt)
        self.btns['carousel_next'].clicked.connect(self.target_left)
        self.btns['carousel_prev'].clicked.connect(self.target_right)
        self.lines['current_target'].returnPressed.connect(self.move_to_target)
        self.sc_left.activated.connect(self.target_left)
        self.sc_right.activated.connect(self.target_right)
        # FIXME: Probably don't want this implementation of raster?
        self.checks['raster'].stateChanged.connect(self.raster_current_target)
        self.brain.target_changed.connect(lambda: self.check_raster.setChecked(False))
        self.sliders['sub_speed'].valueChanged.connect(self.update_speed_line)
        self.lines['sub_speed'].returnPressed.connect(self.update_speed_slide)
        self.btns['carousel_home'].clicked.connect(self.brain.home_target_carousel)
        self.btns['sub_home'].clicked.connect(self.brain.home_sub)

    def init_fields(self):
        self.lines['current_target'].setText(str(self.brain.current_target()))
        # ToDo: change this to report real units from target to substrate.
        self.lines['sub_position'].setText(str(self.brain.arduino.query_motor_parameters('substrate', 'position')))
        self.lines['sub_speed'].setText(str(self.brain.arduino.query_motor_parameters('substrate', 'max speed')))

    def toggle_hotkeys(self):
        # Toggle the hotkey disable boolean
        self.hotkey_disable = not self.hotkey_disable

        # Act on hotkey_disable
        self.sc_left.blockSignals(self.hotkey_disable)
        self.sc_right.blockSignals(self.hotkey_disable)

        if self.hotkey_disable:
            self.installEventFilter(self)
        elif not self.hotkey_disable:
            self.removeEventFilter(self)

    def sub_up(self):
        self.brain.arduino.update_motor_param('sub', 'start', Global.SUB_UP)

    def sub_down(self):
        self.brain.arduino.update_motor_param('sub', 'start', Global.SUB_DOWN)

    def sub_halt(self):
        self.brain.arduino.halt_motor('sub')

    def target_right(self):
        goal = (self.brain.current_target() + 1) % 6
        print("Moving to target {}".format(goal))
        self.brain.move_to_target(goal)
        self.lines['current_target'].setText(str(goal))

    def target_left(self):

        goal = (self.brain.current_target() - 1) % 6
        print("Moving to target {}".format(goal))
        self.brain.move_to_target(goal)
        self.lines['current_target'].setText(str(goal))

    def move_to_target(self):
        goal = int(self.lines['current_target'].text())
        print('Moving to target {}'.format(goal))
        self.brain.move_to_target(goal)

    def update_speed_line(self):
        self.mm_speed_val = float(self.sliders['sub_speed'].value() / 10)
        self.lines['sub_speed'].setText(str(self.mm_speed_val))
        self.set_sub_speed()

    def update_speed_slide(self):
        self.mm_speed_val = float(self.lines['sub_speed'].text())
        self.sliders['sub_speed'].setValue(int(self.mm_speed_val * 10))
        self.set_sub_speed()

    def set_sub_speed(self):
        # ToDo: convert this to be a mm/s value rather than an rps value
        self.brain.arduino.update_laser_param('sub', 'speed', self.mm_speed_val)

    def raster_current_target(self):
        if self.checks['raster'].isChecked():
            find_string = "./target_carousel/target[@ID='{}']/Size".format(self.brain.current_target())
            target_size = self.parent.preferences_dialog.pld_settings.find(find_string).text
            self.brain.arduino.update_motor_param('target', 'raster', target_size)
        else:
            # self.brain.raster_target(False, self.get_current_target())
            print('Raster Off')
        pass

    # Build custom behavior for keys that control substrate movement
    def keyReleaseEvent(self, eventQKeyEvent):
        key = eventQKeyEvent.key()
        if not eventQKeyEvent.isAutoRepeat():
            if key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Plus, Qt.Key_Minus]:
                print('Key {} released'.format(key))

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if event.key() in [Qt.Key_Up, Qt.Key_Plus]:
                self.sub_up()
            elif event.key() in [Qt.Key_Down, Qt.Key_Minus]:
                self.sub_down()

        return super().eventFilter(source, event)
