# Code to connect to an established server through ethernet
# Resource for the setting up the server: https://codesource.io/creating-python-socket-server-with-multiple-clients/

import socket
import time
import tkinter as tk
import threading
import pickle
import sys
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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
# and list which will contain plottable data
plottable = [[], [], [], [], [], [], [], []]
# and list which will contain target wavelengths
targets = 8*[0]

# Set up basic geometry of the GUI window
window.geometry("1600x800")
window.rowconfigure([0,1,2,3,4,5,6,7,8,9,10,11], minsize=50, weight=1)
window.columnconfigure([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15], minsize=50, weight=1)

# Change application color
window.configure(bg='white')

# This function allows for constant updating of the GUI
def start():
    global t
    t = threading.Thread(target=update)
    t.start()    

# This function stops the GUI from updating and then closes it
end = False
def stop():
    global end, ClientSocket, window
    end = True

# A function to be tied to each check box, merely allows channels to be turned on and off                
def Ch(n):
    global selec_list
    selec_list[n] = not selec_list[n]
    
# Create labels to display wavelength output
lbl_master = 8*[0]
for i in range(8):
    lbl_master[i] = tk.Label(master=window, text=f'Channel {i+1}', borderwidth=2, relief="solid", bg='white')
    
# Position the labels
lbl_master[0].grid(row=0, rowspan=2, column=0, columnspan=4, sticky="nsew")
lbl_master[1].grid(row=0, rowspan=2, column=4, columnspan=4, sticky="nsew")
lbl_master[2].grid(row=0, rowspan=2, column=8, columnspan=4, sticky="nsew")
lbl_master[3].grid(row=0, rowspan=2, column=12, columnspan=4, sticky="nsew")
lbl_master[4].grid(row=3, rowspan=2, column=0, columnspan=4, sticky="nsew")
lbl_master[5].grid(row=3, rowspan=2, column=4, columnspan=4, sticky="nsew")
lbl_master[6].grid(row=3, rowspan=2, column=8, columnspan=4, sticky="nsew")
lbl_master[7].grid(row=3, rowspan=2, column=12, columnspan=4, sticky="nsew")

# Make a checkbutton to turn the display of each label on or off
btn_1 = tk.Checkbutton(master=window, text='Ch 1', highlightbackground = 'black', bg='white', command = lambda : Ch(0)).grid(row=2, column=3, sticky="nsew")
btn_2 = tk.Checkbutton(master=window, text='Ch 2', highlightbackground = 'black', bg='white', command = lambda : Ch(1)).grid(row=2, column=7, sticky="nsew")
btn_3 = tk.Checkbutton(master=window, text='Ch 3', highlightbackground = 'black', bg='white', command = lambda : Ch(2)).grid(row=2, column=11, sticky="nsew")
btn_4 = tk.Checkbutton(master=window, text='Ch 4', highlightbackground = 'black', bg='white', command = lambda : Ch(3)).grid(row=2, column=15, sticky="nsew")
btn_5 = tk.Checkbutton(master=window, text='Ch 5', highlightbackground = 'black', bg='white', command = lambda : Ch(4)).grid(row=5, column=3, sticky="nsew")
btn_6 = tk.Checkbutton(master=window, text='Ch 6', highlightbackground = 'black', bg='white', command = lambda : Ch(5)).grid(row=5, column=7, sticky="nsew")
btn_7 = tk.Checkbutton(master=window, text='Ch 7', highlightbackground = 'black', bg='white', command = lambda : Ch(6)).grid(row=5, column=11, sticky="nsew")
btn_C = tk.Checkbutton(master=window, text='Ch 8', highlightbackground = 'black', bg='white', command = lambda : Ch(7)).grid(row=5, column=15, sticky="nsew")

# Create entry boxes for the target wavelength of each channel
entry_master = 8*[0]
for i in range(8):
    entry_master[i] = tk.Entry(master=window, highlightbackground = 'black')

# Position the entry boxes
entry_master[0].grid(row=2, column=2, sticky="nsew")
entry_master[1].grid(row=2, column=6, sticky="nsew")
entry_master[2].grid(row=2, column=10, sticky="nsew")
entry_master[3].grid(row=2, column=14, sticky="nsew")
entry_master[4].grid(row=5, column=2, sticky="nsew")
entry_master[5].grid(row=5, column=6, sticky="nsew")
entry_master[6].grid(row=5, column=10, sticky="nsew")
entry_master[7].grid(row=5, column=14, sticky="nsew")

# Create labels for the entry boxes
tgt_lbl = 8*[0]
for i in range(8):
    tgt_lbl[i] = tk.Label(master=window, text=f'Ch {i+1} Target Wavelength', relief='solid', bg='white')

# Position entry box labels
tgt_lbl[0].grid(row=2, column=0, columnspan=2, sticky="nsew")
tgt_lbl[1].grid(row=2, column=4, columnspan=2, sticky="nsew")
tgt_lbl[2].grid(row=2, column=8, columnspan=2, sticky="nsew")
tgt_lbl[3].grid(row=2, column=12, columnspan=2, sticky="nsew")
tgt_lbl[4].grid(row=5, column=0, columnspan=2, sticky="nsew")
tgt_lbl[5].grid(row=5, column=4, columnspan=2, sticky="nsew")
tgt_lbl[6].grid(row=5, column=8, columnspan=2, sticky="nsew")
tgt_lbl[7].grid(row=5, column=12, columnspan=2, sticky="nsew")

# Create figure for plotting
fig = plt.Figure((5,7), dpi=100)
ax = fig.add_subplot(111)
graph = FigureCanvasTkAgg(fig, master=window)
graph.get_tk_widget().grid(row=6, rowspan=6, column = 8, columnspan=7, sticky="nsew")

# Use a color map to pick the colors used for plotting
cmap = plt.cm.get_cmap('viridis')
colors = [None]*8
for i in range(8):
    colors[i] = cmap(i/8)

# Create the start button and tie it to the start function
btn_start = tk.Button(master=window, text='Start', command=start, bg='DarkSeaGreen', fg = 'DarkOliveGreen')
btn_start.grid(row=10, column=15, sticky="nsew")

# Create the stop button and tie it to the stop function       
btn_stop = tk.Button(master=window, text='Close Window', command=stop, bg='dark salmon', fg = 'dark red')
btn_stop.grid(row=11, column=15, sticky="nsew")

# This function reads and displays the wavelength in the correct place
# Also closes the window if 'stop' button is pressed    
def update():
    global selec_list, data, lbl_master, end
    while True:
        # Pickles and sends selection list
        to_send = pickle.dumps(selec_list)
        ClientSocket.sendall(to_send)
        # Reads data from server, stores in list
        msg = ClientSocket.recv(1024)
        data = pickle.loads(msg)
        for i in range(8):
            # Updates the display for each channel
            lbl_master[i]['text'] = f'{data[i]} nm'
            # Reads out user entered target wavelengths
            targets[i] = entry_master[i].get()
            # Updates the plottable data for selected channels
            if data[i] != '---':
                plottable[i].append(data[i])
                try:
                    # Changes plottable data to the difference between measured and desired wavelength
                    plottable[i][-1] = float(plottable[i][-1])  - float(targets[i])
                except:
                    plottable[i] = plottable[i]
                else:
                    for k in range(len(plottable[i])):
                        if plottable[i][k] > 0:
                            ax.cla()
                            ax.grid()
                            ax.set_xlabel('Samples')
                            ax.set_ylabel('nm')
                            ax.set_title(r'$\Delta \lambda$')
                            ax.plot(plottable[i], c=colors[i])
                            graph.draw()
            if len(plottable[i]) > 30:
                plottable[i].pop(0)
        if end:
            break
    ClientSocket.close()
    window.destroy()
    sys.exit()

# Run the GUI
window.mainloop()

# Close the entire program once window closes
print('Program closing')
os._exit(0)
