import serial
import os
import json
import sys
import logging
import time
import threading
import numpy
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

__author__ = "Yves Auad"


abs_path = os.path.abspath(os.path.join((__file__+"/../"), "global_settings.json"))
with open(abs_path) as savfile:
    settings = json.load(savfile)

DEBUG_pw = settings["PW"]["DEBUG"]

def _isPython3():
    return sys.version_info[0] >= 3

def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc

class controlRoutine:

    def __init__(self, sendmessage):
        self.sendmessage=sendmessage   
        #self.control_thread=None  


    def pw_control_thread(self, arg):
        self.control_thread=threading.currentThread()
        while getattr(self.control_thread, "do_run", True):
            if DEBUG_pw: time.sleep(0.05)
            self.sendmessage(101)

    def pw_control_thread_check(self):
        try:
            return getattr(self.control_thread, "do_run")
        except:
            return False

    def pw_control_thread_on(self):
        self.control_thread=threading.Thread(target=self.pw_control_thread, args=("task",))
        self.control_thread.do_run=True
        self.control_thread.start()

    def pw_control_thread_off(self):
        self.control_thread.do_run=False
