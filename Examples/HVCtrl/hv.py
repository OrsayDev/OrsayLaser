import socket

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    sock.connect(("192.168.1.37", 80))
    print('chromaTEM')  
except socket.timeout:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        print('vgLum')  
        sock.connect(("129.175.82.70", 80))
    except:
        print("No HV was found.")

v = 50
veff = int(v/10)
plus = ('HV+ ' + str(veff)+'\n').encode()
less = ('HV- ' + str(veff)).encode()

#sock.sendall(b'CMD:BOX')

sock.sendall(b'CMD?')
data = sock.recv(512)
print(data)

sock.sendall(b'HV:DAC?')
data = sock.recv(512)
print(data)

sock.sendall(b'HV:BOX?')
data = sock.recv(512)
print(data)

sock.sendall(b'HV:REM?')
data = sock.recv(512)
print(data)

sock.sendall(b'HV:MON?')
data = sock.recv(512)
index1 = data.find(b'+')
index2 = data.find(b'%', index1)

index3 = data.find(b'-')
index4 = data.find(b'%', index3)
print(data)
print(int(data[index1+1:index2]), int(data[index3+1:index4]))

sock.sendall(plus+less)
#sock.sendall(less)

#data = sock.recv(512)
#print(data)
