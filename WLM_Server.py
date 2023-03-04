#!/usr/bin/env python3

# Allows server connection to multiple clients, as well as wavemeter interaction

import socket
import threading
import time
#import wlmData
#import wlmConst
import sys
import pickle
import numpy as np
#import nidaqmx
#from nidaqmx import stream_writers

#modules for the local test
from server_test_module import wlmTest
test = wlmTest()
#global variable for the header of the message
HEADERLENGTH=8
# Load in the DLL provided by HighFinesse
DLL_PATH = "wlmData.dll"
#try:
    #wlmData.LoadDLL(DLL_PATH)
#except:
    #sys.exit(
    #    "Error: Couldn't find DLL on path %s. Please check the DLL_PATH variable!"
    #    % DLL_PATH
    #)

# Specify the IP address and TCP port which will be used to host the server
#modified for the local test
host = "127.0.0.1"
port = 5000

# Put the wavemeter in switcher mode
test.SetSwitcherMode(1)

# Initialize the wavelength list, zeroth entry serves as an identifier for the client
Wavelength = 8 * [0]
# Initialize the interferometer list, zeroth entry serves as an identifier for the client
Interferometer = 8 * [[]]
# Initialize the combined list which will be sent over the network
to_send = [Wavelength, Interferometer]

# Create a function which will manage the connection with the client
def client_handler(connection):
    # Loop to continually interact with the client
    global test
    while True:
        data = connection.recv(4096)
        selec_list = pickle.loads(data)

        for i in range(8):
            # Set the exposure times accoring to selec_list
            try:
                test.SetExposureNum(i + 1, 1, int(selec_list[i][1]))
            except:
                pass

            # Manage sending the wavelength data
            if selec_list[i][0] != "Off":
                test.SetSwitcherSignalStates(i + 1, 1, 1)
                test_wavelength = test.GetWavelengthNum(i + 1, 0)
                #if test_wavelength == wlmConst.ErrOutOfRange:
                    #Wavelength[i] = "Error: Out of Range"
                #elif test_wavelength <= 0:
                    #Wavelength[i] = f"Error code: {test_wavelength}"
                #else:
                Wavelength[i] = f"{test_wavelength}"
                to_send[0] = Wavelength
            # Don't bother reading the wavelength if the client doesn't request it
            elif selec_list[i][0] == "Off":
                test.SetSwitcherSignalStates(i + 1, 0, 0)
                Wavelength[i] = "---"
                Interferometer[i] = []
            # Manage sending the interferometer data
            if (
                selec_list[i][0] == "Interferometer"
                or selec_list[i][0] == "Both Graphs"
            ):
                #n = wlmData.dll.GetPatternItemCount(wlmConst.cSignal1Interferometers)
                #nn = wlmData.dll.GetPatternItemSize(wlmConst.cSignal1Interferometers)
                #wlmData.dll.SetPattern(
                #    wlmConst.cSignal1Interferometers, wlmConst.cPatternEnable
                #)
                #X = wlmData.dll.GetPatternNum(i + 1, wlmConst.cSignal1Interferometers)
                #wlmData.dll.GetPatternDataNum(i + 1, wlmConst.cSignalAnalysisX, X)
                #Interferometer[i] = list(np.ctypeslib.as_array(X, (n // nn,)))
                #to_send[1] = Interferometer
                test.randomPattern(i+1)
                Interferometer[i] =test.patternList[i]
                to_send[1] = Interferometer

            # Try to change output voltage on the NI device according to PID output
            #try:
            #    pid_out = selec_list[i][2]
            #    with nidaqmx.Task() as task:
            #        # Add in the two available channels
            #        task.ao_channels.add_ao_voltage_chan("Dev1/ao0")
            #        task.ao_channels.add_ao_voltage_chan("Dev1/ao1")

            #        input = np.array([pid_out, pid_out])

            #        # Set the voltage to whatever values are specified in the input array
            #        stream_writers.AnalogMultiChannelWriter(
            #            task.out_stream, auto_start=True
            #        ).write_one_sample(input)

            #except:
                #pass

        # Send the acquired data
        msgLength=f"{len(pickle.dumps(to_send)):<{HEADERLENGTH}}"
        connection.sendall(msgLength.encode())
        connection.sendall(pickle.dumps(to_send))
        # Specified wait time to allow for multiple clients
        # Without this, opening an additional client causes the initial client program to freeze
        # This time delay could potentially be reduced
        time.sleep(0.5)


# Create a function which will connect to clients and assign these to be managed in individual threads
def accept_connections(ServerSocket,counter):
    Client, address = ServerSocket.accept()
    print("Connected to: " + address[0] + ":" + str(address[1]))
    threading.Thread(target=client_handler, args=(Client,)).start()
    if counter<1:
        threading.Thread(target=expTest,args=()).start()


# Lastly, create a function which starts the server
def start_server(host, port):
    counter =0
    ServerSocket = socket.socket()
    try:
        ServerSocket.bind((host, port))
    except socket.error as e:
        print(str(e))
    print(f"Server is listening on TCP port {port}...")
    ServerSocket.listen()

    while True:
        accept_connections(ServerSocket,counter)
        counter +=1

def expTest():
    for i in range(20):
        global test
        print(test.expTimes)
        time.sleep(3)


start_server(host, port)
