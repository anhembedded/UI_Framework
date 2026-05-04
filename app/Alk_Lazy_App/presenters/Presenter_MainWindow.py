from app.Alk_Lazy_App.tasks.task_run_files import Factory_Task_Run_Files
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
from app.Alk_Lazy_App.views.View_MainWindow import IMainWindow
import sys
from framework.ui.presenters.base_presenter import BasePresenter
from app.Alk_Lazy_App.tasks.task_run_files import TaskRunFilesWindows, TaskRunFilesLinux
from app.Alk_Lazy_App.tasks.task_get_all_runable_file import Task_Get_All_Runable_File


class Presenter_MainWindow(BasePresenter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def bind(self, view: IMainWindow) -> None:
        super().bind(view)
        view.get_oh_no_button().clicked.connect(self.on_oh_no)  

    def on_oh_no(self):
        file_path = r"C:/Users/hoang/Desktop"
        task = Task_Get_All_Runable_File(file_path)
    
    
    
  