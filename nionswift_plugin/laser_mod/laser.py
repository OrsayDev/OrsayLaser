import sys
import numpy
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import serial

__author__ = "Yves Auad"

def _isPython3():
    return sys.version_info[0] >= 3

def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc


class SirahCredoLaser:

    def __init__(self, sendmessage)->None:
        self.sendmessage=sendmessage
        self.abort_ctrl = False
        self.laser_thread = None
        self.thread = None
        self.lock=threading.Lock()
        
        ser = serial.Serial()
        ser.baudrate = 19200
        ser.port='COM12'
        ser.timeout=1

        try:
            if not ser.open():
                ser.open()
        except:
            self.sendmessage(7)


    def bytes_to_pos(self, s):
        dec_val = 0
        for i in range(len(s)):
            dec_val+=256**i * s[i]
        return dec_val

    def pos_to_bytes(self, pos):
        rem = pos
        val = numpy.zeros(4, dtype=int)
        for j in range(4): #4 bytes
            val[j] = rem % 256
            rem = rem - val[j]
            rem = rem / 256
        return val

    def pos_to_wl(self, pos):
        wl = -5.26094211e-17 * pos**3 + 8.28867083e-11 * pos**2 -4.28775800e-4 * pos + 1.10796664e3
        return wl

    def wl_to_pos(self, wl):
        pos = -1.42336972e-4 * wl**3 - 8.58549626e-1 * wl**2 -9.54738134e2 * wl +2.16000371e6
        return int(pos)

    def set_hardware_wl(self, wl):
        pos = self.wl_to_pos(wl)
        byt = self.pos_to_bytes(pos)
        checksum = byt.sum() + 60 + 7 + 1 #head associated with send
        if (checksum > 255):
            checksum -= 256
        send_mes = [60, 7, 1, byt[0], byt[1], byt[2], byt[3], 0, 0, 0, 0, checksum, 62]
        ba_send_mes = bytearray(send_mes)
        pos2 = self.bytes_to_pos(byt)
        if (wl > 500 and wl < 800):
            try:
                ser.open()
                ser.write(ba_send_mes)
                ser.close()
            except:
                self.sendmessage(5)
        else:
            print("Care with WL!")

    def get_hardware_wl(self):
        mes = [60, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 62]
        bs=bytearray(mes)
        try:
            ser.write(bs)
            ser.read(1)
            error = ser.read(1)
            ser.read(1)
            status = ser.read(1)
            abs1 = ser.read(4)
            ser.read(6) #clear buffer
            pos = self.bytes_to_pos(abs1)
            cur_wl = pos_to_wl(pos)
            return (cur_wl, status[0])
        except:
            self.sendmessage(6)
            return (580, None)
        


    def set_startWL(self, wl: float, cur_wl: float):
        self.set_hardware_wl(wl)
        self.sendmessage(2)

    def setWL(self, wavelength: float, current_wavelength: float):
        if (float(current_wavelength) == float(wavelength)):
            self.sendmessage(1)
        else:
            self.laser_thread = threading.Thread(target=self.set_startWL, args=(wavelength, current_wavelength))
            self.laser_thread.start()
            self.laser_thread.join() #this thread has a join() which means you wait until it finishes

    
    
    
    
    def abort_control(self):
        self.abort_ctrl = True

    def set_scan_thread_locked(self):
        return self.lock.locked()

    def set_scan_thread_release(self):
        self.lock.release()

    def set_scan_thread_check(self):
        if self.thread==None:
            return True #if there is none then its done
        else:
            return self.thread.done()

    def set_scan_thread_hardware_status(self):
        return self.get_hardware_wl()[1] #2 hold; 3 moving

    def set_scan_thread(self, cur, i_pts, step):
        if not self.abort_ctrl:
            self.lock.acquire()
            self.set_hardware_wl(cur+i_pts*step)
        else:
            with self.lock:
                logging.info("Laser abort control function.")
                self.sendmessage(4)

    def set_scan(self, cur, step, pts):
        self.abort_ctrl = False
        pool = ThreadPoolExecutor(1)
        for index in range(pts):
            self.thread = pool.submit(self.set_scan_thread, cur, index, step)
        
        #self.set_scan_thread_release()



