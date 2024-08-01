from Workbench import Workbench, arrayAverage
#from States import EnterBathState, CaptureState, SealState, HuntState, BreakInState, WholeCellState, CleanState

import time
from datetime import datetime
import threading
import queue
import numpy as np
import os

from matplotlib.animation import FuncAnimation
from matplotlib import pyplot as plt

import nest_asyncio
nest_asyncio.apply()
    
class Machine(object):
    """ 
    A simple state machine that mimics the functionality of a device from a 
    high level.
    """

    def __init__(self):
        """ Initialize the components. """
        self.wb = Workbench()
        self.wb.pressureController.writeMessageSwitch(b'atm 1')
        self.wb.pressureController.setPressure(200, 2)
        self.wb.pressureController.writeMessageSwitch(b'pressure 2')
        
        self.experimentDir = '../acq4-storage/Experiments/' + datetime.today().strftime('%Y%m%d%H%M%S') + "/"
        if not os.path.exists(self.experimentDir):
            os.makedirs(self.experimentDir)

        self.wholeCellDir = self.experimentDir + 'Misc/'
        if not os.path.exists(self.wholeCellDir):
            os.makedirs(self.wholeCellDir)

        self.file = open(self.experimentDir + 'Misc/resistance.txt', 'w')
        self.file.write('Experiment commencing at ' + datetime.now().isoformat() +'\n')
        self.file.close()
        self.file = open('resistance.txt', 'a')
        # Start with a default state.
        self.state = None
        self.saveImage = False
        self.imNumber = 0
        #self.state = EnterBathState(self.wb, self)#CaptureState(self.wb, self)
        self.data_queue = queue.Queue(100)
        self.streamVoltagePulses()
        self.configurePlot()

    def __del__(self):
        self.wb.pressureController.writeMessageSwitch(b'atm 1')
        self.wb.pressureController.writeMessageSwitch(b'atm 2')
        self.future.stop()
        self.wb.camera.stopCamera()
        self.file.close()
        self.stop_event.set()
        self.data_acquisition_thread.join()
        exit()
        print("Terminating program.")

    def on_event(self, event):
        """
        This is the bread and butter of the state machine. Incoming events are
        delegated to the given states which then handle the event. The result is
        then assigned as the new state.
        """

        # The next state will be the result of the on_event function. Pass in device as arg
        self.state = self.state.on_event(event)

    def streamVoltagePulses(self):
        frequency = 60
        period = 1 / frequency

        self.wb.voltageClamp(1)
        self.wb.voltageClamp(2)

        print("Configured background recording!")

        self.stop_event = threading.Event()

        self.data_acquisition_thread = threading.Thread(target=self.acquireVoltageClampData, args=(self.data_queue, period, self.stop_event, True))
        self.data_acquisition_thread.start()

    def readVoltagePulses(self):
        frequency = 60
        period = 1 / frequency

        self.stop_event = threading.Event()

        self.data_acquisition_thread = threading.Thread(target=self.acquireVoltageClampData, args=(self.data_queue, period, self.stop_event, False))
        self.current_acquisition_thread.start()

    def readCurrentPulses(self):
        frequency = 60
        period = 1 / frequency

        self.wb.currentClamp(1)
        self.wb.currentClamp(2)

        self.stop_event = threading.Event()

        self.data_acquisition_thread = threading.Thread(target=self.acquireCurrentClampData, args=(self.data_queue, period, self.stop_event))
        self.current_acquisition_thread.start()

    def acquireCurrentClampData(self, data_queue, period, stop_recording):
        while not stop_recording.is_set():
            voltage_data = self.wb.readPulseBothChannels( period)
            
            patch_secondary = voltage_data[1]
            patch_primary = voltage_data[0]
            capture_secondary = voltage_data[3]
            capture_primary = voltage_data[2]

            current_patch = patch_secondary * self.wb.patchAmplifier.getState()['secondaryScaleFactor']
            voltage_patch = patch_primary * self.wb.patchAmplifier.getState()['primaryScaleFactor']
            current_capture = capture_secondary * self.wb.captureAmplifier.getState()['secondaryScaleFactor']
            voltage_capture = capture_primary * self.wb.captureAmplifier.getState()['primaryScaleFactor']
            
            resistancesPatch, transientPresentPatch = self.wb.calculateResistance(voltage_patch, current_patch, 1)
            resistancesCapture, transientPresentCapture = self.wb.calculateResistance(voltage_capture, current_capture, 1)
            resistancePatchMegaohm = resistancesPatch[0] / 1e6
            resistanceCaptureMegaohm = resistancesCapture[0] / 1e6
            date = datetime.datetime.now()
            if self.state is not None:
                self.file.write(date.isoformat(' ') + ' ' + self.state.__str__() + ' ' + str(round(resistancePatchMegaohm, 2)) + '\n')
            data_queue.put((voltage_patch, current_patch, resistancePatchMegaohm, transientPresentPatch, date, resistanceCaptureMegaohm))
    
    # DATAQUEUE:
    # voltage_sent: Voltage reading of last pulse
    # current_read: Current reading of last pulse
    # resistance: Resistance measure in megaohms
    # date: Timestamp

    def stopAcquiringData(self):
        self.stop_event.set()
        self.data_acquisition_thread.join()

    def acquireVoltageClampData(self, data_queue, period, stop_recording, sendPulse=True):
        while not stop_recording.is_set():
            if sendPulse:
                voltage_data = self.wb.sendPulseBothChannels(1, 0, period)
            else:
                voltage_data = self.wb.readPulseBothChannels(period)
            
            patch_secondary = voltage_data[1]
            patch_primary = voltage_data[0]
            capture_secondary = voltage_data[3]
            capture_primary = voltage_data[2]

            voltage_patch = patch_secondary * self.wb.patchAmplifier.getState()['secondaryScaleFactor']
            current_patch = patch_primary * self.wb.patchAmplifier.getState()['primaryScaleFactor']
            voltage_capture = capture_secondary * self.wb.captureAmplifier.getState()['secondaryScaleFactor']
            current_capture = capture_primary * self.wb.captureAmplifier.getState()['primaryScaleFactor']
            
            resistancesPatch, transientPresentPatch = self.wb.calculateResistance(voltage_patch, current_patch, 1)
            resistancesCapture, transientPresentCapture = self.wb.calculateResistance(voltage_capture, current_capture, 1)
            resistancePatchMegaohm = resistancesPatch[0] / 1e6
            resistanceCaptureMegaohm = resistancesCapture[0] / 1e6
            date = datetime.now()
            if self.state is not None:
                self.file.write(date.isoformat(' ') + ' ' + self.state.__str__() + ' ' + str(round(resistancePatchMegaohm, 2)) + '\n')
            data_queue.put((voltage_patch, current_patch, resistancePatchMegaohm, transientPresentPatch, date, resistanceCaptureMegaohm))
    
    def processQueue(self):
        if not self.data_queue.empty():
            while not self.data_queue.empty():
                self.voltage_patch, self.current_patch, resistance_patch, transientPresent_patch, date, resistance_capture = self.data_queue.get_nowait()
                
                if len(self.resistancePatchHistory) >= 1000:
                    self.resistancePatchHistory = self.resistancePatchHistory[-999:-1]
                if len(self.resistanceCaptureHistory) >= 1000:
                    self.resistanceCaptureHistory = self.resistanceCaptureHistory[-999:-1]
                if len(self.dates) >= 100:
                    self.dates = self.dates[-99:-1]
                if len(self.transientPatchHistory) >= 100:
                    self.transientPatchHistory = self.transientPatchHistory[-999:-1]

                self.resistancePatchHistory.append(resistance_patch)
                self.resistanceCaptureHistory.append(resistance_capture)
                self.dates.append(date)
                self.transientPatchHistory.append(transientPresent_patch)

    def configurePlot(self):
        x = np.zeros(1)
        self.voltage_patch = [0 for _ in range(350)]
        self.current_patch = [0 for _ in range(350)]
        self.resistancePatchHistory = [0 for _ in range(1000)]
        self.resistanceCaptureHistory = [0 for _ in range(1000)]
        self.transientPatchHistory = [0 for _ in range(1000)]
        self.dates = [0 for _ in range(1000)]

        self.fig, self.ax = plt.subplot_mosaic([[0, 3, 4],
                                           [1, 3, 4],
                                           [2, 3, 4]],
                                            figsize=(15, 5), layout='constrained')

        self.line1, = self.ax[0].plot(x, np.zeros(1))
        self.line2, = self.ax[1].plot(x, np.zeros(1))
        self.line3, = self.ax[2].plot(np.zeros(1000), np.zeros(1000))
    
        self.ax[0].set_xlim([-20, 400])
        self.ax[0].set_ylim([-0.01, 0.05])
        self.ax[1].set_xlim([-20, 400])
        self.ax[1].set_ylim([-1E-9, 5e-9])
        self.ax[2].set_xlim([-10, 1001])
        self.ax[2].set_ylim([-10, 800])

        self.cam_img = self.ax[3].imshow(np.full((512,512), np.nan), cmap='gray', vmin=0, vmax=2**16 -1)
        
        self.cam_histogram, = self.ax[4].plot(np.zeros(2048), np.zeros(2048))

        self.ax[4].set_xlim([0, 2048])
        self.ax[4].set_ylim([0, 1])

        self.fig.canvas.draw()

        self.ax0background  = self.fig.canvas.copy_from_bbox(self.ax[0].bbox)
        self.ax1background  = self.fig.canvas.copy_from_bbox(self.ax[1].bbox)
        self.ax2background  = self.fig.canvas.copy_from_bbox(self.ax[2].bbox)
        self.aximbackground = self.fig.canvas.copy_from_bbox(self.ax[3].bbox)
        self.ax4background  = self.fig.canvas.copy_from_bbox(self.ax[4].bbox)

        print("Exposure!")
        print(self.wb.camera.getParam('exposure'))
        self.wb.camera.setParam('exposure', 0.02)
        self.wb.camera.start()
        self.future = self.wb.camera.acquireFrames(None)

        plt.show(block=False)

    def updatePlot(self):
        self.processQueue()

        self.line1.set_xdata(np.arange(len(self.voltage_patch)))
        self.line1.set_ydata(self.voltage_patch)
        self.line2.set_xdata(np.arange(len(self.current_patch)))
        self.line2.set_ydata(self.current_patch)

        self.line3.set_xdata(np.arange(len(self.resistancePatchHistory)))
        self.line3.set_ydata(self.resistancePatchHistory)

        if self.transientPatchHistory[-1]:
            self.line3.set_color('green')
        else:
            self.line3.set_color('red')

        camera_date = datetime.datetime.now()
        lastFrames = self.future.getStreamingResults()
        
        if len(lastFrames) > 0:
            lastFrame = lastFrames[-1].data()
            decimationFactor = 4
            decimatedFrame = lastFrame[::decimationFactor,::decimationFactor]
            self.image = decimatedFrame

            hist,bins = np.histogram(decimatedFrame.flatten(),2**11,[0,2**16])
            norm_hist = hist / max(hist)

            if self.saveImage:
                fname = self.wholeCellDir + str(self.imNumber) + '.png'
                plt.imsave(fname, decimatedFrame, cmap='gray', vmin=0, vmax=2**16 - 1)
                self.imNumber += 1
                self.saveImage = False

            self.cam_img.set_data(decimatedFrame)
            self.cam_histogram.set_data(np.arange(0, 2**11), norm_hist)

        self.fig.canvas.restore_region(self.ax0background )
        self.fig.canvas.restore_region(self.ax1background )
        self.fig.canvas.restore_region(self.ax2background )
        self.fig.canvas.restore_region(self.aximbackground)
        self.fig.canvas.restore_region(self.ax4background)

        self.ax[0].draw_artist(self.line1)
        self.ax[1].draw_artist(self.line2)
        self.ax[2].draw_artist(self.line3)
        self.ax[3].draw_artist(self.cam_img)
        self.ax[4].draw_artist(self.cam_histogram)

        self.fig.canvas.blit(self.ax[0].bbox)
        self.fig.canvas.blit(self.ax[1].bbox)
        self.fig.canvas.blit(self.ax[2].bbox)
        self.fig.canvas.blit(self.ax[3].bbox)
        self.fig.canvas.blit(self.ax[4].bbox)
        
        self.fig.canvas.flush_events()