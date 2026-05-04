from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from framework.core.task_state import TaskStatus
from framework.ui.views.base_qt_view import BaseQtView
from typing import Protocol
from PySide6.QtWidgets import QApplication
import sys


class IMainWindow(BaseQtView):
    def get_oh_no_button(self) -> QPushButton: 
        pass
    def get_change_message_button(self) -> QPushButton:
        pass
    def get_message_label(self) -> QLabel:
        pass   

class View_MainWindow(IMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counter = 0

        layout = QVBoxLayout()

        self.message_label = QLabel("Start")
        self.oh_no_button = QPushButton("DANGER!")
        self.oh_no_button.pressed.connect(self.oh_no)

        self.change_message_button = QPushButton("?")
        self.change_message_button.pressed.connect(self.change_message)

        layout.addWidget(self.message_label)
        layout.addWidget(self.oh_no_button)
        layout.addWidget(self.change_message_button)

        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.recurring_timer)
        self.timer.start()
    
    def oh_no(self):
        self.message_label.setText("Pressed")

    def change_message(self):
        self.message_label.setText("OH NO")

    def recurring_timer(self):
        self.counter += 1
        self.message_label.setText(f"Timer count: {self.counter}")

    def get_oh_no_button(self) -> QPushButton: 
        return self.oh_no_button
    def get_change_message_button(self) -> QPushButton:
        return self.change_message_button
    def get_message_label(self) -> QLabel:
        return self.message_label       

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = View_MainWindow()
    window.show()
    sys.exit(app.exec())    