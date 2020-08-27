import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((socket.gethostname(), 1234))
s.listen(5)

while True:
    clientsocket, adress = s.accept()
    print(f"Connection from {adress} has been stablished.")
    with clientsocket:
        while True:
            data = clientsocket.recv(1024)
            if not data:
                break
            clientsocket.sendall(data)
#clientsocket.send(bytes("Hey there!!!", "utf-8"))
#clientsocket.close()
