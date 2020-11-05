import numpy
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor

__author__ = "Yves Auad"

class SirahCredoLaser:

    def __init__(self)->None:
        self.abort_ctrl = False
        self.laser_thread = None
        self.thread = None
        self.thread_wl = 575.0
        self.lock = threading.Lock()

        self.successful = True

    def set_hardware_wl(self, wl):
        self.thread_wl = wl
        latency = round(float(5) * 1.0 / 20.0 + 0.5 * abs(numpy.random.randn(1)[0]), 5)
        time.sleep(latency)

    def get_hardware_wl(self):
        return (self.thread_wl, 0)

    def set_startWL(self, wl: float, cur_wl: float):
        latency = round(abs(cur_wl - wl) * 1.0 / 20.0 + 0.25, 5)
        time.sleep(latency)
        time.sleep(5)
        self.thread_wl = wl

    def setWL(self, wavelength: float, current_wavelength: float):
        if (float(current_wavelength) == float(wavelength)):
            return b'message_01'
        else:
            self.laser_thread = threading.Thread(target=self.set_startWL, args=(wavelength, current_wavelength))
            self.laser_thread.start()
            return b'message_02'

    def abort_control(self):
        self.abort_ctrl = True

    def set_scan_thread_locked(self):
        return self.lock.locked()

    def set_scan_thread_release(self):
        if self.lock.locked():
            self.lock.release()

    def set_scan_thread_check(self):
        if self.thread == None:
            return True  # if there is none then its done
        else:
            return self.thread.done()

    def set_scan_thread_hardware_status(self):
        if self.lock.locked():
            return 2  # motor holding. You can avance
        else:
            return 3  # motor moving. Do not avance

    def set_scan_thread(self, cur, i_pts, step):
        if not self.abort_ctrl:
            self.lock.acquire()
            self.set_hardware_wl(cur + i_pts * step)
        else:
            with self.lock:
                logging.info('***LASER***: Laser abort control function.')

    def set_scan(self, cur: float, step: float, pts: int):
        self.abort_ctrl = False
        pool = ThreadPoolExecutor(1)
        for index in range(pts):
            self.thread = pool.submit(self.set_scan_thread, cur, index, step)


