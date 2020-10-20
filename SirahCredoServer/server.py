import socket
import os
import json
import PySimpleGUI as sg
import laser_vi
import laser

__author__ = "Yves Auad"

abs_path = os.path.abspath(os.path.join((__file__ + "/../../nionswift_plugin/laser_mod/"), "global_settings.json"))
with open(abs_path) as savfile:
    settings = json.load(savfile)

SERVER_HOST = settings["SOCKET_SERVER"]["HOST"]
SERVER_PORT = settings["SOCKET_SERVER"]["PORT"]


class ServerSirahCredoLaser:

    def __init__(self, SERVER_HOST=SERVER_HOST, SERVER_PORT=SERVER_PORT, TIMEOUT=10.0):
        print("***SERVER***: Initializing SirahCredoServer...")
        if SERVER_HOST == '127.0.0.1':
            self.__sirah = laser_vi.SirahCredoLaser()
            print('***SERVER***: Server Running in Local Host. Laser is a virtual instrument in this case.')
        elif SERVER_HOST == '129.175.82.159':
            self.__sirah = laser.SirahCredoLaser()
            print('***SERVER***: Server Running in VG Lumiere. Real laser employed.')
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.settimeout(TIMEOUT)
        self.s.bind((SERVER_HOST, SERVER_PORT))

        if not self.__sirah.sucessfull:
            self.s.close()  # quits the server is not successful
            print('***SERVER***: Server not successfully created. Leaving...')

    def main_loop(self):
        self.s.listen(0)
        #while True:
        if 1:
            clientsocket, address = self.s.accept()
            print(f"***SERVER***: Connection from {address} has been established.")
            with clientsocket:
                while True:
                    try:
                        data = clientsocket.recv(512)
                    except:
                        print('***SERVER***: Client disconnected. Instantiate a new server for a new connection.')
                        break

                    if not data:
                        print('***SERVER***: No data received. Hanging for new connection...')
                        break

                    if b"server_ping" in data:
                        return_data = 'Server Alive'.encode()

                    elif b"set_hardware_wl" in data:  # set_hardware_wl(self, wl). no return
                        if data[15:19] == bytes(4):
                            wl = float(data[19: 35].decode())  # 16 bytes
                            self.__sirah.set_hardware_wl(wl)
                            return_data = 'None'.encode()

                    elif b"get_hardware_wl" in data:  # get_hardware_wl(self). return
                        if data[15:19] == bytes(4):
                            return_data = format(self.__sirah.get_hardware_wl()[0], '.8f').rjust(16, '0').encode()

                    elif b"setWL" in data:  # setWL(self, wavelength: float, current_wavelength: float). no return
                        if data[5:9] == bytes(4) and data[25:29] == bytes(4):
                            wl = float(data[9:25].decode())  # 16 bytes
                            cur_wl = float(data[29:45].decode())  # 16 bytes
                            return_data = self.__sirah.setWL(wl, cur_wl)

                    elif b"abort_control" in data:  # abort_control(self). No return
                        if data[13:17] == bytes(4):
                            self.__sirah.abort_control()
                            return_data = 'None'.encode()

                    elif b"set_scan_thread_locked" in data:  # set_scan_thread_locked(self). return
                        if data[22:26] == bytes(4):
                            return_data = self.__sirah.set_scan_thread_locked()
                            if return_data:
                                return_data = b'1'
                            else:
                                return_data = b'0'

                    elif b"set_scan_thread_release" in data:  # set_scan_thread_release(self). no return
                        if data[23:27] == bytes(4):
                            self.__sirah.set_scan_thread_release()
                            return_data = 'None'.encode()

                    elif b"set_scan_thread_check" in data:  # set_scan_thread_check(self). return
                        if data[21:25] == bytes(4):
                            return_data = self.__sirah.set_scan_thread_check()
                            if return_data:
                                return_data = b'1'
                            else:
                                return_data = b'0'

                    elif b"set_scan_thread_hardware_status" in data:  # set_scan_thread_hardware_status(self). return
                        if data[31:35] == bytes(4):
                            return_data = self.__sirah.set_scan_thread_hardware_status()
                            if return_data == 2:
                                return_data = b'2'
                            else:
                                return_data = b'3'

                    elif b"set_scan" in data:  # set_scan(self, cur, step, pts). no return
                        if data[8:12] == bytes(4) and data[28:32] == bytes(4) and data[48:52] == bytes(4):
                            cur = float(data[12:28].decode())  # 16 bytes
                            step = float(data[32:48])  # 16 bytes
                            pts = int(data[52:60])  # 8 bytes
                            self.__sirah.set_scan(cur, step, pts)
                            return_data = 'None'.encode()

                    else:
                        print(f'***SERVER***: Data {data} received unknown origin.')

                    clientsocket.sendall(return_data)

layout = [
    [sg.Text('Hanging Timeout (s): '), sg.In('10.00', size=(25, 1), enable_events=True, key='TIMEOUT')],
    [sg.Radio("Local Host", "Radio", size=(10, 1), key='LOCAL_HOST', enable_events=True, default=True),
     sg.Radio("VG Lumiere", "Radio", size=(10, 1), key='VG_LUMIERE', enable_events=True),
     sg.Radio("User Defined", "Radio", size=(10, 1), key='USER_DEFINED', enable_events=True)],
    [sg.Text('Host: '), sg.In('127.0.0.1', size=(25, 1), enable_events=True, key='HOST_NAME', disabled=True)],
    [sg.Text('Port: '), sg.In('65432', size=(25, 1), enable_events=True, key='PORT', disabled=True)],
    [sg.Button("Start"), sg.Button('Hang', disabled=True), sg.Button("Reset")]
]
window = sg.Window("Sirah Credo Server", layout)
while True:
    event, values = window.read()

    if event == 'LOCAL_HOST':
        window.FindElement('HOST_NAME').Update('127.0.0.1', disabled=True)
        window.FindElement('PORT').Update('65432', disabled=True)
    if event == 'VG_LUMIERE':
        window.FindElement('HOST_NAME').Update('129.175.82.159', disabled=True)
        window.FindElement('PORT').Update('65432', disabled=True)
    if event == 'USER_DEFINED':
        window.FindElement('HOST_NAME').Update('0.0.0.0', disabled=False)
        window.FindElement('PORT').Update('1', disabled=False)

    if event == "Start":
        try:
            ss = ServerSirahCredoLaser(values['HOST_NAME'], int(values['PORT']), float(values['TIMEOUT']))
            if ss._ServerSirahCredoLaser__sirah.sucessfull:
                window.FindElement('Hang').Update(disabled=False)
                window.FindElement('Start').Update(disabled=True)
                window.FindElement('LOCAL_HOST').Update(disabled=True)
                window.FindElement('VG_LUMIERE').Update(disabled=True)
                window.FindElement('USER_DEFINED').Update(disabled=True)
        except OSError:
            ss.s.close()
            print('***SERVER***: Could not BIND probably. MUST work on LOCALHOST.')
    if event == "Hang":
            try:
                ss.main_loop()

                try:
                    ss.s.close()
                    ss = None
                except:
                    print('***SERVER***: Server already reseted. There is no Socket object anymore.')
                window.FindElement('Hang').Update(disabled=True)
                window.FindElement('Start').Update(disabled=False)
                window.FindElement('LOCAL_HOST').Update(disabled=False)
                window.FindElement('VG_LUMIERE').Update(disabled=False)
                window.FindElement('USER_DEFINED').Update(disabled=False)

            except socket.timeout:
                ss.s.close()
                print('***SERVER***: Socket timeout. Retry connection.')
                window.FindElement('Hang').Update(disabled=True)
                window.FindElement('Start').Update(disabled=False)
            window.FindElement('LOCAL_HOST').Update(disabled=False)
            window.FindElement('VG_LUMIERE').Update(disabled=False)
            window.FindElement('USER_DEFINED').Update(disabled=False)
    if event == "Reset":
        try:
            ss.s.close()
            ss = None
        except:
            print('***SERVER***: Server already reseted. There is no Socket object anymore.')
        window.FindElement('Hang').Update(disabled=True)
        window.FindElement('Start').Update(disabled=False)
        window.FindElement('LOCAL_HOST').Update(disabled=False)
        window.FindElement('VG_LUMIERE').Update(disabled=False)
        window.FindElement('USER_DEFINED').Update(disabled=False)
    if event == sg.WIN_CLOSED:
        break
