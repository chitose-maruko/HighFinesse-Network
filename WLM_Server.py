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

DLL_PATH = "wlmData.dll"
try:
    wlmData.LoadDLL(DLL_PATH)
except:
    sys.exit("Error: Couldn't find DLL on path %s. Please check the DLL_PATH variable!" % DLL_PATH)

host = '192.168.1.56'
port = 5353

# Put the wavemeter in switcher mode
wlmData.dll.SetSwitcherMode(1)

# Initialize the wavelength list
Wavelength = 8*[0]
# Initialize the interferometer list
Interferometer = [[], [], [], [], [], [], [], []]

def client_handler(connection):
    while True:
        time.sleep(0.5)
        data = connection.recv(4096)
        select_list = pickle.loads(data)
        for n in range(8):
            if select_list[n] == 1:
                wlmData.dll.SetSwitcherSignalStates(n+1, 1, 1)
                test_wavelength = wlmData.dll.GetWavelengthNum(n+1, 0)
                if test_wavelength == wlmConst.ErrOutOfRange:
                    Wavelength[n] = 'Error: Out of Range'
                elif test_wavelength <= 0:
                    Wavelength[n] = f'Error code: {test_wavelength}'
                else:
                    Wavelength[n] = f'{test_wavelength}'
            elif select_list[n] == 0:
                wlmData.dll.SetSwitcherSignalStates(n+1, 0, 0)
                Wavelength[n] = '---'
            i = wlmData.dll.GetPatternItemCount(wlmConst.cSignal1Interferometers)
            ii = wlmData.dll.GetPatternItemSize(wlmConst.cSignal1Interferometers)
            wlmData.dll.SetPattern(wlmConst.cSignal1Interferometers, wlmConst.cPatternEnable)
            X = wlmData.dll.GetPatternNum(1, wlmConst.cSignal1Interferometers)
            wlmData.dll.GetPatternDataNum(1, wlmConst.cSignalAnalysisX, X)
            Interferometer[n] = np.ctypeslib.as_array(X, (i//ii,))
        to_send1 = pickle.dumps(Wavelength)
        connection.sendall(to_send1)
        to_send2 = pickle.dumps(Interferometer)
        connection.sendall(to_send2)

def accept_connections(ServerSocket):
    Client, address = ServerSocket.accept()
    print('Connected to: ' + address[0] + ':' + str(address[1]))
    threading.Thread(target=client_handler, args=(Client, )).start()

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