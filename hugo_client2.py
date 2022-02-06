import socket
import sys
def main(type):
    ClientSocket = socket.socket()
    host = socket.gethostname()
    port = 10016
    print('Waiting for connection')
    try:
        ClientSocket.connect((host, port))
    except socket.error as e:
        print(str(e))
    if type == 1: # sender
        while True:
            Input = input('Say Something: ')
            ClientSocket.send(str.encode(Input))
            Response = ClientSocket.recv(1024)
            print(f"Response: {Response.decode('utf-8')}")
    else: # reciever
        while True:
            try:
                response = ClientSocket.recv(1024)
                print(f"Response: {response.decode('utf-8')}")
            except:
                pass

if __name__ == "__main__":
   main(int(sys.argv[1]))

