import socket
import argparse
import sys
import getpass
import hashlib
import csv


########################################################################
# Server class
########################################################################

class Server:
    HOSTNAME = "0.0.0.0"
    PORT = 50000
    RECV_BUFFER_SIZE = 1024
    MAX_CONNECTION_BACKLOG = 10
    MSG_ENCODING = "utf-8"
    SOCKET_ADDRESS = (HOSTNAME, PORT)
    GET_AVERAGES_CMD = "GETA"
    AUTHENTICATION = False

    def __init__(self):
        self.read_csv()
        self.create_listen_socket()
        self.process_connections_forever()

    def read_csv(self):
        print("\nData read from CSV file:\n")
        with open('course_grades_2018.csv') as csvfile:
            line = csvfile.readline()
            while line:
                print(line)
                line = csvfile.readline()

    def create_listen_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Set socket layer socket options. This allows us to reuse
            # the socket without waiting for any timeouts.
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(Server.SOCKET_ADDRESS)
            self.socket.listen(Server.MAX_CONNECTION_BACKLOG)
            print("Listening for connections on port {} ...".format(Server.PORT))
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def process_connections_forever(self):
        try:
            while True:
                self.AUTHENTICATION = False
                client = self.socket.accept()
                self.connection_handler(client)
        except Exception as msg:
            print(msg)
        except KeyboardInterrupt:
            print()

    def connection_handler(self, client):
        connection, address_port = client
        print("-" * 72)
        print("Connection received from {} on port {}.".format(address_port[0], address_port[1]))

        while True:
            try:
                # Receive bytes over the TCP connection. This will block
                # until "at least 1 byte or more" is available.
                recvd_bytes = connection.recv(Server.RECV_BUFFER_SIZE)

                # If recv returns with zero bytes, the other end of the
                # TCP connection has closed (The other end is probably in
                # FIN WAIT 2 and we are in CLOSE WAIT.). If so, close the
                # server end of the connection and get the next client
                # connection.
                if len(recvd_bytes) == 0:
                    print("Closing client connection ... ")
                    connection.close()
                    break

                if recvd_bytes == self.GET_AVERAGES_CMD.encode(self.MSG_ENCODING):
                    print("Received GAC from client.")
                    with open('course_grades_2018.csv') as csvfile:
                        connection.sendall(
                            (csvfile.readlines()[-1].split(',,,,')[1].split('\n')[0]).encode(Server.MSG_ENCODING))
                else:
                    print("Received IP/password hash from client:", recvd_bytes)
                    with open('course_grades_2018.csv') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            if row['ID Number'] == '':
                                break
                            h = hashlib.sha256()
                            h.update(row['ID Number'].encode(Server.MSG_ENCODING))
                            h.update(row['Password'].encode(Server.MSG_ENCODING))
                            if h.digest() == recvd_bytes:
                                self.AUTHENTICATION = True
                                print("Correct password, record found.")
                                connection.sendall(("Correct password, record found.\n" + "Hi, " + row[
                                    'First Name'] + " " + row['Last Name'] + "\nYour Midterm grade is: " + row[
                                                        'Midterm'] + "\nYour Lab 1 grade is: " + row[
                                                        'Midterm'] + "\nYour Lab 1 grade is: " + row[
                                                        'Lab 1'] + "\nYour Lab 2 grade is: " + row[
                                                        'Lab 2'] + "\nYour Lab 3 grade is: " + row[
                                                        'Lab 3'] + "\nYour Lab 4 grade is: " + row['Lab 4']).encode(
                                    Server.MSG_ENCODING))
                                break

                        if self.AUTHENTICATION != True:
                            print("Password failure.")
                            connection.sendall("Password failure.".encode(Server.MSG_ENCODING))

            except KeyboardInterrupt:
                print()
                print("Closing client connection ... ")
                connection.close()
                break


########################################################################
# Client class
########################################################################

class Client:
    # Set the server hostname to connect to. If the server and client
    # are running on the same machine, we can use the current
    # hostname.
    SERVER_HOSTNAME = socket.gethostname()
    HOSTNAME = socket.gethostname()
    PORT = 40000
    RECV_BUFFER_SIZE = 1024
    GET_AVERAGES_CMD = "GETA"

    def __init__(self):
        self.send_console_input_forever()

    def get_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((Client.HOSTNAME, Client.PORT))
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def connect_to_server(self):
        try:
            print("-" * 72)
            print("Please enter 'GETA' or student ID")
            self.get_console_input()
            print("Command entered:", self.input_text)
            if self.input_text == self.GET_AVERAGES_CMD:
                self.socket.connect((Client.SERVER_HOSTNAME, Server.PORT))
                self.connection_send()
                print("Fetching grade averages:")
                self.connection_receive()

            else:
                id_number = self.input_text
                print("Please enter your password:")
                p = getpass.getpass()
                password = p
                print("ID number: {} and password: {} received.".format(id_number, p))
                h = hashlib.sha256()
                h.update(id_number.encode(Server.MSG_ENCODING))
                h.update(password.encode(Server.MSG_ENCODING))
                self.socket.connect((Client.SERVER_HOSTNAME, Server.PORT))
                self.connection_send_byte(h.digest())
                print("ID/password hash: {} sent to server".format(h.digest()))
                self.connection_receive()
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def get_console_input(self):
        while True:
            self.input_text = input("Input: ")
            if self.input_text != "":
                break

    def send_console_input_forever(self):
        while True:
            try:
                self.get_socket()
                self.connect_to_server()
                print("Closing server connection ... ")
                self.socket.close()

            except (KeyboardInterrupt, EOFError):
                print()
                print("Closing server connection ...")
                self.socket.close()
                sys.exit(1)

    def connection_send(self):
        try:
            self.socket.sendall(self.input_text.encode(Server.MSG_ENCODING))
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def connection_send_byte(self, input_byte):
        try:
            self.socket.sendall(input_byte)
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def connection_receive(self):
        try:
            recvd_bytes = self.socket.recv(Client.RECV_BUFFER_SIZE)
            if len(recvd_bytes) == 0:
                print("Closing server connection ... ")
                self.socket.close()
                sys.exit(1)

            print(recvd_bytes.decode(Server.MSG_ENCODING))

        except Exception as msg:
            print(msg)
            sys.exit(1)


########################################################################
# Process command line arguments if this module is run directly.
########################################################################


if __name__ == '__main__':
    roles = {'client': Client, 'server': Server}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles,
                        help='server or client role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()

########################################################################
