#!/usr/bin/env python3

# Code to connect to an established server through ethernet
import pyqtgraph as pg
import socket
import pickle
import sys
import time

from os import path
from pyqtgraph.Qt import QtCore, QtGui

# Configs file location
FILE_DIR = path.dirname(path.abspath(__file__))
CONFIGS_FILE = path.join(FILE_DIR, "configs.ini")

# IP address and TCP port of server
HOST = "192.168.1.56"
PORT = 5353

# Connect to server, display error if connection fails
ClientSocket = socket.socket()
print("Waiting for connection")
try:
    ClientSocket.connect((HOST, PORT))
    print("Connected!")
except socket.error as e:
    print(str(e))

# Define global variable which will store the desired mode, selected exposure time of each channel,
# and the PID output for each channel
# Starting values are Off with 1 ms exposure time and 0.0 for PID output
selec_list = [
    ["Off", "1", None],
    ["Off", "1", None],
    ["Off", "1", None],
    ["Off", "1", None],
    ["Off", "1", None],
    ["Off", "1", None],
    ["Off", "1", None],
    ["Off", "1", None],
]

# Define another global variable to hold the target wavelengths, initialized to 0
targets = [0, 0, 0, 0, 0, 0, 0, 0]

# Define another global variable to contain PID control values
PID_val = 8 * [[False, 0.0, 0.0, 0.0]]

# This class contains the function which will run in a thread separate from the GUI
# and manages the server connection
class Transmission(QtCore.QObject):
    # Create signal to send the data for plotting
    data = QtCore.pyqtSignal(list)

    # The function that manages the connection and updates variable with received data
    def update(self):
        # Create list to store the wavelength error data for plotting
        wvl_error = [[], [], [], [], [], [], [], []]

        # Initialize integral for PID to zero
        integral = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        while True:
            # Initial time measurement
            ti = time.perf_counter()

            # Pickles and sends selection list
            to_send = pickle.dumps(selec_list)
            ClientSocket.sendall(to_send)
            # Reads in the length of the message to be received
            length = ClientSocket.recv(8).decode()

            msg = []
            # Reads data sent from the host, stores in msg until full message is received
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
                if selec_list[i][0] == "Wvl Error" or selec_list[i][0] == "Both Graphs":
                    try:
                        diff = float(wvl_data[i]) - float(targets[i])
                    except:
                        if len(wvl_error[i]) > 1:
                            wvl_error[i].append(wvl_error[i][-1])
                        elif len(wvl_error[i]) <= 1:
                            pass
                    else:
                        wvl_error[i].append(diff)

                    # Stop wvl_longdata from growing indefinitely
                    if len(wvl_error[i]) > 30:
                        wvl_error[i].pop(0)

            # Time interval for PID
            dt = time.perf_counter() - ti

            # Calculate the PID function output
            for i in range(8):
                if PID_val[i][0] == True:
                    try:
                        integral[i] += wvl_error[i][-1] * dt
                        derivative = (wvl_error[i][-1] - wvl_error[i][-2]) / dt
                        pid_out = (
                            float(PID_val[i][1]) * wvl_error[i][-1]
                            + float(PID_val[i][2]) * integral[i]
                            + float(PID_val[i][3]) * derivative
                        )

                        # If statements prevent voltage range in Toptica rack from being exceeded
                        if pid_out < 4 and pid_out > -0.0285:
                            selec_list[i][2] = pid_out
                        if pid_out >= 4:
                            selec_list[i][2] = 4.0
                        if pid_out <= -0.0285:
                            selec_list[i][2] = -0.0285
                        print(f"Ch {i+1}: {selec_list[i][2]:.5f} V")
                    except:
                        print(f"Error in PID channel {i}")

                # Don't compute PID if box not checked
                elif PID_val[i] == False:
                    selec_list[i][2] = None

            # Send the data that has just been stored to another function for further operation
            self.data.emit([int_data, wvl_error, wvl_data])


# This class sets up and runs the GUI, while using the Transmission class in a separate thread
# to interact with the server
class Window(QtGui.QWidget):
    # Create selectable modes for each channel
    modes = ["Off", "Pause Graphs", "Interferometer", "Wvl Error", "Both Graphs"]

    # A list of RGB color codes to differentiate channels
    color = [
        (255, 160, 122),
        (238, 232, 170),
        (152, 251, 152),
        (72, 209, 204),
        (186, 85, 211),
        (255, 192, 203),
        (188, 143, 143),
        (220, 20, 60),
    ]

    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        self.setWindowTitle("Wavelength Meter")
        self.setGeometry(100, 100, 500, 750)
        self.setStyleSheet("background-color: black")
        self.settings = QtCore.QSettings(CONFIGS_FILE, QtCore.QSettings.IniFormat)

        # Initialize widgets for...
        # Wavelength display
        self.wvl_lbl = 8 * [0]
        # Operation mode selection menu
        self.menu_master = 8 * [0]
        # Target wavelength entry
        self.tgt_master = 8 * [0]
        # Label for target entry
        tgt_lbl = 8 * [0]
        # Exposure time entry
        self.expo_master = 8 * [0]
        # Label for exposure time entry
        expo_lbl = 8 * [0]
        # PID enable/disable
        self.pid_master = 8 * [0]
        # Label for PID enable/disable
        pid_lbl = 8 * [0]
        # Entry boxes for the PID parameters
        self.P = 8 * [0]
        self.I = 8 * [0]
        self.D = 8 * [0]
        # Labels for the PID parameters
        P_lbl = 8 * [0]
        I_lbl = 8 * [0]
        D_lbl = 8 * [0]

        # Loop over channels to create the different labels, entry boxes, and such
        for i in range(8):
            self.wvl_lbl[i] = QtGui.QLabel(
                "<h4>Channel " + f"{i+1}" + "</h4>", parent=self
            )
            self.wvl_lbl[i].setStyleSheet(f"color: rgb{self.color[i]}")
            self.wvl_lbl[i].setFixedWidth(225)
            self.menu_master[i] = QtGui.QComboBox(parent=self)
            self.menu_master[i].setStyleSheet("color: white")
            self.menu_master[i].addItems(self.modes)

            self.tgt_master[i] = QtGui.QLineEdit(parent=self)
            self.tgt_master[i].setStyleSheet("color: white")
            tgt_lbl[i] = QtGui.QLabel(f"Ch {i+1} Target Wavelength (nm):", parent=self)
            tgt_lbl[i].setStyleSheet("color: white")

            self.expo_master[i] = QtGui.QLineEdit(parent=self)
            self.expo_master[i].setText(selec_list[i][1])
            self.expo_master[i].setStyleSheet("color: white")
            expo_lbl[i] = QtGui.QLabel(f"Ch {i+1} Exposure Time (ms):", parent=self)
            expo_lbl[i].setStyleSheet("color: white")

            self.pid_master[i] = QtGui.QCheckBox(parent=self)
            self.pid_master[i].setStyleSheet("color: black;" "background-color: grey;")
            pid_lbl[i] = QtGui.QLabel("Engage PID:")
            pid_lbl[i].setStyleSheet("color: white")

            self.P[i] = QtGui.QLineEdit(parent=self)
            self.P[i].setStyleSheet("color: white")
            self.I[i] = QtGui.QLineEdit(parent=self)
            self.I[i].setStyleSheet("color: white")
            self.D[i] = QtGui.QLineEdit(parent=self)
            self.D[i].setStyleSheet("color: white")
            P_lbl[i] = QtGui.QLabel("P:")
            P_lbl[i].setStyleSheet("color: white")
            I_lbl[i] = QtGui.QLabel("I:")
            I_lbl[i].setStyleSheet("color: white")
            D_lbl[i] = QtGui.QLabel("D:")
            D_lbl[i].setStyleSheet("color: white")

        # Create the widgets for plotting
        # Wavelength Error plot
        self.wvl = pg.PlotWidget(parent=self)
        self.wvl.setTitle("Wavelength Error")
        self.wvl.addLegend()
        self.wvl.setLabel("left", "nm")
        # Interferometer plot
        self.inter = pg.PlotWidget(parent=self)
        self.inter.setTitle("Interferometer")
        self.inter.addLegend()

        # Format the layout of the application
        layout = QtGui.QGridLayout()
        self.setLayout(layout)

        # Position each of these widgets on the GUI
        for i in range(4):
            layout.addWidget(self.wvl_lbl[i], 0, 8 * i, 1, 4)
            layout.addWidget(self.menu_master[i], 0, 8 * i + 4, 1, 4)
            layout.addWidget(self.tgt_master[i], 1, 8 * i + 4, 1, 4)
            layout.addWidget(tgt_lbl[i], 1, 8 * i, 1, 4)
            layout.addWidget(self.expo_master[i], 2, 8 * i + 4, 1, 4)
            layout.addWidget(expo_lbl[i], 2, 8 * i, 1, 4)
            layout.addWidget(self.pid_master[i], 3, 8 * i + 1)
            layout.addWidget(pid_lbl[i], 3, 8 * i)
            layout.addWidget(self.P[i], 3, 8 * i + 3)
            layout.addWidget(self.I[i], 3, 8 * i + 5)
            layout.addWidget(self.D[i], 3, 8 * i + 7)
            layout.addWidget(P_lbl[i], 3, 8 * i + 2)
            layout.addWidget(I_lbl[i], 3, 8 * i + 4)
            layout.addWidget(D_lbl[i], 3, 8 * i + 6)
        for i in range(4, 8):
            layout.addWidget(self.wvl_lbl[i], 4, 8 * i - 32, 1, 4)
            layout.addWidget(self.menu_master[i], 4, 8 * i - 28, 1, 4)
            layout.addWidget(self.tgt_master[i], 5, 8 * i - 28, 1, 4)
            layout.addWidget(tgt_lbl[i], 5, 8 * i - 32, 1, 4)
            layout.addWidget(self.expo_master[i], 6, 8 * i - 28, 1, 4)
            layout.addWidget(expo_lbl[i], 6, 8 * i - 32, 1, 4)
            layout.addWidget(self.pid_master[i], 7, 8 * i - 31)
            layout.addWidget(pid_lbl[i], 7, 8 * i - 32)
            layout.addWidget(self.P[i], 7, 8 * i - 29)
            layout.addWidget(self.I[i], 7, 8 * i - 27)
            layout.addWidget(self.D[i], 7, 8 * i - 25)
            layout.addWidget(P_lbl[i], 7, 8 * i - 30)
            layout.addWidget(I_lbl[i], 7, 8 * i - 28)
            layout.addWidget(D_lbl[i], 7, 8 * i - 26)

        layout.addWidget(self.wvl, 8, 16, 3, 16)
        layout.addWidget(self.inter, 8, 0, 3, 16)

        # load saved configs
        self.load_configs()

        # Run the function, defined later in this code, which starts the thread for the Transmission class
        self.worker_thread()

    # This function updates the GUI with data received from the server
    # It also calculates the PID function
    def gui_update(self, data):
        # Clear the plots whenever new data is received
        self.wvl.clear()
        self.inter.clear()

        for i in range(8):
            # Use the channel labels to display current wavelength (only up to 6 decimal points)
            try:
                float(data[2][i])
                self.wvl_lbl[i].setText("<h4>Ch " + f"{i+1}: {data[2][i]:.10} nm </h4>")
            except:
                self.wvl_lbl[i].setText("<h4>Ch " + f"{i+1}: {data[2][i]} nm </h4>")

            # Update global lists with user entered information
            selec_list[i][0] = self.menu_master[i].currentText()
            selec_list[i][1] = self.expo_master[i].text()
            targets[i] = self.tgt_master[i].text()
            PID_val[i] = [
                self.pid_master[i].isChecked(),
                self.P[i].text(),
                self.I[i].text(),
                self.D[i].text(),
            ]

            # Plot according to user requests
            if selec_list[i][0] != "Off":
                try:
                    # Plot circles if the error data is not updating
                    if data[1][i][-1] == data[1][i][-2]:
                        self.wvl.plot(
                            data[1][i], name=f"Ch{i+1}", pen=self.color[i], symbol="o"
                        )
                    else:
                        self.wvl.plot(data[1][i], name=f"Ch{i+1}", pen=self.color[i])
                except:
                    pass
                try:
                    self.inter.plot(data[0][i], name=f"Ch{i+1}", pen=self.color[i])
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

    def closeEvent(self, event):
        self.save_configs()

        return super().closeEvent(event)

    def load_configs(self):
        for i in range(8):
            if str(i) in self.settings.childGroups():
                self.settings.beginGroup(str(i))
                self.menu_master[i].setCurrentIndex(int(self.settings.value("menu")))
                self.tgt_master[i].setText(self.settings.value("target_wvl"))
                self.expo_master[i].setText(self.settings.value("exposure"))
                self.pid_master[i].setCheckState(int(self.settings.value("PID_state")))
                self.P[i].setText(self.settings.value("P"))
                self.I[i].setText(self.settings.value("I"))
                self.D[i].setText(self.settings.value("D"))
                self.settings.endGroup()

    def save_configs(self):
        for i in range(8):
            self.settings.beginGroup(str(i))
            self.settings.setValue("menu", self.menu_master[i].currentIndex())
            self.settings.setValue("target_wvl", self.tgt_master[i].text())
            self.settings.setValue("exposure", self.expo_master[i].text())
            self.settings.setValue("PID_state", self.pid_master[i].checkState())
            self.settings.setValue("P", self.P[i].text())
            self.settings.setValue("I", self.I[i].text())
            self.settings.setValue("D", self.D[i].text())
            self.settings.endGroup()
        # forced synchronization
        self.settings.sync()


# Set up and run GUI
app = QtGui.QApplication([])
window = Window()
window.show()
sys.exit(app.exec_())
