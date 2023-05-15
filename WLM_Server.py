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
#global list to keep track of which channel is in use
#first element (which is also the list) represents the physical statust of the channel
#as clients joins, lists that represents the use of the channel in each client will be concatenated
Channels=[8*[False]]
CAL = False
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
    client_id = str(counter)
    exposures=[False,Exposures]
    pids =[False,PIDs]
    tgts=[False,Targets]
    client = client_dict[client_id]
    if counter==0:
        initialize=True
    while True:
        #initialize the boolean to flag the overwriting exposure value by the Highfinesse application
        exp_overwrite =False
        #receive mesage from the client
        try: 
            selec_list=recv_msg(connection,HEADERLENGTH)
        except:
            break
        #in case when there is no other client is running and this is the first time to loop,
        #reflect all the user input of the given client as the valid selection
        #without the flowwing lines all the clients' user parameter will be set to server default 
        # (which defeats the purpose of loading previous config in client) or the user input is overwritten each time new client joins
        if initialize:
            selec_list[-1]=[True,True,True]
            initialize=False
        
        #check which WLM chennel should be active according to the user input from the client and store the active channel number to the list
        ch_active=check_chs_status(client_id)

        #check if exposure was updated from the Highfinesse application side.
        for ch in ch_active:
            try:
                if not CAL:
                    # test.SetSwitcherSignalStates(ch, 1, 1)
                    wlmData.dll.SetSwitcherSignalStates(ch, 1, 1)
                    #exposure reading from the wavemeter itself
                    expo_read=wlmData.dll.GetExposureNum(ch,1,0) 
                    # expo_read = test.GetExposureNum(ch, 1,0)

                if expo_read!=Exposures[ch-1]:
                    Exposures[ch-1]=expo_read
                    exp_overwrite=True
                    for elm in client_dict:
                        client_dict[elm].updateExpo = True
            except: 
                pass
        #reflect the parameter updates from another client if there is any. but overwrite
        # it if there is newer update
        client.paramupdate(selec_list[-1])
        
        if selec_list[-1][0]==True:
            for ch in ch_active:
            # Set the exposure times accoring to selec_list
                try:
                    if (CAL or exp_overwrite)==False:
                        # # #line for local test
                        # test.SetExposureNum(ch, 1, int(selec_list[ch-1][1]))
                        #line for machine test
                        wlmData.dll.SetExposureNum(ch, 1, int(selec_list[ch-1][1]))
                        Exposures[ch-1]=int(selec_list[ch-1][1])                  
                except:
                    pass

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

           
            if not CAL:
                 # # Manage sending the wavelength data
                # #line for the local test
                # test_wavelength = test.GetWavelengthNum(ch, 0)
                # Wavelength[ch-1] = f"{test_wavelength}"
                
                #line for the machine run
                test_wavelength = wlmData.dll.GetWavelengthNum(ch, 0)
                if test_wavelength == wlmConst.ErrOutOfRange:
                    Wavelength[ch-1] = "Error: Out of Range"
                elif test_wavelength <= 0:
                    Wavelength[ch-1] = f"Error code: {test_wavelength}"
                else:
                    Wavelength[ch-1] = f"{test_wavelength}"
                #Manage sending the interferometer data
                if (
                    selec_list[ch-1][0] == "Interferometer"
                    or selec_list[ch-1][0] == "Both Graphs"
                ):
                    # test.randomPattern(ch)
                    # Interferometer[ch-1]=test.patternList[ch-1]
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
        if not CAL:
            for i in range(8):
                if PIDs[i][0]:
                    try:
                        #line for the machine run
                        test_wavelength = wlmData.dll.GetWavelengthNum(i+1, 0)
                        # #line for local test
                        # test_wavelength=test.GetWavelengthNum(i+1, 0)
                        if test_wavelength <= 100:
                            print(f"Error code: {test_wavelength}")
                        else:
                            errors_current[i] = float(test_wavelength)-float(Targets[i])

                    except:
                        pass
                    if PIDs[i][2]==0:
                        integrals[i]=0
                    
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
                        if pid_out < 4 and pid_out > -0.0285:
                            output_PID(i+1,pid_out)
                        elif pid_out >= 4:
                            output_PID(i+1,4.0)
                        else:
                            output_PID(i+1,-0.0285)
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
    global offset
    for i in range(8):
        #line for local test
        pass
        #comment out for machine test
        # output_PID(i+1,offset)
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
        Channels.append(8*[False])
        if counter==0:
            output_PID(offset)
            thread_PID=threading.Thread(target=PID_calc, args=())
            thread_PID.daemon=True
            thread_PID.start()
        counter +=1
class ConnectionState():
    def __init__(self):
        self.updateExpo =False
        self.updatePID=False
        self.updateTgts=False
        self.options=8*["Off"]
        self.exposures=[False,Exposures]
        self.pids=[False,PIDs]
        self.tgts=[False,Targets]
    def paramUpdate(self,updList):
        #reflect the parameter updates from another client if there is any. but overwrite
        # it if there is newer update
        if self.updateExpo and (not updList[0]):
            self.exposures[0]=True
            self.exposures[1]=Exposures
            self.updateExpo=False

        if self.updatePID and (not updList[0]):
            self.pids[0]=True
            self.pids[1]=PIDs
            self.updatePID=False

        if self.updateTgts and (not updList[0]):
            self.tgts[0]=True
            self.tgts[1]=Targets
client_dict={}
start_server(host, port)

def calibrate():
    global CAL
    CAL=True
    try:
                    #pause all measurement before the calibration
                    wlmData.dll.Operation(wlmConst.cCtrlStopAll)
                    wlmData.dll.Calibrate(wlmConst.cHeNe633, wlmConst.cReturnWavelengthVac,632.99,8)
                    wlmData.dll.Operation(wlmConst.cCtrlStartMeasurement)
    except:
        pass
    CAL =False
def calibrationHandler():
    calPeriod=60 #calibration period in seconds
    calibrate()
    while True:
        time.sleep(calPeriod)

def recv_msg(conn,len_head):
# a function to manage receiving message from clients. 
# First element has to be a socket.client object of the given connection the client handler is handling.
#the second argument is an integer which represents the predetermined header length for sending just the data size.

#receive an information about the data size
    length=int(conn.recv(len_head))
#initialize the bin to store the received data
    msg=[]
#loop to concatenate the received data
#it is a good practive to keep the data size of each communication to a small number to prevent a packet loss
    while len(B"".join(msg))<length:
        #a variable to temporalily store the received data
        temp=conn.recv(128)
        #concatenate the received data in the bin
        msg.append(temp)
    #conver the data in binary format to normal list and return the value
    return  pickle.loads(b"".join(msg))

def check_chs_status(id):
    global Channels
    #check which WLM chennel should be active according to the user input from the client and store the active channel number to the list
    active=[]
    for i in range(8):
        if selec_list[i][0]!= "Off":
            active.append(i+1)
            #record that the given chennel is used by the given client
            Channels[int(id) +1][ch-1]=True
            #record that the given chnnel is used by at least one client
            Channels[0][ch-1]=True
        else:
            Channels[int(id) +1][i]=False

        if Channels[0][i]:
            #record that the given chennel is used by the given client
            ch_count =0
            #check whether other clients are using the given channel
            for ch in Channels:
                if ch[i]:
                    ch_count+=1
            #if no client is using the given chennel, turn it off
            if ch_count<2:
                wlmData.dll.SetSwitcherSignalStates(i+1, 0, 0)
                Channels[0][i]=False
    return active