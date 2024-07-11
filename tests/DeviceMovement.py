from __future__ import print_function
import sys, os, time, logging

#logging.basicConfig(level=logging.DEBUG)

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from acq4.drivers.Scientifica import Scientifica
from acq4.devices.NiDAQ import NiDAQ
from acq4.drivers.nidaq.nidaq import NIDAQ as n
from acq4.devices.MultiClamp import MultiClamp
from acq4.devices.MicroManagerCamera import MicroManagerCamera
from acq4.devices.MicroManagerStage import MicroManagerStage

import acq4.util.ptime as ptime
from matplotlib import pyplot as plt
import numpy as np

# MANIPULATOR
baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else None
devname = "PatchStar"
if devname.lower().startswith('com') or devname.startswith('/dev/'):
    ps = Scientifica(port=devname, baudrate=baudrate, ctrl_version=None)
else:
    ps = Scientifica(name=devname, baudrate=baudrate, ctrl_version=None)

def printManipulatorSettings():
    print("Device type:  %s  Description:  %s" % (ps.getType(), ps.getDescription()))
    print("Firmware version: %r" % ps.getFirmwareVersion())
    print("Position: %r" % ps.getPos())
    print("Max speed: %r um/sec" % ps.getSpeed())
    if ps._version < 3:
        print("Min speed: %r um/sec" % (ps.getParam('minSpeed') / (2. * ps.getAxisScale(0))))
        print("Acceleration: %r um^2/sec" % (ps.getParam('accel') * 250. / ps.getAxisScale(0)))
    else:
        print("Min speed: %r um/sec" % ps.getParam('minSpeed'))
        print("Acceleration: %r um^2/sec" % ps.getParam('accel'))
print("Configured PatchStar")

# NATIONAL INSTRUMENTS DAQ
daq = NiDAQ(None, 
            {'defaultAIMode': 'NRSE', 'defaultAIRange': [-10, 10], 'defaultAORange': [-10, 10]}, 
            "DAQ")

def printDAQSettings():
    print("Assert num devs > 0:")
    assert len(n.listDevices()) > 0
    print("  OK")
    print("devices: %s" % n.listDevices())
    dev = n.listDevices()[0]

    print("\nAnalog Channels:")
    print("  AI: ", n.listAIChannels(dev))
    print("  AO: ", n.listAOChannels(dev))

    print("\nDigital ports:")
    print("  DI: ", n.listDIPorts(dev))
    print("  DO: ", n.listDOPorts(dev))

    print("\nDigital lines:")
    print("  DI: ", n.listDILines(dev))
    print("  DO: ", n.listDOLines(dev))

# MULTICLAMP
clamp = MultiClamp(None, {'channelID': 'model:MC700B,sn:00836613,chan:1',
    'commandChannel': {
        'device': 'DAQ',
        'channel': '/Dev1/ao0',
        'type': 'ao'},
    'primaryChannel': {
        'device': 'DAQ',
        'chsannel': '/Dev1/ai10',
        'mode': 'NRSE',
        'type': 'ai'},
    'secondaryChannel': {
        'device': 'DAQ',
        'channel': '/Dev1/ai9',
        'mode': 'NRSE',
        'type': 'ai'},
    #vcHolding: -65e-3
    'vcHolding': 0.0,
    'icHolding': 0.0}, 'Clamp1', daq)

def printClampStateOptions():
    print("Clamp State Options: ", clamp.getState())

printClampStateOptions()

# HAMAMATSU ORCA CAMERA
camera = MicroManagerCamera(None, {'mmAdapterName': 'HamamatsuHam',
    'mmDeviceName': 'HamamatsuHam_DCAM'}, 'Camera')

print("Created Camera with sensor size ", camera.sensorSize)

# PRIOR Z STAGE
stage = MicroManagerStage(None, {
    'scale': [-1e-6, -1e-6, 1e-6],
            
    'zStage':
        {'mmAdapterName': 'Prior',
        'mmDeviceName': 'ZStage',
        'serial':
            {'port': 'COM6',
            'baud': 9600}}
}, 'Stage')

print("Configured Stage")

# All devices Configured

# Camera Functions 
def displayFrames(frames, title=""):
    for frame in frames:
        plt.imshow(frame, interpolation='nearest')
        plt.title(title)
        plt.show()

cameraCapture = True
num_frames = 1

if cameraCapture:
    frames = camera._acquireFrames(num_frames)
    displayFrames(frames, "Baseline")

# Move Manipulator

def moveOnAxis(axis, val, speed, displayResults=False):
    pos1 = ps.getPos()
    pos2 = [None, None, None]
    pos2[axis] = pos1[axis] + val
    print("Move %s => %s" % (pos1, pos2))
    ps.moveTo(pos2, speed=speed)
    #i = 0
    if displayResults:
        while ps.isMoving():
            pos = ps.getPos()
            print("time: %s position: %s" % (time.time(), pos))
            time.sleep(0.01)
        #i += 1

manipulatorMove = True

if manipulatorMove:
    moveOnAxis(2, 1000, 3000, True)
    pos1 = ps.getPos()
    pos2 = [None, None, pos1[2]]
    pos2[2] -= 2000
    print("Move %s => %s" % (pos1, pos2))
    ps.moveTo(pos2, speed=1000)
    c = 0
    while ps.isMoving():
        pos = ps.getPos()
        print("time: %s position: %s" % (time.time(), pos))
        time.sleep(0.01)
        c += 1
    
# Take a Picture

if cameraCapture:
    frames = camera._acquireFrames(num_frames)
    displayFrames(frames, "Manipulator Moved")

# DAQ It, Precursor
def finiteReadTest():
    print("::::::::::::::::::  Analog Input Test  :::::::::::::::::::::")
    task = n.createTask()
    task.CreateAIVoltageChan("/Dev1/ai10", "", n.Val_RSE, -1.0, 1.0, n.Val_Volts, None)
    task.CreateAIVoltageChan("/Dev1/ai9", "", n.Val_Cfg_Default, -10.0, 10.0, n.Val_Volts, None)

    task.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_FiniteSamps, 1000)
    task.start()
    data = task.read()
    task.stop()

    return data


def contReadTest():
    print("::::::::::::::::::  Continuous Read Test  :::::::::::::::::::::")
    task = n.createTask()
    task.CreateAIVoltageChan("/Dev1/ai10", "", n.Val_RSE, -10.0, 10.0, n.Val_Volts, None)
    task.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_ContSamps, 4000)
    task.start()
    t = ptime.time()
    for i in range(0, 10):
        data, size = task.read(1000)
        print("Cont read %d - %d samples, %fsec" % (i, size, ptime.time() - t))
        t = ptime.time()
    task.stop()

    return data

data = finiteReadTest()
print(data)

# DAQ it

print("Switching to VC on MC")
clamp.setMode('VC')
print("ao0 Baseline at 0.0V")
daq.setChannelValue('/Dev1/ao0', 0.0)
print("Done changing ao0")
time.sleep(1)

print("Setting a0 to 1.0V")
daq.setChannelValue('/Dev1/ao0', 1.0)
time.sleep(3)

print("Recording primary output")
iter1Primary = finiteReadTest()
print("Done recording primary output. Samples: ", iter1Primary)
x = np.arange(0, len(iter1Primary[0][0]), 1)
plt.plot(x, iter1Primary[0][0])
plt.plot(x, iter1Primary[0][1])
plt.title("Primary, Secondary Output")
plt.show()

daq.setChannelValue('/Dev1/ao0', 0.0)

# Move Z Stage
METERS_TO_MICRONS = 1e-6

currentStagePos = stage.getPosition()
newStagePos = currentStagePos
newStagePos[2] += 500 * METERS_TO_MICRONS
stage.move(newStagePos)

#cmd = {'mode': 'VC', 'primary': 'Membrane Current', 'secondary': 'Membrane Potential', 'holding': 0, 'primaryGain': 2.0, 'secondaryGain': 1.0}
#newTask = MultiClampTask(clamp, cmd, None)
#newTask.configure()
#newTask.createChannels(daq)
#newTask.start()
#while newTask.isDone == False:
#    time.sleep(0.1)
#newTask.getResult()




#daqPrimary = daq.getChannelValue('/Dev1/ai9')
#clampPrimary = clamp.getParam('PrimarySignal')
# # in picoamps
#print("Clamp Primary (pA): ", clampPrimary)
##print("DAQ Primary (V): ", daqPrimary)
#
#daq.setChannelValue('/Dev1/ao0', 1)
#
#clampPrimary = clamp.getState() #clamp.listSignals('VC')
#daqPrimary = daq.getChannelValue('/Dev1/ai9')
#print("Clamp Primary (pA): ", clampPrimary) # in picoamps
#print("DAQ Primary (V): ", daqPrimary)
#
#daq.setChannelValue('/Dev1/ao0', 0)
