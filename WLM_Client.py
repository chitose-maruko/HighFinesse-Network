# Code to connect to an established server through ethernet
# Based on code found here: https://codesource.io/creating-python-socket-server-with-multiple-clients/

import socket
import time
import tkinter as tk
from tkinter import ttk
import threading
import pickle

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
# Resource for GUI code found here: https://realpython.com/python-gui-tkinter/#making-your-applications-interactive
window = tk.Tk()
window.title('Wavelength Meter')

# Initialize list which selects which channel to turn on
selec_list = [0, 0, 0, 0, 0, 0, 0, 0]
# and list which will contain the received data
data = ['---', '---', '---', '---', '---', '---', '---', '---',]

# Set up basic geometry of the GUI window
window.geometry("1600x800")
window.rowconfigure([0,1,2,3,4,5], minsize=50, weight=1)
window.columnconfigure([0,1,2,3,4,5,6,7], minsize=200, weight=1)

# This function allows for constant updating of the GUI
def thread():
    # Create thread to tie to the 'start' button
    t = threading.Thread(target=update)
    t.start()    
                
def Ch(n):
    global selec_list
    selec_list[n] = not selec_list[n]
    
# Create and position all eight buttons with respective labels 
lbl_1 = tk.Label(master=window, text="Channel 1", borderwidth=2, relief="solid")
lbl_1.grid(row=0, column=0, columnspan=2, sticky="nsew")
lbl_2 = tk.Label(master=window, text="Channel 2", borderwidth=2, relief="solid")
lbl_2.grid(row=0, column=2, columnspan=2, sticky="nsew")
lbl_3 = tk.Label(master=window, text="Channel 3", borderwidth=2, relief="solid")
lbl_3.grid(row=0, column=4, columnspan=2, sticky="nsew")
lbl_4 = tk.Label(master=window, text="Channel 4", borderwidth=2, relief="solid")
lbl_4.grid(row=0, column=6, columnspan=2, sticky="nsew")
lbl_5 = tk.Label(master=window, text="Channel 5", borderwidth=2, relief="solid")
lbl_5.grid(row=2, column=0, columnspan=2, sticky="nsew")
lbl_6 = tk.Label(master=window, text="Channel 6", borderwidth=2, relief="solid")
lbl_6.grid(row=2, column=2, columnspan=2, sticky="nsew")
lbl_7 = tk.Label(master=window, text="Channel 7", borderwidth=2, relief="solid")
lbl_7.grid(row=2, column=4, columnspan=2, sticky="nsew")
lbl_C = tk.Label(master=window, text="Channel C", borderwidth=2, relief="solid")
lbl_C.grid(row=2, column=6, columnspan=2, sticky="nsew")
lbl_master = [lbl_1, lbl_2, lbl_3, lbl_4, lbl_5, lbl_6, lbl_7, lbl_C]

btn_1 = tk.Checkbutton(master=window, text='1', command = lambda : Ch(0)).grid(row=1, column=1, sticky="e")
btn_2 = tk.Checkbutton(master=window, text='2', command = lambda : Ch(1)).grid(row=1, column=3, sticky="e")
btn_3 = tk.Checkbutton(master=window, text='3', command = lambda : Ch(2)).grid(row=1, column=5, sticky="e")
btn_4 = tk.Checkbutton(master=window, text='4', command = lambda : Ch(3)).grid(row=1, column=7, sticky="e")
btn_5 = tk.Checkbutton(master=window, text='5', command = lambda : Ch(4)).grid(row=3, column=1, sticky="e")
btn_6 = tk.Checkbutton(master=window, text='6', command = lambda : Ch(5)).grid(row=3, column=3, sticky="e")
btn_7 = tk.Checkbutton(master=window, text='7', command = lambda : Ch(6)).grid(row=3, column=5, sticky="e")
btn_C = tk.Checkbutton(master=window, text='C', command = lambda : Ch(7)).grid(row=3, column=7, sticky="e")

# This function reads and displays the wavelength in the correct place    
def update():
    global selec_list, data, lbl_master
    while True:
        time.sleep(0.25)
        # Pickles and sends selection list
        to_send = pickle.dumps(selec_list)
        ClientSocket.sendall(to_send)
        for i in range(8):
            lbl_master[i]['text'] = data[i]
        # Reads data from server, stores in list
        msg = ClientSocket.recv(1024)
        data = pickle.loads(msg)

btn_start = tk.Button(master=window, text='start', command=thread)
btn_start.grid(row=4, column=6, columnspan=2, rowspan=2, sticky="nsew")       

# Run the GUI
window.mainloop()
# Closing the GUI returns an error "main thread is not in main loop"
# This does not seem to affect the utility of the program and is a result of how the threading is set up,
# but it should probably be fixed in the future
