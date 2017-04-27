#!/usr/bin/python

import subprocess

from Tkinter import *

class Application(Frame):
    def say_hi(self):
        print "hi there, everyone!"

    def publishSnapshotMessage(self):
        cmd = 'mosquitto_pub -h localhost -t berrynet/event/camera -m snapshot_picam'
        subprocess.call(cmd, shell=True)

    def createWidgets(self):
        self.hi_there = Button(self, text='Snapshot', width=16, height=5)
        self.hi_there["command"] = self.publishSnapshotMessage
        self.hi_there.pack({"side": "left"})

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack()
        self.createWidgets()

root = Tk()
app = Application(master=root)
app.master.title('Cheese')
app.master.lift()
app.master.attributes('-topmost', True)
app.mainloop()
root.destroy()
