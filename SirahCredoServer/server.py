import socket
import os
import json
import PySimpleGUI as sg
import laser_vi
import laser
import power_supply_vi
import power_supply
import power
import power_vi
import ard
import ard_vi
import time
import select
import sys

__author__ = "Yves Auad"

abs_path = os.path.abspath(os.path.join((__file__ + "/../../nionswift_plugin/laser_mod/"), "global_settings.json"))
with open(abs_path) as savfile:
    settings = json.load(savfile)

SERVER_HOST = settings["SOCKET_SERVER"]["HOST"]
SERVER_PORT = settings["SOCKET_SERVER"]["PORT"]


class ServerSirahCredoLaser:

    def __init__(self, SERVER_HOST=SERVER_HOST, SERVER_PORT=SERVER_PORT):
        self.__running = True
        print("***SERVER***: Initializing SirahCredoServer...")
        if SERVER_HOST == '129.175.82.159':
            self.__sirah = laser.SirahCredoLaser()
            self.__ps = power_supply.SpectraPhysics()
            self.__pwmeter = [power.TLPowerMeter('USB0::4883::32882::1907040::0::INSTR'),
                              power.TLPowerMeter('USB0::0x1313::0x8072::1908893::INSTR')]
            self.__ard = ard.Arduino()
            print('***SERVER***: Server Running in VG Lumiere. Real laser employed.')
        elif SERVER_HOST == '192.168.137.96':
            self.__sirah = laser.SirahCredoLaser('/dev/ttyUSB1')
            self.__ps = power_supply.SpectraPhysics('/dev/ttyUSB0')
            self.__pwmeter = [power.TLPowerMeter('USB0::4883::32882::1907040::0::INSTR'),
                              power.TLPowerMeter('USB0::0x1313::0x8072::1908893::INSTR')]
            self.__ard = ard.Arduino('/dev/ttyACM0')
            print('***SERVER***: Server Running in Raspberry Pi. Real Laser employed.')
        else:
            self.__sirah = laser_vi.SirahCredoLaser('COM12')
            self.__ps = power_supply_vi.SpectraPhysics('COM11')
            self.__pwmeter = [power_vi.TLPowerMeter('USB0::4883::32882::1907040::0::INSTR'),
                              power_vi.TLPowerMeter('USB0::0x1313::0x8072::1908893::INSTR')]
            self.__ard = ard_vi.Arduino('COM15')
            print('***SERVER***: Server Running in Local Host. Laser is a virtual instrument in this case.')
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.s.setblocking(False)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((SERVER_HOST, SERVER_PORT))
        self.instruments = list()
        self.instruments.append(self.__sirah)
        self.instruments.append(self.__ps)
        self.instruments.append(self.__pwmeter[0])
        self.instruments.append(self.__pwmeter[1])
        self.instruments.append(self.__ard)

        self.inputs = [self.s]
        self.outputs = []
        self.who = {}
        self.who['server'] = self.s
        self.message_queues = {}

        if not self.__sirah.successful or not self.__ps.successful or not self.__pwmeter[0].successful\
                or not self.__pwmeter[1].successful or not self.__ard.successful:
            self.s.close()  # quits the server is not successful
            print('***SERVER***: Server not successfully created. Check instrument message.')
        else:
            self.s.listen()
            print('***SERVER***: Server is listening.')

    def handle_error(self):
        for inst in self.instruments:
            if hasattr(inst, 'ser'):
                inst.ser.close()
            elif hasattr(inst, 'tl'):
                inst.tl.close()
        if hasattr(self.s, 'close'):
            self.s.close()


    def main(self):
        while self.__running:
            readable, writable, exceptional = select.select(self.inputs, self.outputs, self.inputs)
            for s in readable:
                if s is self.s:
                    clientsocket, address = self.s.accept()
                    #clientsocket.setblocking(False)
                    data = clientsocket.recv(512)
                    clientsocket.sendall(data)
                    self.inputs.append(clientsocket)
                    self.who[data.decode()] = clientsocket
                    print(f"***SERVER***: Connection from {address} has been established.")
                else:
                    try:
                        data = s.recv(512)
                        if not data:
                            self.inputs.remove(s)
                            self.handle_error()
                            print('***SERVER***: No data received. Waiting new connection.')
                            self.__running = False
                        else:
                            start_time = time.time()
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
                                    return_data = return_data + bytes(4) + b'LASER'

                            elif b"setWL" in data:  # setWL(self, wavelength: float, current_wavelength: float). no return
                                if data[5:9] == bytes(4) and data[25:29] == bytes(4):
                                    wl = float(data[9:25].decode())  # 16 bytes
                                    cur_wl = float(data[29:45].decode())  # 16 bytes
                                    return_data = self.__sirah.setWL(wl, cur_wl)
                                    return_data = return_data + bytes(4) + b'LASER'

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
                                    return_data = return_data + bytes(4) + b'LASER'

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
                                    return_data = return_data + bytes(4) + b'LASER'


                            elif b"set_scan_thread_hardware_status" in data:  # set_scan_thread_hardware_status(self). return
                                if data[31:35] == bytes(4):
                                    return_data = self.__sirah.set_scan_thread_hardware_status()
                                    if return_data == 2:
                                        return_data = b'2'
                                    else:
                                        return_data = b'3'
                                    return_data = return_data + bytes(4) + b'LASER'

                            elif b"set_scan" in data:  # set_scan(self, cur, step, pts). no return
                                if data[8:12] == bytes(4) and data[28:32] == bytes(4) and data[48:52] == bytes(4):
                                    cur = float(data[12:28].decode())  # 16 bytes
                                    step = float(data[32:48])  # 16 bytes
                                    pts = int(data[52:60])  # 8 bytes
                                    self.__sirah.set_scan(cur, step, pts)
                                    return_data = 'None'.encode()

                            ## Power Supply Functions
                            elif b"query" in data:
                                if data[5:8] == bytes(3):
                                    my_msg = data[8:-15]
                                    return_data = self.__ps.query(my_msg.decode())
                                    return_data = return_data + bytes(3) + b'POWER_SUPPLY'

                            elif b"comm" in data:
                                if data[4:7] == bytes(3):
                                    my_msg = data[7:-15]
                                    self.__ps.comm(my_msg.decode())
                                    return_data = 'None'.encode()

                            ## Power Meter Functions

                            elif b"pw_read" in data:
                                which=int(data[7:8])
                                if data[8:13] == bytes(5):
                                    try:
                                        wl = float(data[13: 29])
                                        return_data = format(self.__pwmeter[which].pw_read(wl), '.8f').rjust(16, '0').encode()
                                    except:
                                        print(f'***WARNING***: Power Meter {which} is disconnected.')
                                        return_data = format(9e5, '.8f').rjust(16, '0').encode()
                                    return_data = return_data + bytes(5) + b'POWERMETER'+data[7:8]

                            elif b"pw_reset" in data:
                                which=int(data[8:9])
                                if data[9:14] == bytes(5):
                                    self.__pwmeter[which].pw_reset()
                                    return_data = 'None'.encode()

                            elif b"pw_set_avg" in data:
                                which=int(data[10:11])
                                if data[11:16] == bytes(5):
                                    avg = int(data[16:24])
                                    try:
                                        self.__pwmeter[which].pw_set_avg(avg)
                                    except:
                                        print(f'***WARNING***: Power Meter {which} is disconnected.')
                                    return_data = 'None'.encode()

                            # Arduino Function
                            elif b"get_pos" in data:
                                if data[7:13] == bytes(6):
                                    return_data = format(self.__ard.get_pos(), '.0f').rjust(8, '0').encode()
                                    return_data = return_data + bytes(6) + b'ARDUINO'

                            elif b"set_pos" in data:
                                if data[7:13] == bytes(6):
                                    pos = int(data[13:21])
                                    self.__ard.set_pos(pos)
                                    return_data = 'None'.encode()

                            elif b"wobbler_on" in data:
                                if data[10:16] == bytes(6):
                                    pos = int(data[16:24])
                                    step = int(data[30:38])
                                    self.__ard.wobbler_on(pos, step)
                                    return_data = 'None'.encode()

                            elif b"wobbler_off" in data:
                                if data[11:17] == bytes(6):
                                    self.__ard.wobbler_off()
                                    return_data = 'None'.encode()

                            else:
                                print(f'***SERVER***: Data {data} received unknown origin.')

                            end = time.time()
                            s.sendall(return_data)
                            if 'bc' in self.who:
                                self.who['bc'].sendall(data+b'RX')
                                if return_data != b'None':
                                    self.who['bc'].sendall(return_data+b'TX')
                            if (end-start_time > 0.03):
                                print('***WARNING***: Server action took ' +format((end-start_time)*1000, '.1f')+ 'ms.')
                                print(f'Sent data was {data}')
                    except ConnectionResetError:
                        self.inputs.remove(s)
                        self.handle_error()
                        print('***SERVER***: Nionswift closed. Waiting new connection.')
                        self.__running = False



try:
    HOST = str(sys.argv[1])
    PORT = int(sys.argv[2])
    while True:
        print(f'***SERVER***: Looping Server without GUI over {HOST} @ {PORT}')
        ss = ServerSirahCredoLaser(HOST, PORT)
        ss.main()
except IndexError:
    print('***SERVER***: No HOST and/or PORT were given. UI starting...')
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
                ss = ServerSirahCredoLaser(values['HOST_NAME'], int(values['PORT']))
                if ss._ServerSirahCredoLaser__sirah.successful:
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
                    ss.main()
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
