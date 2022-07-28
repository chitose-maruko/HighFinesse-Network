# Code to connect to an established server through ethernet
# Resource for the setting up the server: https://codesource.io/creating-python-socket-server-with-multiple-clients/
# Resource for pyqtgraph: https://www.pyqtgraph.org/

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import socket
import time
import threading
import pickle
import sys

# IP address and TCP port of server
host = '192.168.1.56'
port = 5353

# Connect to server, display error if connection fails
ClientSocket = socket.socket()
print('Waiting for connection')
try:
    ClientSocket.connect((host, port))
    print('Connected!')
except socket.error as e:
    print(str(e))

# Set up GUI
app = QtGui.QApplication([])
window = QtGui.QWidget()
window.setWindowTitle('Wavelength Meter')

# Set up basic geometry of the GUI window
window.setGeometry(100, 100, 500, 750)
window.setStyleSheet("background-color: black")

# Create selectable modes for each channel
modes = ['Off', 'Wavelength', 'Interferometer', 'Wvl Difference', 'Both Graphs']

# Initialize the list that will control operation mode and exposure time
# Starting values are Off with 1 ms exposure time
selec_list = 8*[['Off', '1']]

# Create empty lists which will contain data for plotting
wvl_longdata = 8*[[]]
int_data = 8*[[]]

# Create array to store target wavelengths
targets = 8*[0]

# Initialize widgets for...
# Wavelength display
wvl_lbl = 8*[0]
# Operation mode selection
menu_master = 8*[0]
# Target wavelength entry
tgt_master = 8*[0]
# Label for target entry
tgt_lbl = 8*[0]
# Exposure time entry
expo_master = 8*[0]
# Label for exposure time entry
expo_lbl = 8*[0]
# One widget per channel
for i in range(8):
    wvl_lbl[i] = QtGui.QLabel('<h2>Channel ' + f'{i+1}' + '</h2>', parent=window)
    wvl_lbl[i].setStyleSheet('color: white')
    menu_master[i] = QtGui.QComboBox(parent=window)
    menu_master[i].setStyleSheet('color: white')
    menu_master[i].addItems(modes)
    tgt_master[i] = QtGui.QLineEdit(parent=window)
    tgt_master[i].setStyleSheet('color: white')
    tgt_lbl[i] = QtGui.QLabel(f'Ch {i+1} Target Wavelength:', parent=window)
    tgt_lbl[i].setStyleSheet('color: white')
    expo_master[i] = QtGui.QLineEdit(parent=window)
    expo_master[i].setStyleSheet('color: white')
    expo_lbl[i] = QtGui.QLabel(f'Ch {i+1} Exposure Time:', parent=window)
    expo_lbl[i].setStyleSheet('color: white')

# Create the plot for the difference between measured and target wavelength
wvl_plot = pg.PlotWidget(parent=window, data=wvl_longdata)
#Create the plot for the interferometer data
int_plot = pg.PlotWidget(parent=window, data=int_data)

# Format the layout of the application
layout = QtGui.QGridLayout()
window.setLayout(layout)

# Position each of these widgets on the GUI
for i in range(4):
    layout.addWidget(wvl_lbl[i], 0, 2*i)
    layout.addWidget(menu_master[i], 0, 2*i+1)
    layout.addWidget(tgt_master[i], 1, 2*i+1)
    layout.addWidget(tgt_lbl[i], 1, 2*i)
    layout.addWidget(expo_master[i], 2, 2*i+1)
    layout.addWidget(expo_lbl[i], 2, 2*i)
for i in range(4,8):
    layout.addWidget(wvl_lbl[i], 3, 2*i-8)
    layout.addWidget(menu_master[i], 3, 2*i-7)
    layout.addWidget(tgt_master[i], 4, 2*i-7)
    layout.addWidget(tgt_lbl[i], 4, 2*i-8)
    layout.addWidget(expo_master[i], 5, 2*i-7)
    layout.addWidget(expo_lbl[i], 5, 2*i-8)

layout.addWidget(wvl_plot, 6, 4, 3, 4)
layout.addWidget(int_plot, 6, 0, 3, 4)

# The function that manages the connection and updates variable with received data
def update():
    while True:
        # Pickles and sends selction list    
        to_send = pickle.dumps(selec_list)
        ClientSocket.sendall(to_send)
        # Reads in the length of the message to be received
        length = ClientSocket.recv(8).decode()
        # Reads data from server, stores in msg
        msg = []
        while len(b"".join(msg)) < int(length):
            temp = ClientSocket.recv(8192)
            msg.append(temp)
        # Unpickle msg
        data = pickle.loads(b"".join(msg))
        # Store wavelength and interferometer data in separate lists
        wvl_data = data[0]
        int_data = data[1]
        for i in range(8):
            # Update selec_list
            selec_list[i][0] = menu_master[i].currentText()
            selec_list[i][1] = expo_master[i].text()
            # Update labels to display wavelength
            wvl_lbl[i].setText(f'Ch1: {wvl_data[i]} nm')
            # Store entered target wavelengths
            targets[i] = tgt_master[i].text()
            # If the received wavelength data is a number, add it to the array to be plotted
            try:
                diff = float(wvl_data[i]) - float(targets[i])
            except:
                pass
            else:
                wvl_longdata[i].append(diff)
            # Stop wvl_longdata from growing indefinitely
            if len(wvl_longdata[i]) > 30:
                wvl_longdata[i].pop(0)
        if not window.isVisible():
            break

# Start a thread to run the update function
t = threading.Thread(target=update)
t.start() 

# Set the layout
#window.setLayout(layout)
# Run the GUI
window.show()

# Close the entire program and socket once window closes
ClientSocket.close()
sys.exit(app.exec_())
