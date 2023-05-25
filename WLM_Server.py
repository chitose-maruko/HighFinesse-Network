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
import XEM3001_AD5676R_DAC
fpga_dac = XEM3001_AD5676R_DAC.XEM3001_AD5676R_DAC()

offset =2.5
CAL =False
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
count=0
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
initialize=False
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
PIDs=8*[[False,0,0,0]]
Targets=8*["___"]
Channels=[8*[False]]
# # Initialize the combined list which will be sent over the network
# to_send = [Wavelength, Interferometer,Exposures,PIDs,Targets]

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
    global client_dict
    global PIDs
    global Channels
    global Targets
    global initialize
    global CAL
    expoSkipped = False
    client_id = str(counter)
    exposures=[False,Exposures]
    pids =[False,PIDs]
    tgts=[False,Targets]
    client = client_dict[client_id]
    if counter==0:
        initialize=True
    while True:
        exp_overwrite =False
        try: 
            length=int(connection.recv(8))
        except:
            break
        msg=[]
        while len(B"".join(msg))<length:
            temp=connection.recv(64)
            msg.append(temp)
        selec_list = pickle.loads(b"".join(msg))
        ch_active=[]
        if initialize:
            selec_list[-1]=[True,True,True]
            initialize=False

        for i in range(8):
            if selec_list[i][0]!= "Off":
                ch_active.append(i+1)
            elif Channels[0][i]:
                Channels[int(client_id) +1][i]=False
                ch_count =0
                for ch in Channels:
                    if ch[i]:
                        ch_count+=1
                if ch_count<2:
                    # test.SetSwitcherSignalStates(i+1, 0, 0)
                    wlmData.dll.SetSwitcherSignalStates(i+1, 0, 0)
                    Channels[0][i]=False
            else:
                Channels[int(client_id) +1][i]=False

        for ch in ch_active:
            try:
                #test.SetSwitcherSignalStates(ch, 1, 1)
                Channels[int(client_id) +1][ch-1]=True
                Channels[0][ch-1]=True
                if not CAL:
                    wlmData.dll.SetSwitcherSignalStates(ch, 1, 1)

                #exposure reading from the wavemeter itself
                if not CAL:
                    expo_read=wlmData.dll.GetExposureNum(ch,1,0) 
                # expo_read = test.GetExposureNum(ch, 1,0)

                

                if expo_read!=Exposures[ch-1]:
                    Exposures[ch-1]=expo_read
                    exp_overwrite=True
                    for elm in client_dict:
                        client_dict[elm].updateExpo = True
            except: 
                pass
        #reflect the parameter updates from another client if there is any but overwrite
        # it if there is newer update
        if client.updateExpo and (not selec_list[-1][0]):
            exposures[0]=True
            exposures[1]=Exposures
            client.updateExpo=False

        if client.updatePID and (not selec_list[-1][1]):
            pids[0]=True
            pids[1]=PIDs
            client.updatePID=False

        if client.updateTgts and (not selec_list[-1][2]):
            tgts[0]=True
            tgts[1]=Targets

        if selec_list[-1][0] or expoSkipped:
            for ch in ch_active:
            # Set the exposure times accoring to selec_list
                try:
                    if exp_overwrite==False:
                        # #line for local test
                        # test.SetExposureNum(ch, 1, int(selec_list[ch-1][1]))
                        #line for machine test
                        if CAL:
                            expoSkipped =True
                        else:
                            wlmData.dll.SetExposureNum(ch, 1, int(selec_list[ch-1][1]))
                            Exposures[i]=int(selec_list[ch-1][1])                  
                except:
                    pass
                if expoSkipped:
                    expoSkipped=False

            selec_list[-1][0]=False
            for key in client_dict:
                if key!=client_id:
                    client_dict[key].updateExpo=True
                elif exp_overwrite:
                    client_dict[key].updateExpo=True
                else:
                    client_dict[key].updateExpo=False
        if selec_list[-1][1]:
            PIDs=selec_list[-2]
            for key in client_dict:
                if key!=client_id:
                    client_dict[key].updatePID=True
                else:
                    client_dict[key].updatePID=False

        if selec_list[-1][2]:
            Targets=selec_list[-3]
            for key in client_dict:
                if key!=client_id:
                    client_dict[key].updateTgts=True
                else:
                    client_dict[key].updateTgts=False
        
        for ch in ch_active:

            # # Manage sending the wavelength data
            # #line for the local test
            # test_wavelength = test.GetWavelengthNum(ch, 0)
            # Wavelength[ch-1] = f"{test_wavelength}"

            #line for the machine run
            if CAL:
                Wavelength[ch-1]="Calibrating..."
            else:
                test_wavelength = wlmData.dll.GetWavelengthNum(ch, 0)
                if test_wavelength == wlmConst.ErrOutOfRange:
                    Wavelength[ch-1] = "Error: Out of Range"
                elif test_wavelength <= 0:
                    Wavelength[ch-1] = f"Error code: {test_wavelength}"
                else:
                    Wavelength[ch-1] = f"{test_wavelength}"
                # Manage sending the interferometer data
            if (
                    (selec_list[ch-1][0] == "Interferometer"
                    or selec_list[ch-1][0] == "Both Graphs") and not CAL
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
        
        to_send = [Wavelength, Interferometer,exposures,pids,tgts]
        # Send the acquired data
        msgLength=f"{len(pickle.dumps(to_send)):<{HEADERLENGTH}}"
        connection.sendall(msgLength.encode())
        connection.sendall(pickle.dumps(to_send))
        exposures[0]=False
        pids[0]=False
        tgts[0]=False
        # Specified wait time to allow for multiple clients
        # Without this, opening an additional client causes the initial client program to freeze
        # This time delay could potentially be reduced
        time.sleep(0.6)
    connection.close()
    del client_dict[client_id]
    if len(client_dict)==0:
        PIDs=8*[[False,0,0,0]]
        initialize=True
        print("no client connections left")
    print("connection closed")


# Create a function which will connect to clients and assign these to be managed in individual threads
def accept_connections(ServerSocket,counter):
    global client_updates
    global client_dict
    Client, address = ServerSocket.accept()
    print("Connected to: " + address[0] + ":" + str(address[1]))
    client_updates.append(False)
    clientstate=ConnectionState()
    client_dict[str(counter)]=clientstate
    threading.Thread(target=client_handler, args=(Client,counter)).start()
    
def PID_calc():
    global PIDs
    global Targets
    global offset
    global CAL
    ti = time.perf_counter()+0
    tis = 8*[ti]
    tfs=8*[0.0]
    errors_prev=8*[[]]
    errors_current=8*[[]]
    integrals=8*[0.0]
    cts=0
    dtTot=0
    offsets = 8*[offset]
    outputs=8*[0]
    print("PID operation started")
    while True:
        for i in range(8):
            if PIDs[i][0] and not CAL:
                try:
                    #line for the machine run
                    test_wavelength = wlmData.dll.GetWavelengthNum(i+1, 0)
                    if test_wavelength <= 100:
                        print(f"Error code: {test_wavelength}")
                    else:
                        errors_current[i] = float(test_wavelength)-float(Targets[i])

                except:
                    pass
                if PIDs[i][2]==0:
                    integrals[i]=0
                if errors_current !=errors_prev:
                    tfs[i] = time.perf_counter()
                    dt = float(tfs[i]-tis[i])
                    dtTot+=dt
                    cts+=1
                    
                    tis[i]=tfs[i]
                    try:

                        error_now=errors_current[i]
                        error_prev=errors_prev[i]
                        integrals[i]+=error_now*dt
                        derivative = (error_now-error_prev)/dt
                        pid_out = (float(PIDs[i][1]) * error_now
                                    + float(PIDs[i][2]) * integrals[i]
                                    + float(PIDs[i][3]) * derivative
                                ) +offsets[i]
                        
                    except:
                        pass

                try:
                    if pid_out < 4 and pid_out >= 0:
                        output_PID(i+1,pid_out)
                    elif pid_out >= 4:
                        output_PID(i+1,4.0)
                    else:
                        output_PID(i+1,0)
                    #print(f"Ch {i+1}: {selec_list[i][2]:.5f} V")
                    outputs[i]=pid_out
                    
                except:
                    pass
                        #print(f"Error in PID channel {i}")
            else:
                offsets[i]= outputs[i]
                integrals[i]=0
        errors_prev=errors_current
def output_PID(ch_num,vol_out):
    try:
        fpga_dac.dac(ch_num, vol_out)
    except:
        pass


# Lastly, create a function which starts the server
def start_server(host, port):
    for i in range(8):
        output_PID(i+1,offset)
    counter =0
    ServerSocket = socket.socket()
    try:
        ServerSocket.bind((host, port))
    except socket.error as e:
        print(str(e))
    print(f"Server is listening on TCP port {port}...")
    ServerSocket.listen()
    while True:
        calThread=threading.Thread(target=calibrationHandler,args=())
        calThread.start()
        accept_connections(ServerSocket,counter)
        Channels.append(8*[False])
        if counter==0:
            thread_PID=threading.Thread(target=PID_calc, args=())
            thread_PID.daemon=True
            thread_PID.start()
        counter +=1
def autocalibrate():
    global CAL
    HeNeval=632.9915
    CAL=True
    try:
        #pause all measurement before the calibration
        wlmData.dll.Operation(wlmConst.cCtrlStopAll)
        print('measurement paused for calibration')
        calOut=wlmData.dll.Calibrate(wlmConst.cHeNe633, wlmConst.cReturnWavelengthVac,HeNeval,8)
        wlmData.dll.Operation(wlmConst.cCtrlStartMeasurement)
        if calOut==0:
            print('calibration completed')
        else:
            print('calibration failed')
    except:
        pass
    CAL=False
def calibrationHandler():
    autocalibrate()
    calPeriod = 30*60 #calibration period in seconds
    while True:
        time.sleep(calPeriod)
        autocalibrate()
class ConnectionState():
    def __init__(self):
        self.updateExpo =False
        self.updatePID=False
        self.updateTgts=False
        self.options=8*["Off"]
        self.test =False
client_dict={}
start_server(host, port)


