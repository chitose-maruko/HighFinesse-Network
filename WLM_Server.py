#!/usr/bin/env python3

# Allows server connection to multiple clients, as well as wavemeter interaction

import socket
import threading
import time
import wlmData
import wlmConst
import random
import sys
import pickle
import numpy as np
import nidaqmx
from nidaqmx import stream_writers

# #modules for the local test
# from server_test_module import wlmTest
# test = wlmTest()
#global variable for the header of the message
HEADERLENGTH=8
# Load in the DLL provided by HighFinesse
DLL_PATH = "wlmData.dll"

#comment out in case of local test
try:
    wlmData.LoadDLL(DLL_PATH)
except:
    sys.exit(
        "Error: Couldn't find DLL on path %s. Please check the DLL_PATH variable!"
        % DLL_PATH
    )

# Specify the IP address and TCP port which will be used to host the server
# #modified for the local test
# host = "127.0.0.1"
# port = 5000
#for machine test
host = "192.168.1.30"
port = 5353

#global variable to be shared among all clients and the server
exp_Time=8*[1] 
PID_val = 8 * [[False, 0.0, 0.0, 0.0]]

# #line for local test
# test.SetSwitcherMode(1)

#Put the wavemeter in switcher mode
wlmData.dll.SetSwitcherMode(1)

# Initialize the wavelength list, zeroth entry serves as an identifier for the client
Wavelength = 8 * [0]
# Initialize the interferometer list, zeroth entry serves as an identifier for the client
Interferometer = 8 * [[]]
#Initialize the exposure time list, zeroth entry serves as an identifier whether there has been an update
Exposures=8*[1]
PIDs=[False,8*[False,0,0,0]]
Targets=[False]
# Initialize the combined list which will be sent over the network
#to_send = [Wavelength, Interferometer,Exposures,PIDs,Targets]
#global variable to indicate the updates avaialbility for parameters
update=True
#Initialize the list of parameter update avaialbilities for each client
client_updates=[]

# Create a function which will manage the connection with the client
def client_handler(connection,counter):
    # Loop to continually interact with the client
    global test
    global selec_list
    global client_updates
    global Exposures
    global client_list
    client_id = counter
    exposures=[False,Exposures]
    client = client_list[counter]

    while True:
        exp_overwrite =False
        length=int(connection.recv(8))
        msg=[]
        while len(B"".join(msg))<length:
            temp=connection.recv(64)
            msg.append(temp)
        selec_list = pickle.loads(b"".join(msg))
        ch_active=[]
        for i in range(8):
            if selec_list[i][0]!= "Off":
                ch_active.append(i+1)
        for ch in ch_active:
            try:
                # test.SetSwitcherSignalStates(ch, 1, 1)
                wlmData.dll.SetSwitcherSignalStates(ch, 1, 1)
                #exposure reading from the wavemeter itself
                expo_read=wlmData.dll.GetExposureNum(ch,1,0) 
                if expo_read!=Exposures[ch-1]:
                    Exposures[ch-1]=expo_read
                    exp_overwrite=True
                    for elm in client_list:
                        elm.update = True
            except: 
                pass
        #reflect the parameter updates from another client if there is any but overwrite
        # it if there is newer update
        if client.update and (not selec_list[-1][0]):
            exposures[0]=True
            exposures[1]=Exposures
            client.update=False

        if selec_list[-1][0]==True:
            for ch in ch_active:
            # Set the exposure times accoring to selec_list
                try:
                    if exp_overwrite==False:
                        #line for local test
                        #test.SetExposureNum(ch, 1, int(selec_list[ch-1][1]))
                        #line for machine test
                        wlmData.dll.SetExposureNum(ch, 1, int(selec_list[ch-1][1]))
                        Exposures[i]=int(selec_list[ch-1][1])                  
                except:
                    pass

            selec_list[-1][0]=False
            for i in range(len(client_list)):
                if i!=client_id:
                    client_list[i].update=True
                elif exp_overwrite:
                    client_list[i].update=True
                else:
                    client_list[i].update=False
        for ch in ch_active:
            # # Set the exposure times accoring to selec_list
            # try:
            #     test.SetExposureNum(i + 1, 1, int(selec_list[i][1]))
            #     Exposures[1][i]=selec_list[i][1]
            # except:
            #      pass

            # # Manage sending the wavelength data
            # if selec_list[][0] != "Off":
            # #line for the local test
            # test_wavelength = test.GetWavelengthNum(ch, 0)
            # Wavelength[ch-1] = f"{test_wavelength}"

            #line for the actual run
            test_wavelength = wlmData.dll.GetWavelengthNum(ch, 0)
            if test_wavelength == wlmConst.ErrOutOfRange:
                Wavelength[ch-1] = "Error: Out of Range"
            elif test_wavelength <= 0:
                Wavelength[ch-1] = f"Error code: {test_wavelength}"
            else:
                Wavelength[ch-1] = f"{test_wavelength}"
            to_send[0] = Wavelength
            # Don't bother reading the wavelength if the client doesn't request it
            # elif selec_list[i][0] == "Off":
            #     #line for local test
            #     test.SetSwitcherSignalStates(i + 1, 0, 0)
            #     # #line for actual test
            #     # wlmData.dll.SetSwitcherSignalStates(i + 1, 0, 0)
            #     Wavelength[i] = "---"
            #     Interferometer[i] = []
            # Manage sending the interferometer data
            if (
                selec_list[ch-1][0] == "Interferometer"
                or selec_list[ch-1][0] == "Both Graphs"
            ):
                #comment out the following block for the local test
                n = wlmData.dll.GetPatternItemCount(wlmConst.cSignal1Interferometers)
                nn = wlmData.dll.GetPatternItemSize(wlmConst.cSignal1Interferometers)
                wlmData.dll.SetPattern(
                    wlmConst.cSignal1Interferometers, wlmConst.cPatternEnable
                )
                X = wlmData.dll.GetPatternNum(ch, wlmConst.cSignal1Interferometers)
                wlmData.dll.GetPatternDataNum(ch, wlmConst.cSignalAnalysisX, X)
                Interferometer[ch-1] = list(np.ctypeslib.as_array(X, (n // nn,)))
                to_send[1] = Interferometer

                # #line for the local test
                # test.randomPattern(ch)
                # Interferometer[ch-1] =test.patternList[ch-1]
                # to_send[1] = Interferometer

            # comment the following block for the local test
            # Try to change output voltage on the NI device according to PID output
            try:
               pid_out = selec_list[ch-1][2]
               with nidaqmx.Task() as task:
                   # Add in the two available channels
                   task.ao_channels.add_ao_voltage_chan("Dev1/ao0")
                   task.ao_channels.add_ao_voltage_chan("Dev1/ao1")

                   input = np.array([pid_out, pid_out])

                   # Set the voltage to whatever values are specified in the input array
                   stream_writers.AnalogMultiChannelWriter(
                       task.out_stream, auto_start=True
                   ).write_one_sample(input)

            except:
                pass
        to_send = [Wavelength, Interferometer,exposures,PIDs,Targets]
        # Send the acquired data
        msgLength=f"{len(pickle.dumps(to_send)):<{HEADERLENGTH}}"
        connection.sendall(msgLength.encode())
        connection.sendall(pickle.dumps(to_send))
        exposures[0]=False
        # Specified wait time to allow for multiple clients
        # Without this, opening an additional client causes the initial client program to freeze
        # This time delay could potentially be reduced
        time.sleep(0.5)


# Create a function which will connect to clients and assign these to be managed in individual threads
def accept_connections(ServerSocket,counter):
    global client_updates
    global client_list
    Client, address = ServerSocket.accept()
    print("Connected to: " + address[0] + ":" + str(address[1]))
    client_updates.append(False)
    clientstate=ConnectionState()
    client_list.append(clientstate)
    threading.Thread(target=client_handler, args=(Client,counter)).start()
    # if counter<1:
    #     threading.Thread(target=expTest,args=()).start()


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
class ConnectionState():
    def __init__(self):
        self.update =False
        self.options=8*["Off"]
        self.test =False
client_list=[]
start_server(host, port)
