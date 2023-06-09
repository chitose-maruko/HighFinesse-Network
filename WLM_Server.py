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
#module necessary to output voltage
fpga_dac = XEM3001_AD5676R_DAC.XEM3001_AD5676R_DAC()
#initial voltage offset on DAC output
offset =2.5
#global variable to track whether a calibration is ongoing or not
CAL =False
#global variable for the header of the message
HEADERLENGTH=8
# Load in the DLL provided by HighFinesse
DLL_PATH = "wlmData.dll"
try:
    wlmData.LoadDLL(DLL_PATH)
except:
    sys.exit(
        "Error: Couldn't find DLL on path %s. Please check the DLL_PATH variable!"
        % DLL_PATH
    )
count=0
# Specify the IP address and TCP port which will be used to host the server
#for machine test
host = "192.168.1.30"
port = 5353
#Put the wavemeter in switcher mode
wlmData.dll.SetSwitcherMode(1)

#global variables to be shared among all clients and the server

#the following variable indicates whether user parameters 
# should be initialized to the saved configuration
#if true the user input parameters are set accoridng to the saved configuration of the connected client
#this boolean is used to avoid the overwrite of the user parameters when new client is connected during 
#multi client operation.
initialize=False
#list of user parameters/data shared among clients
# Initialize the wavelength list
Wavelength = 8 * [0]
# Initialize the interferometer list
Interferometer = 8 * [[]]
#Initialize the exposure time list
Exposures=8*[1]
#Initialize the pid value list, the boolean in teh first element indicates whether the PID is engaged in the given channel
PIDs=8*[[False,0,0,0]]
#Initialize the traget wavelengthlist
Targets=8*["___"]
#Initialize the list of active channels
Channels=[8*[False]]

#Initialize the list of parameter update avaialbilities for each client
#in this list the booleans to indicate whether thre is an updates available for the given client
client_updates=[]

# a function which will manage the connection with the client
def client_handler(connection,counter):
    # Loop to continually interact with the client
    global selec_list
    global client_updates
    global Exposures
    global client_dict
    global PIDs
    global Channels
    global Targets
    global initialize
    global CAL
    #a boolean to keep track of whether the chnage to the exposure time is skipped due to calibration
    #(during calibration every function calls on WLM is skipped)
    expoSkipped = False
    #id number for the given client
    client_id = str(counter)
    #initialize list to store the user input according to the given client
    #the first element, which is a boolean, indicates whether there is an update made by the given client
    exposures=[False,Exposures]
    pids =[False,PIDs]
    tgts=[False,Targets]

    #store the socket client object corresponding to the given client to a variable
    client = client_dict[client_id]

    #if the given client is the first client to connect the server,
    #initilize all the user input parameters (exposure, pid, and target wavelength) to 
    #the configuration saved in the given client 
    if counter==0:
        initialize=True

    #loop for communication handling
    while True:
        #initialize the boolean that indicates that the exposure is overwritten by the WLM application
        exp_overwrite =False
        #receive the length of message from the client
        try: 
            length=int(connection.recv(8))
        except:
            break
        #list to store the mesage until the entire message is received
        msg=[]
        while len(B"".join(msg))<length:
            temp=connection.recv(64)
            msg.append(temp)
        #convert the binary encoded message to something readable to us and store the received list
        selec_list = pickle.loads(b"".join(msg))
        #initialize the list of channels used by the given client
        ch_active=[]
        #if initialization is required, flag that the updates are available for all the parameters
        if initialize:
            selec_list[-1]=[True,True,True]
            initialize=False

        for i in range(8):
            #check if the channel is used by the given client
            if selec_list[i][0]!= "Off":
                ch_active.append(i+1)
            #if the channel is not used by the given client nor other clients connected to the server
            #switch the channel off
            elif Channels[0][i]:
                Channels[int(client_id) +1][i]=False
                ch_count =0
                for ch in Channels:
                    if ch[i]:
                        ch_count+=1
                if ch_count<2:
                    wlmData.dll.SetSwitcherSignalStates(i+1, 0, 0)
                    Channels[0][i]=False
            else:
                #store the information about the use of the channels by the given client into the global list
                Channels[int(client_id) +1][i]=False

        for ch in ch_active:
            try:
                #store the information about the use of the channels by the given client into the global list
                Channels[int(client_id) +1][ch-1]=True
                #indicate that the channel is in use
                Channels[0][ch-1]=True
                #if the calibration is no ongoing, turn the signal states on and make measurements
                if not CAL:
                    wlmData.dll.SetSwitcherSignalStates(ch, 1, 1)

                #exposure reading from the wavemeter itself
                if not CAL:
                    expo_read=wlmData.dll.GetExposureNum(ch,1,0) 
                #check whther exposure is changed by WLM application
                if expo_read!=Exposures[ch-1]:
                #if so store the new exposure set by WLM application
                    Exposures[ch-1]=expo_read
                    exp_overwrite=True
                # and indicate that the update is available for all the clients
                    for elm in client_dict:
                        client_dict[elm].updateExpo = True
            except: 
                pass
        #reflect the parameter updates from other client if there is any, but overwrite
        # it if there is newer update from the given client
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

        #set the exposure time according to the avaialble updates
        if selec_list[-1][0] or expoSkipped:
            for ch in ch_active:
            # Set the exposure times accoring to selec_list
                try:
                    if exp_overwrite==False:
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
            #indicate that the parameter is changed by the given client therefore it has to be updated in 
            #the GUI of other clients
            for key in client_dict:
                if key!=client_id:
                    client_dict[key].updateExpo=True
                elif exp_overwrite:
                    client_dict[key].updateExpo=True
                else:
                    client_dict[key].updateExpo=False
        #if thre is an update for the PID parameters store the updates to teh global list
        if selec_list[-1][1]:
            PIDs=selec_list[-2]
            for key in client_dict:
                if key!=client_id:
                    client_dict[key].updatePID=True
                else:
                    client_dict[key].updatePID=False
        #if thre is an update for the target wavelength store the updates to teh global list
        if selec_list[-1][2]:
            Targets=selec_list[-3]
            for key in client_dict:
                if key!=client_id:
                    client_dict[key].updateTgts=True
                else:
                    client_dict[key].updateTgts=False
        
        for ch in ch_active:
            #store the measured wavelength to the list to be sent to the client
            if CAL:
                #if the calibration is ongoing don't measure the wavelength and send the following text
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
    #close the connection if no message is sent from the client side
    connection.close()
    del client_dict[client_id]
    #if there is no more clients left turn off the PID control and pause the measurement
    if len(client_dict)==0:
        wlmData.dll.Operation(wlmConst.cCtrlStopAll)
        PIDs=8*[[False,0,0,0]]
        initialize=True
        #and reset the output value to the initial offset
        for i in range(8):
            output_PID(i+1,offset)
        print("no client connections left. WLM measurements paused")
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

#a function to manage PID controls    
def PID_calc():
    global PIDs
    global Targets
    global offset
    global CAL
    ti = time.perf_counter()
    # initialize the list of the time where the last wavelength measurement is perforrmed (ti) and 
    # the time most recent measurement is made
    tis = 8*[ti]
    tfs=8*[0.0]
    #list to store the previous and most recent error signal for the derivative control calculation
    errors_prev=8*[0]
    errors_current=8*[0]
    #list to store the integral of the error signals
    integrals=8*[0.0]
    #list to store the applied offset
    offsets = 8*[offset]
    #list to store the most recent PID output for each channel. Initialized to offset value
    outputs=offsets
    print("PID operation started")
    while True:
        for i in range(8):
            #if the PID is engaged and calibration is not ongoing, get the most recent wavelength value
            # and calculate the error signal.
            if PIDs[i][0] and not CAL:
                try:
                    #line for the machine run
                    test_wavelength = wlmData.dll.GetWavelengthNum(i+1, 0)
                    if test_wavelength <= 100:
                        print(f"Error code: {test_wavelength}")
                    else:
                        #if there was no error in obtaining the wavelength number, calcualte the error signal
                        errors_current[i] = float(test_wavelength)-float(Targets[i])

                except:
                    pass
                #if the integral gain is set to zero, initialize the integrals 
                if PIDs[i][2]==0:
                    integrals[i]=0
                #if new measurement is available, calculate PID output
                if errors_current[i] !=errors_prev[i]:
                    tfs[i] = time.perf_counter()
                    dt = float(tfs[i]-tis[i])
                    tis[i]=tfs[i]

                    try:
                        integrals[i]+=errors_current[i]*dt
                        derivative = (errors_current[i]-errors_prev[i])/dt
                        pid_out = (float(PIDs[i][1]) * errors_current[i]
                                    + float(PIDs[i][2]) * integrals[i]
                                    + float(PIDs[i][3]) * derivative
                                ) +offsets[i]
                        if pid_out <= 0:
                            pid_out=0
                        elif pid_out >= 5:
                            pid_out=5.0
                        outputs[i]=pid_out
                        errors_prev[i]=errors_current[i]
                    except:
                        print('PID calculation failed')
            elif CAL:
                pass
            else:
                #maintain the last output voltage when the PID is turned off
                offsets[i]= outputs[i]
                integrals[i]=0
        #update the output voltage for each channel with PID engaged output the PID voltage.
        for i in range(8):
            if PIDs[i][0]:
                output_PID(i+1,outputs[i])        
                print(f"Ch {i+1}: {outputs[i]} V")

            
#a function to output voltage from DAC       
def output_PID(ch_num,vol_out):
    try:
        fpga_dac.dac(ch_num, vol_out)
    except:
        print(f"Error in PID channel {ch_num}")


# a function which starts the server
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
    calThread=threading.Thread(target=calibrationHandler,args=())
    calThread.start()
    while True:
        accept_connections(ServerSocket,counter)
        Channels.append(8*[False])
        if counter==0:
            thread_PID=threading.Thread(target=PID_calc, args=())
            thread_PID.daemon=True
            thread_PID.start()
        counter +=1

#function for autocalibration
def autocalibrate():
    global CAL
    HeNeval=632.9915
    CAL=True
    try:
        #pause all measurement before the calibration
        wlmData.dll.SetSwitcherSignalStates(8, 1,1)
        wlmData.dll.Operation(wlmConst.cCtrlStopAll)
        print('measurement paused for calibration')
        calOut=wlmData.dll.Calibration(wlmConst.cHeNe633, wlmConst.cReturnWavelengthVac,HeNeval,8)
        wlmData.dll.Operation(wlmConst.cCtrlStartMeasurement)
        if calOut==0:
            print('calibration completed')
        else:
            print('calibration failed')
        wlmData.dll.SetSwitcherSignalStates(8, 0,0)
    except:
        pass
    CAL=False
# a function that manages the periodic calibration
def calibrationHandler():
    autocalibrate()
    calPeriod = 60*60 #calibration period in seconds
    while True:
        #sleep until the next calibration
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


