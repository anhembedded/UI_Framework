from abc import abstractmethod
from framework.core.task_context import TaskContext
from framework.core.task import AbstractTask
from app.Alk_Lazy_App.util.helper import OS_Type, Helper
import os
from abc import ABC



class ITaskRunFiles(ABC):
    @abstractmethod
    def run(self, ctx: TaskContext):
        pass


class TaskRunFilesWindows(ITaskRunFiles):
    def __init__(self, file_path):
        self.file_path = file_path

    def run(self, ctx: TaskContext):
        try:
            os.system(f"start {self.file_path}")
            ctx.report_message("File opened successfully")
        except Exception as e:
            ctx.report_message(f"Error opening file: {str(e)}")    
        

class TaskRunFilesLinux(ITaskRunFiles):
    def __init__(self, file_path):
        self.file_path = file_path

    def run(self, ctx: TaskContext):
        try:
            os.system(f"open {self.file_path}")
            ctx.report_message("File opened successfully")
        except Exception as e:
            ctx.report_message(f"Error opening file: {str(e)}")    
        

class Factory_Task_Run_Files():
    def create(self, file_path) -> ITaskRunFiles:
        if Helper.get_what_os() == OS_Type.WINDOWS:
            return TaskRunFilesWindows(file_path)
        elif Helper.get_what_os() == OS_Type.LINUX_MAC:
            return TaskRunFilesLinux(file_path)
        else:
            raise ValueError("Unknown OS")