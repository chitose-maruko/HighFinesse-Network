# Code to connect to an established server through ethernet

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import socket
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

# Define global variable which will store the desired mode and exposure time of each channel
# Starting values are Off with 1 ms exposure time
selec_list = [['Off', '1'], ['Off', '1'], ['Off', '1'], ['Off', '1'], ['Off', '1'], ['Off', '1'], ['Off', '1'], ['Off', '1']]

# Define another global variable to hold the target wavelengths, initialized to 0
targets = [0, 0, 0, 0, 0, 0, 0, 0]

# This class contains the function which will run in a thread separate from the GUI
# and manages the server connection
class Transmission(QtCore.QObject):
    # Create signal to send the data for plotting
    data = QtCore.pyqtSignal(list)
    
    # The function that manages the connection and updates variable with received data
    def update(self):
        # Create list to store the wavelength-target difference data for plotting
        wvl_difference = [[], [], [], [], [], [], [], []]
    
        while True:
            # Pickles and sends selection list    
            to_send = pickle.dumps(selec_list)
            ClientSocket.sendall(to_send)
            # Reads in the length of the message to be received
            length = ClientSocket.recv(8).decode()
            
            msg = []
	    # Reads data sent from the host, stores in msg
            while len(b"".join(msg)) < int(length):
                temp = ClientSocket.recv(8192)
                msg.append(temp)
            # Unpickle msg
            data = pickle.loads(b"".join(msg))

            # Store wavelength and interferometer data in separate lists
            wvl_data = data[0]
            int_data = data[1]

	    # Conditionally calculate the difference between measured and target wavelength
            for i in range(8):
                if selec_list[i][0] == 'Wvl Difference' or selec_list[i][0] == 'Both Graphs':
                    try:
                        diff = float(wvl_data[i]) - float(targets[i])
                    except: 
                        pass
                    else:
                        wvl_difference[i].append(diff)
                    # Stop wvl_longdata from growing indefinitely
                    if len(wvl_difference[i]) > 30:
                        wvl_difference[i].pop(0)
                else:
                    pass
            # Send the data that has just been stored to another function for further operation        
            self.data.emit([int_data, wvl_difference, wvl_data])

	
# This class sets up and runs the GUI, while using the Transmission class in a separate thread
# to interact with the server
class Window(QtGui.QWidget):
    # Create selectable modes for each channel
    modes = ['Off', 'Pause Graphs', 'Interferometer', 'Wvl Difference', 'Both Graphs']
    
    # A list of RGB color codes to differentiate channels
    color = [(255,160,122),(238,232,170),(152,251,152),(72,209,204),(186,85,211),(255,192,203),(188,143,143),(220,20,60)]
    
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)
        
        self.setWindowTitle('Wavelength Meter')
        self.setGeometry(100, 100, 500, 750)
        self.setStyleSheet("background-color: black")
	
        # Initialize widgets for...
        # Wavelength display
        self.wvl_lbl = 8*[0]
        # Operation mode selection menu
        self.menu_master = 8*[0]
        # Target wavelength entry
        self.tgt_master = 8*[0]
        # Label for target entry
        tgt_lbl = 8*[0]
        # Exposure time entry
        self.expo_master = 8*[0]
        # Label for exposure time entry
        expo_lbl = 8*[0]
	
        # Loop over channels
        for i in range(8):
            self.wvl_lbl[i] = QtGui.QLabel('<h4>Channel ' + f'{i+1}' + '</h4>', parent=self)
            self.wvl_lbl[i].setStyleSheet(f'color: rgb{self.color[i]}')
            self.wvl_lbl[i].setFixedWidth(225)
            self.menu_master[i] = QtGui.QComboBox(parent=self)
            self.menu_master[i].setStyleSheet('color: white')
            self.menu_master[i].addItems(self.modes)
            self.tgt_master[i] = QtGui.QLineEdit(parent=self)
            self.tgt_master[i].setStyleSheet('color: white')
            tgt_lbl[i] = QtGui.QLabel(f'Ch {i+1} Target Wavelength (nm):', parent=self)
            tgt_lbl[i].setStyleSheet('color: white')
            self.expo_master[i] = QtGui.QLineEdit(parent=self)
            self.expo_master[i].setText(selec_list[i][1])
            self.expo_master[i].setStyleSheet('color: white')
            expo_lbl[i] = QtGui.QLabel(f'Ch {i+1} Exposure Time (ms):', parent=self)
            expo_lbl[i].setStyleSheet('color: white')

        # Create the widgets for plotting
	# Wavelength Difference plot
        self.wvl = pg.PlotWidget(parent=self)
        self.wvl.setTitle('Wavelength Difference')
        self.wvl.addLegend()
        self.wvl.showAxis('bottom', False)
        self.wvl.setLabel('left', 'nm')
	# Interferometer plot
        self.inter = pg.PlotWidget(parent=self)
        self.inter.setTitle('Interferometer')
        self.inter.addLegend()
                                            
        # Format the layout of the application
        layout = QtGui.QGridLayout()
        self.setLayout(layout)
	
        # Position each of these widgets on the GUI
        for i in range(4):
            layout.addWidget(self.wvl_lbl[i], 0, 2*i)
            layout.addWidget(self.menu_master[i], 0, 2*i+1)
            layout.addWidget(self.tgt_master[i], 1, 2*i+1)
            layout.addWidget(tgt_lbl[i], 1, 2*i)
            layout.addWidget(self.expo_master[i], 2, 2*i+1)
            layout.addWidget(expo_lbl[i], 2, 2*i)
        for i in range(4,8):
            layout.addWidget(self.wvl_lbl[i], 3, 2*i-8)
            layout.addWidget(self.menu_master[i], 3, 2*i-7)
            layout.addWidget(self.tgt_master[i], 4, 2*i-7)
            layout.addWidget(tgt_lbl[i], 4, 2*i-8)
            layout.addWidget(self.expo_master[i], 5, 2*i-7)
            layout.addWidget(expo_lbl[i], 5, 2*i-8)

        layout.addWidget(self.wvl, 6, 4, 3, 4)
        layout.addWidget(self.inter, 6, 0, 3, 4)
        
	# Run the function, defined later in this code, which starts the thread for the Transmission class
        self.worker_thread()
           
    # This function updates the GUI with data received from the server
    def gui_update(self, data):
        # Clear the plots whenever new data is received
        self.wvl.clear()
        self.inter.clear() 
	
        for i in range(8):
	    # Use the channel labels to display current wavelength
            self.wvl_lbl[i].setText('<h4>Ch '+f'{i+1}: {data[2][i]} nm </h4>')

            # Update global lists with user entered information
            selec_list[i][0] = self.menu_master[i].currentText()
            selec_list[i][1] = self.expo_master[i].text()
            targets[i] = self.tgt_master[i].text()

	    # Plot according to user requests
            if selec_list[i][0] != 'Off':
                try:
                    self.wvl.plot(data[1][i], name=f'Ch{i+1}', pen=self.color[i])
                except:
                    pass
                try:
                    self.inter.plot(data[0][i], name=f'Ch{i+1}', pen=self.color[i])
                except:
                    pass
	
    # This functions runs the transmission class in another thread       
    def worker_thread(self):
        self.thread = QtCore.QThread()
        self.worker = Transmission()
	# Tie transmission class to the new thread
        self.worker.moveToThread(self.thread)
	# Once the thread starts, run the update function in Transmission
        self.thread.started.connect(self.worker.update)
	# Connect the data emitted from Transmission to the gui_update function
        self.worker.data.connect(self.gui_update)
        self.thread.start()
        

# Set up and run GUI
app = QtGui.QApplication([])
window = Window()
window.show()
sys.exit(app.exec_())
