from Workbench import Workbench, arrayAverage
#from States import EnterBathState, CaptureState, SealState, HuntState, BreakInState, WholeCellState, CleanState

import time
import datetime
import threading
import queue
import numpy as np

from matplotlib.animation import FuncAnimation
from matplotlib import pyplot as plt
from cv2 import equalizeHist

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
        self.file = open('resistance.txt', 'w')
        self.file.write('Experiment commencing at ' + datetime.datetime.now().isoformat() +'\n')
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
        self.voltage_acquisition_thread.join()
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

        self.voltage_acquisition_thread = threading.Thread(target=self.acquireVoltageClampData, args=(self.data_queue, period, self.stop_event))
        self.voltage_acquisition_thread.start()

    
    # DATAQUEUE:
    # voltage_sent: Voltage reading of last pulse
    # current_read: Current reading of last pulse
    # resistance: Resistance measure in megaohms
    # date: Timestamp

    def acquireVoltageClampData(self, data_queue, period, stop_recording):
        while not stop_recording.is_set():
            #_, voltage_data = self.wb.sendPulse(1, 0, period)
            voltage_data = self.wb.sendPulseBothChannels(1, 0, period)
            #task = voltage_data['chans'][0]['task']
            #ind = voltage_data['chans'][0]['index']
            #print(voltage_data[task]['data'][0][ind])
            # print "Data:", data[task]['data'][0][ind]
            #print(voltage_data['Dev1'])
            #self.__del__()
            #raise Exception("STop")
            
            voltage_sent = voltage_data[1]
            voltage_read = voltage_data[0]
            voltage2_sent = voltage_data[3]
            voltage2_read = voltage_data[2]

            voltage_sent = voltage_sent * self.wb.clamp.getState()['secondaryScaleFactor']
            current_read = voltage_read * self.wb.clamp.getState()['primaryScaleFactor']
            voltage2_sent = voltage2_sent * self.wb.clamp2.getState()['secondaryScaleFactor']
            current2_read = voltage2_read * self.wb.clamp2.getState()['primaryScaleFactor']
            
            resistances, transient_present = self.wb.calculateResistance(voltage_sent, current_read, 1)
            resistances2, _ = self.wb.calculateResistance(voltage2_sent, current2_read, 1)
            megasurement = resistances[0] / 1e6
            megasurement2 = resistances2[0] / 1e6
            date = datetime.datetime.now()
            if self.state is not None:
                self.file.write(date.isoformat(' ') + ' ' + self.state.__str__() + ' ' + str(round(megasurement, 2)) + '\n')
            data_queue.put((voltage_sent, current_read, megasurement, transient_present, date, megasurement2))
    
    def processQueue(self):
        if not self.data_queue.empty():
            while not self.data_queue.empty():
                self.voltage, self.current, resistance, transientPresent, date, resistance2 = self.data_queue.get_nowait()
                
                
                if len(self.resistanceHistory) >= 1000:
                    self.resistanceHistory = self.resistanceHistory[-999:-1]
                if len(self.resistance2History) >= 1000:
                    self.resistance2History = self.resistance2History[-999:-1]
                if len(self.dates) >= 100:
                    self.dates = self.dates[-99:-1]
                if len(self.transientHistory) >= 100:
                    self.transientHistory = self.transientHistory[-999:-1]

                self.resistanceHistory.append(resistance)
                self.resistance2History.append(resistance2)
                self.dates.append(date)
                self.transientHistory.append(transientPresent)

    def configurePlot(self):
        x = np.zeros(1)
        self.voltage = [0 for _ in range(350)]
        self.current = [0 for _ in range(350)]
        self.resistanceHistory = [0 for _ in range(1000)]
        self.resistance2History = [0 for _ in range(1000)]
        self.transientHistory = [0 for _ in range(1000)]
        self.dates = [0 for _ in range(1000)]

        self.fig, self.ax = plt.subplot_mosaic([[0, 3, 4],
                                           [1, 3, 4],
                                           [2, 3, 4]],
                                            figsize=(15, 5), layout='constrained')
        #fig.canvas.mpl_connect('close_event', self.__del__())

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
        
        blank_frame = np.zeros((512,512))
        #self.cam_histogram = self.ax[4].hist(blank_frame.flatten(),2**11,[0,2**16], color = 'r')
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

        self.line1.set_xdata(np.arange(len(self.voltage)))
        self.line1.set_ydata(self.voltage)
        self.line2.set_xdata(np.arange(len(self.current)))
        self.line2.set_ydata(self.current)

        self.line3.set_xdata(np.arange(len(self.resistanceHistory)))
        self.line3.set_ydata(self.resistanceHistory)

        #self.ax[0].set_title(self.dates[-1].isoformat(' '))

        if self.transientHistory[-1]:
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
            cdf = hist.cumsum()
            cdf_normalized = cdf * hist.max() / cdf.max()

            #self.cam_histogram.plot(cdf_normalized, color = 'b')

            if self.saveImage == True:
                fname = '../acq4-storage/730CatchAndRelease/' + str(self.imNumber) + '.png'
                plt.imsave(fname, decimatedFrame, cmap='gray', vmin=0, vmax=2**16 - 1)
                self.imNumber += 1
                self.saveImage = False
            self.cam_img.set_data(decimatedFrame)
            self.cam_histogram.set_data(np.arange(0, 2**11), norm_hist)
            #self.cam_img.set_data(equalizeHist(decimatedFrame.astype(np.uint8)))
            #self.ax[3].set_title(camera_date.isoformat(' '))   

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

        #self.ax[1].relim()
        #self.ax[2].relim()
        #self.ax[2].autoscale_view()
        # update ax.viewLim using the new dataLim
        #self.ax[1].autoscale_view()

        self.fig.canvas.blit(self.ax[0].bbox)
        self.fig.canvas.blit(self.ax[1].bbox)
        self.fig.canvas.blit(self.ax[2].bbox)
        self.fig.canvas.blit(self.ax[3].bbox)
        self.fig.canvas.blit(self.ax[4].bbox)
        
        self.fig.canvas.flush_events()
# Every state returns the next state
# While loop runs outside state machine
# Has resistance increased by 10% Pull bath test out, will cause resistance to increase and call transition.