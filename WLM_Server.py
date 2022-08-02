# Allows server connection to multiple clients
# Based on the code found here: https://github.com/realpython/materials/tree/master/python-sockets-tutorial

import socket
import threading
import time
import wlmData
import wlmConst
import sys
import pickle
import numpy as np

# Load in the DLL provided by HighFinesse
DLL_PATH = "wlmData.dll"
try:
    wlmData.LoadDLL(DLL_PATH)
except:
    sys.exit("Error: Couldn't find DLL on path %s. Please check the DLL_PATH variable!" % DLL_PATH)

# Specify the IP address and TCP port which will be used to host the server
host = '192.168.1.56'
port = 5353

# Put the wavemeter in switcher mode
wlmData.dll.SetSwitcherMode(1)

# Initialize the wavelength list, zeroth entry serves as an identifier for the client
Wavelength = 8*[0]
# Initialize the interferometer list, zeroth entry serves as an identifier for the client
Interferometer = 8*[[]]
# Initialize the combined list which will be sent over the network
to_send = [Wavelength, Interferometer]

# Create a function which will manage the connection with the client
def client_handler(connection):
    # Loop to continually interact with the client
    while True:
        data = connection.recv(4096)
        selec_list = pickle.loads(data)
        
        for n in range(8):
            # Set the exposure times accoring to selec_list
            try:
                wlmData.dll.SetExposureNum(n+1, 1, int(selec_list[n][1]))
            except:
                pass
            # Manage sending the wavelength data
            if selec_list[n][0] != 'Off':
                wlmData.dll.SetSwitcherSignalStates(n+1, 1, 1)
                test_wavelength = wlmData.dll.GetWavelengthNum(n+1, 0)
                if test_wavelength == wlmConst.ErrOutOfRange:
                    Wavelength[n] = 'Error: Out of Range'
                elif test_wavelength <= 0:
                    Wavelength[n] = f'Error code: {test_wavelength}'
                else:
                    Wavelength[n] = f'{test_wavelength}'
                to_send[0] = Wavelength
            # Don't bother reading the wavelength if the client doesn't request it
            elif selec_list[n][0] == 'Off':
                wlmData.dll.SetSwitcherSignalStates(n+1, 0, 0)
                Wavelength[n] = '---'
                Interferometer[n] = []
            # Manage sending the interferometer data
            if selec_list[n][0] == 'Interferometer' or selec_list[n][0] == 'Both Graphs':
                i = wlmData.dll.GetPatternItemCount(wlmConst.cSignal1Interferometers)
                ii = wlmData.dll.GetPatternItemSize(wlmConst.cSignal1Interferometers)
                wlmData.dll.SetPattern(wlmConst.cSignal1Interferometers, wlmConst.cPatternEnable)
                X = wlmData.dll.GetPatternNum(n+1, wlmConst.cSignal1Interferometers)
                wlmData.dll.GetPatternDataNum(n+1, wlmConst.cSignalAnalysisX, X)
                Interferometer[n] = list(np.ctypeslib.as_array(X, (i//ii,)))
                to_send[1] = Interferometer
        # Send the acquired data
        connection.sendall(f'{len(pickle.dumps(to_send))}'.encode())
        time.sleep(0.5)
        connection.sendall(pickle.dumps(to_send))

# Create a function which will connect to clients and assign these be managed in individual threads
def accept_connections(ServerSocket):
    Client, address = ServerSocket.accept()
    print('Connected to: ' + address[0] + ':' + str(address[1]))
    threading.Thread(target=client_handler, args=(Client, )).start()

# Lastly, create a function which starts the server
def start_server(host, port):
    ServerSocket = socket.socket()
    try:
        ServerSocket.bind((host, port))
    except socket.error as e:
        print(str(e))
    print(f'Server is listening on TCP port {port}...')
    ServerSocket.listen()

    while True:
        accept_connections(ServerSocket)

start_server(host, port)
