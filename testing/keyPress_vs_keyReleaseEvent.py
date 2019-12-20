import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtCore import pyqtSlot, Qt, QEvent

class App(QWidget):

    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 button - pythonspot.com'
        self.left = 200
        self.top = 200
        self.width = 320
        self.height = 200
        self.count = 0
        self.installEventFilter(self)
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.button = QPushButton('PyQt5 button', self)
        self.button.setToolTip('This is an example button')
        self.button.move(100, 70)
        self.button.setCheckable(True)
        #self.button.toggle()
        # button.installEventFilter(self)
        self.button.clicked.connect(self.on_click)
        
        self.show()

    @pyqtSlot()
    def on_click(self):
        if self.button.isChecked():
            self.button.setText('Checked')
        elif not self.button.isChecked():
            self.button.setText('Unchecked')
        print('PyQt5 button click')
        

    def keyReleaseEvent(self, eventQKeyEvent):
        key = eventQKeyEvent.key()
        if key == Qt.Key_I and not eventQKeyEvent.isAutoRepeat():
            print('released')
            self.count = 0

    # def eventFilter(self, source, event):
        # if event.type() == QEvent.KeyPress:
            # print(event.key())
        # return super().eventFilter(source, event)

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_I:
            print('right arrow pressed {}'.format(self.count))
            self.count += 1
        return super().eventFilter(source, event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
