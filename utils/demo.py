#!/usr/bin/python

import subprocess

from Tkinter import *

class Application(Frame):
    def publishSnapshotMessage(self):
        cmd = 'mosquitto_pub -h localhost -t berrynet/event/camera -m snapshot_picam'
        subprocess.call(cmd, shell=True)

    def startGateway(self):
        cmd = 'bash ~/codes/BerryNet/berrynet-manager start'
        subprocess.call(cmd, shell=True)

    def stopGateway(self):
        cmd = 'bash ~/codes/BerryNet/berrynet-manager stop'
        subprocess.call(cmd, shell=True)

    def startChromium(self):
        cmd = 'bash -c "sensible-browser http://localhost:8080/index.html#source=dashboard.json" &'
        subprocess.call(cmd, shell=True)

    def stopChromium(self):
        cmd = 'bash -c "kill -9 $(pgrep chromium)"'
        subprocess.call(cmd, shell=True)

    def startDemo(self):
        self.startGateway()
        self.startChromium()

    def stopDemo(self):
        self.stopChromium()
        self.stopGateway()

    def cleanSnapshots(self):
        cmd = 'bash -c "sudo rm /usr/local/berrynet/inference/image/snapshot*"'
        subprocess.call(cmd, shell=True)

    def createWidgets(self):
        self.snapshotButton = Button(self, text='Snapshot', width=16, height=5)
        self.snapshotButton["command"] = self.publishSnapshotMessage
        self.snapshotButton.pack(fill=X)

        self.startDemoButton = Button(self, text='Start Demo', width=16, height=5)
        self.startDemoButton["command"] = self.startDemo
        self.startDemoButton.pack(fill=X)

        self.stopDemoButton = Button(self, text='Stop Demo', width=16, height=5)
        self.stopDemoButton["command"] = self.stopDemo
        self.stopDemoButton.pack(fill=X)

        self.cleanButton = Button(self, text='Clean Snapshots', width=16, height=5)
        self.cleanButton["command"] = self.cleanSnapshots
        self.cleanButton.pack(fill=X)

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
