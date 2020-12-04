import socket

def snitch_func():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        s.connect(('129.175.81.128', 65432))
        #s.connect(('127.0.0.1', 65432))
        s.sendall('snitch'.encode())
        data = s.recv(2048)
        print(f'***Laser STATUS***: {data}')
    except:
        print(f'***Laser STATUS***: Laser disconnected.')


snitch_func()
