

# Create a Qt application
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QApplication, QListView

# Reimplement item so that we can store stuff in it (i.e. the xml element that we need for the deposition step
# add a function to set the step number when they are changed.
class DepStandardItem(QStandardItem):

    def __init__(self, *__args):
        super().__init__(*__args)
        self.property = None
        self.setCheckable(True)

    def set(self, xml: str):
        self.property = xml

    def get(self):
        print(self.property)


app = QApplication(sys.argv)

# Our main window will be a QListView
list = QListView()
# Set flags so that drag and drop is enabled (should all be set from the .ui file
list.setMovement(QListView.Snap)
list.setDragDropMode(QListView.InternalMove)
list.setDragDropOverwriteMode(False)
list.setDefaultDropAction(Qt.MoveAction)
list.setSelectionMode(QListView.ExtendedSelection)
list.setWindowTitle('Honey-Do List')
list.setMinimumSize(600, 400)

# Create an empty model for the list's data
model = QStandardItemModel(list)

# Add some textual items
foods = [
    'Cookie dough',  # Must be store-bought
    'Hummus',  # Must be homemade
    'Spaghetti',  # Must be saucy
    'Dal makhani',  # Must be spicy
    'Chocolate whipped cream'  # Must be plentiful
]

for food in foods:
    # Create an item with a caption
    item = DepStandardItem(food)
    item.set(food)

    # Add a checkbox to it
    item.setCheckable(True)
    # Disable the items dropping on each other
    item.setDropEnabled(False)

    # Add the item to the model
    model.appendRow(item)


def on_item_changed(item):
    # If the changed item is not checked, don't bother checking others
    if not item.checkState():
        return
    else:

        item.get()
        model.appendRow(DepStandardItem('new item'))

    # Loop through the items until you get None, which
    # means you've passed the end of the list
    i = 0
    while model.item(i):
        if not model.item(i).checkState():
            return
        i += 1

    app.quit()


model.itemChanged.connect(on_item_changed)

# Apply the model to the list view
list.setModel(model)

# Show the window and run the app
list.show()
app.exec_()