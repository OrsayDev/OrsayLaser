import socket
import threading
import logging
import time
import os
import json
from concurrent.futures import ThreadPoolExecutor

__author__ = "Yves Auad"

abs_path = os.path.abspath(os.path.join((__file__ + "/../nionswift_plugin/laser_mod/"), "global_settings.json"))
with open(abs_path) as savfile:
    settings = json.load(savfile)

DEBUG_LASER = settings["LASER"]["DEBUG"]

if DEBUG_LASER:
    import laser_vi as laser
else:
    import laser as laser


class ServerSirahCredoLaser:

    def __init__(self):
        print("***SERVER***: Initializing Server...")
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(('127.0.0.1', 65432))
        self.s.listen(5)

        self.__sirah = laser.SirahCredoLaser()


    def main_loop(self):
        while True:
            clientsocket, adress = self.s.accept()
            logging.info(f"Connection from {adress} has been stablished.")
            with clientsocket:
                while True:
                    data = clientsocket.recv(512)

                    if not data:
                        break

                    print(data)

                    if b"set_hardware_wl" in data:  # set_hardware_wl(self, wl). no return
                        if data[15:19] == bytes(4):
                            wl = float(data[19: 35].decode())  # 16 bytes
                            self.__sirah.set_hardware_wl(wl)
                            return_data = 'None'.encode()

                    if b"get_hardware_wl" in data:  # get_hardware_wl(self). return
                        if data[15:19] == bytes(4):
                            return_data = format(self.__sirah.get_hardware_wl()[0], '.8f').rjust(16, '0').encode()

                    if b"setWL" in data:  # setWL(self, wavelength: float, current_wavelength: float). no return
                        if data[5:9] == bytes(4) and data[25:29] == bytes(4):
                            wl = float(data[9:25].decode())  # 16 bytes
                            cur_wl = float(data[29:45].decode())  # 16 bytes
                            return_data = self.__sirah.setWL(wl, cur_wl)

                    if b"abort_control" in data:  # abort_control(self). No return
                        if data[13:17] == bytes(4):
                            self.__sirah.abort_control()
                            return_data = 'None'.encode()

                    if b"set_scan_thread_locked" in data:  # set_scan_thread_locked(self). return
                        if data[22:26] == bytes(4):
                            return_data = self.__sirah.set_scan_thread_locked()
                            if return_data:
                                return_data = b'1'
                            else:
                                return_data = b'0'

                    if b"set_scan_thread_release" in data:  # set_scan_thread_release(self). no return
                        if data[23:27] == bytes(4):
                            self.__sirah.set_scan_thread_release()
                            return_data = 'None'.encode()

                    if b"set_scan_thread_check" in data:  # set_scan_thread_check(self). return
                        if data[21:25] == bytes(4):
                            return_data = self.__sirah.set_scan_thread_check()
                            if return_data:
                                return_data = b'1'
                            else:
                                return_data = b'0'

                    if b"set_scan_thread_hardware_status" in data:  # set_scan_thread_hardware_status(self). return
                        if data[31:35] == bytes(4):
                            return_data = self.__sirah.set_scan_thread_hardware_status()
                            if return_data == 2:
                                return_data = b'2'
                            else:
                                return_data = b'3'

                    if b"set_scan" in data:  # set_scan(self, cur, step, pts). no return
                        if data[8:12] == bytes(4) and data[28:32] == bytes(4) and data[48:52] == bytes(4):
                            cur = float(data[12:28].decode())  # 16 bytes
                            step = float(data[32:48])  # 16 bytes
                            pts = int(data[52:60])  # 8 bytes
                            self.__sirah.set_scan(cur, step, pts)
                            return_data = 'None'.encode()

                    clientsocket.sendall(return_data)


ss = ServerSirahCredoLaser()
ss.main_loop()
