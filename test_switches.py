import RPi_Hardware as hardware
from PyQt5.QtWidgets import QApplication, QLabel
import sys

app = QApplication([])
label = QLabel("Preserve event loop")
rpi = hardware.RPiHardware()
label.show()
sys.exit(app.exec_())
print("RPi initialized")
