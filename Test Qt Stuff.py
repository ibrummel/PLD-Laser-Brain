from PyQt5.QtCore import Qt, QTimer, QObject, QRect
from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator, QKeySequence, QIcon, QPainter
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
                             QWidget, QMessageBox, QFormLayout, QStackedWidget, QSpacerItem,
                             QFrame, QMainWindow, QDockWidget, QShortcut, QSlider, QGridLayout, QDialog)
import sys
from Motor_Control_Module import MotorControlPanel
from pathlib import Path


class ButtonOnWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.steps = 0

        self.btn = QPushButton('Test')
        self.btn.clicked.connect(self.increment)
        self.btn.setAutoRepeat(True)
        self.btn.setAutoRepeatDelay(1000)
        self.btn.setAutoRepeatInterval(100)
        self.up = QShortcut(QKeySequence(Qt.Key_Plus), self)
        self.up.activated.connect(self.increment)

        self.down = QShortcut(QKeySequence(Qt.Key_Minus), self)
        self.down.activated.connect(self.decrement)

        self.label = QLabel(str(self.steps))
        self.vbox = QVBoxLayout()

        self.vbox.addWidget(self.btn)
        self.vbox.addWidget(self.label)

        self.setLayout(self.vbox)

    def increment(self):
        self.steps += 1
        self.label.setText(str(self.steps))

    def decrement(self):
        self.steps -= 1
        self.label.setText(str(self.steps))


def main():
    app = QApplication(sys.argv)

    ex = MotorControlPanel()
    ex.show()

    if ex:
        print("Exterior accepted")
    elif not ex:
        print("exterior rejected")

    sys.exit(app.exec_())


# =============================================================================
# Run
# =============================================================================
if __name__ == '__main__':
    main()
