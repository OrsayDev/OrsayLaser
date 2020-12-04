import socket
import pickle

def snitch_func():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.1)
    try:
        #s.connect(('129.175.81.128', 65432))
        s.connect(('127.0.0.1', 65432))
        s.sendall('snitch'.encode())
        data = s.recv(512)
        print(pickle.loads(data))
        if data == b'snitch':
            print('***SERVER STATUS***: Auxiliary client connected.')
            return True
    except:
        print('***SERVER STATUS***: Auxiliary client not connected. Check server.')
        return False

snitch_func()
