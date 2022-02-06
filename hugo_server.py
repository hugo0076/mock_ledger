import socket
import os
from _thread import *
import socket
import os
from threading import Thread
import thread

ServerSocket = socket.socket()
host = '127.0.0.1'
port = 1234
ThreadCount = 0

bids = []
offers = []

try:
    ServerSocket.bind((host, port))
except socket.error as e:
    print(str(e))

print('Waitiing for a Connection..')
ServerSocket.listen(5)

def threaded_client(connection):
    connection.send(str.encode('Welcome to the Server'))
    while True:
        data = connection.recv(2048)
        decoded_data = data.decode('utf-8')
        if decoded_data[0].upper() not in ['B', 'S']:
            reply = 'Bad request, pls try again'
        elif decoded_data[0].upper() == 'B': # buy order
            px = int(decoded_data[1:])
            bids.append(px)
            reply = 'Bid placed'
        elif decoded_data[0].upper() == 'S': # sell order
            px = int(decoded_data[1:])
            offers.append(px)
            reply = 'offer placed'
        book = f' |bids = {bids}, offers = {offers}|'
        if not data:
            break
        reply = reply + book
        print(f'reply = {reply}')
        connection.sendall(str.encode(reply))
    connection.close()

clients = set()
clients_lock = threading.Lock()

def listener(client, address):
    print("Accepted connection from: ", address)
    with clients_lock:
        clients.add(client)
    try:    
        while True:
            data = client.recv(1024)
            if not data:
                break
            else:
                print repr(data)
                with clients_lock:
                    for c in clients:
                        c.sendall(data)
    finally:
        with clients_lock:
            clients.remove(client)
            client.close()

while True:
    Client, address = ServerSocket.accept()
    print('Connected to: ' + address[0] + ':' + str(address[1]))
    start_new_thread(threaded_client, (Client, ))
    ThreadCount += 1
    print('Thread Number: ' + str(ThreadCount))
ServerSocket.close()