# EQuIP-HighFinesse-Network
This project was set up within the EQuIP Unit at OIST. The goal is to allow workers in the lab to use the HighFinesse wavemeter for wavelength locking on any computer connected to the local network, rather than just the computer directly connected to the wavemeter. The files are all written for Python 3. 

## Manual.pdf
This file saved is the user's manual for the wavemeter this project was initially designed for (WS 8 model), which also contains useful information on the functions provided by HighFinesse which allow for interaction with the wavemeter. 

## WLM_Server.py
This file hosts the server and also manages all of the interactions with the wavemeter and NI-DAQ directly. Variables/functions from wlmData or wlmConst are provided by HighFinesse, so questions as to how those work should be looked up in the Manual.pdf file.
The IP address and TCP port which are used for hosting the server are stored near the top of the code, so if either of those needs to be changed it should be easy to modify. This file contains three connected functions, for the three purposes of hosting the server, threading client connections, and managing the wavemeter/client connection. There is a time.sleep command in the function client_handler which dictates how quickly the server operates, so this can be adjusted as needed. However, the time delay does seem to be necessary for multi-client operation.

## WLM_Client.py
This file connects to the server that has been started on another computer by running WLM_Server.py. Additionally, it runs a GUI that is used to interact with the wavemeter via the established server. Multiple instances of this program running on different computers should be able to connect to the same server at the same time. The capabilities of this GUI are currently: to turn on/off wavelength readout of any of the eight wavemeter channels, to change the exposure time of any of these eight channels, to enter a target wavelength for each channel individually, to plot the interferometer data, and to plot the difference between the measured wavelength and the target wavelength. There are thus five different selectable operation modes for each channel: 'Off', 'Pause Graphs', 'Interferometer', 'Wvl Difference', and 'Both Graphs'. 'Off' leads to no output whatsoever, 'Pause Graphs' will pause any running graphs and only update the wavelength, 'Interferometer' and 'Wvl Difference' allow the interferometer and wavelength difference graphs to update in real time, respectively, and 'Both Graphs' allows both graphs to update in real time.

# Requirements

## WLM_Server.py
This program must be run on a computer which is connected via USB to the wavemeter and NI-DAQ (the NI-DAQ will likely be replaced with a different analog output device in the future). It also requires the software from HighFinesse to be downloaded, which can be found on the unit's SharePoint. Once this software is downloaded, importing wlmData, wlmConst, and loading in the wlmData.dll file should work fine, as these are all included in the file in SharePoint. This file imports the Python librairies socket, time, threading, time, sys, pickle, nidaqmx, and numpy, so ensure the correct version of those is available on the computer.  Using pyqtgraph may also require the user to install PyQt5.

## WLM_Client.py
This program should not be directly connected to the wavemeter and does not need to have anything from HighFinesse downloaded. It uses the Python librairies pyqtgraph, socket, pickle, and sys, so compatible versions of these should be downloaded to run the code. 

# Basic Troubleshooting

## WLM_Server.py
If this file has the wrong path for wlmData.dll, it will let you know. Just find this file on the compute (it should have been downloaded with the HighFinesse software) and update the path accordingly.<br>
Any problems with wlmData functions can be best answered by consulting the wavemeter manual.

## WLM_Client.py
If this file prints 'Waiting for connection' and never prints 'Connected!', there is some issue with the network connection. Things to check: ensure WLM_Server.py is running (it will say 'Server is listening on TCP Port:'), ensure the computer running WLM_Server.py is connected to the same network as the on running WLM_Client.py, and ensure the IP and TCP variables in WLM_Client.py match those in WLM_Server.py. 

# Resources
Shows socket library in a similar context: https://codesource.io/creating-python-socket-server-with-multiple-clients/ <br>
Important to note that this socket demonstration uses _thread while we use threading
pyqtgraph library documentation: https://www.pyqtgraph.org/ <br>
Shows QThread in a similar context: https://realpython.com/python-pyqt-qthread/#freezing-a-gui-with-long-running-tasks <br>
The documentation for nidaqmx is sparse but can be found here: https://nidaqmx-python.readthedocs.io/en/latest/
