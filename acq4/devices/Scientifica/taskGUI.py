from __future__ import print_function

import weakref

from acq4.devices.DAQGeneric.DaqChannelGui import OutputChannelGui, InputChannelGui
from acq4.devices.Device import TaskGui
from pyqtgraph import PlotWidget
from pyqtgraph.WidgetGroup import WidgetGroup
from acq4.util import Qt
from acq4.util.debug import printExc

Ui_Form = Qt.importTemplate('.TaskTemplate')

class ScientificaGUI(TaskGui):
    sigSequenceChanged = Qt.pyqtSignal(object)

    def __init__(self, dev, task, ownUi=True):
        TaskGui.__init__(self, dev, task)
        self.plots = weakref.WeakValueDictionary()
        self.channels = {}
        
        if ownUi:
            self.ui = Ui_Form()
            self.ui.setupUi(self)
            self.stateGroup = WidgetGroup([
                (self.ui.topSplitter, 'splitter1'),
                (self.ui.controlSplitter, 'splitter2'),
                (self.ui.plotSplitter, 'splitter3'),
            ])
            self.createChannelWidgets(self.ui.controlSplitter, self.ui.plotSplitter)
            self.ui.topSplitter.setStretchFactor(0, 0)
            self.ui.topSplitter.setStretchFactor(1, 1)
            
        else:
            ## If ownUi is False, then the UI is created elsewhere and createChannelWidgets must be called from there too.
            self.stateGroup = None
    
    def __init__(self, dev, taskRunner, parent=None):
        super().__init__(dev, taskRunner)
        self.dev = dev
        self.taskRunner = taskRunner
        
        self.initUI()
        self.enable()
        
    def enable(self):
        self.taskRunner.sigTaskSequenceStarted.connect(self.taskSequenceStarted)
        self.taskRunner.sigTaskStarted.connect(self.taskStarted)
        self.taskRunner.sigTaskFinished.connect(self.taskFinished)
        
    def disable(self):
        self.taskRunner.sigTaskSequenceStarted.disconnect(self.taskSequenceStarted)
        self.taskRunner.sigTaskStarted.disconnect(self.taskStarted)
        self.taskRunner.sigTaskFinished.disconnect(self.taskFinished)
        
    def initUI(self):
        layout = Qt.QVBoxLayout(self)
        
        # Create three regions for displaying position
        self.positionDisplays = {}
        for axis in self.dev.axes():
            label = Qt.QLabel(f'{axis}:')
            positionEdit = Qt.QLineEdit()
            positionEdit.setReadOnly(True)
            
            layout.addWidget(label)
            layout.addWidget(positionEdit)
            
            self.positionDisplays[axis] = positionEdit
            
        # Create up/down arrow buttons (optional)
        upButton = Qt.QPushButton('↑')
        downButton = Qt.QPushButton('↓')
        
        layout.addWidget(upButton)
        layout.addWidget(downButton)
        
        # Connect signals
        upButton.clicked.connect(self.moveUp)
        downButton.clicked.connect(self.moveDown)
        
    def moveUp(self):
        # Implement move up functionality
        pass
    
    def moveDown(self):
        # Implement move down functionality
        pass
    
    def updatePosition(self, pos):
        """Update displayed positions."""
        for axis, value in zip(self.dev.axes(), pos):
            self.positionDisplays[axis].setText(f'{value:.4f}')
            
    def prepareTaskStart(self):
        """Called once before the start of each task or task sequence. Allows the device to execute any one-time preparations it needs."""
        pass
        
    def saveState(self):
        """Return a dictionary representing the current state of the widget."""
        return {}
        
    def restoreState(self, state):
        """Restore the state of the widget from a dictionary previously generated using saveState"""
        pass
        
    def describe(self, params=None):
        """Return a nested-dict structure that describes what the device will do during a task.
        This data will be stored along with results from a task run."""
        return self.saveState()  ## lazy; implement something nicer for your devices!
        
    def listSequence(self):
        """
        Return an OrderedDict of sequence parameter names and values {name: list_of_values}. See generateTask for more
        details on usage.
        """
        return {}
        
    def generateTask(self, params=None):
        """
        This method should convert params' index-values back into task-values, along with any default work non-sequenced
        tasks need. WARNING! Long sequences will not automatically lock the UI or preserve the state of your parameter
        sequences. The example code below will break if a user messes with anything while the task sequence is running.

        :param params:
            This dictionary will have the same top-level shape as the return value of listSequence, but instead of a
            list, its values will be the indexes of the values currently being run. E.g.::

                listSequence() -> {'a': [10, 100, 1000], 'b': [20, 40]}
                generateTask({'a': 0, 'b': 0})
                generateTask({'a': 1, 'b': 0})
                ...

        :return:
            Valid command structure for your devices' task.
        """
        if params is None:
            params = {}
        paramSpace = self.listSequence()  # WARNING! This is not reliable!
        params = {k: paramSpace[k][v] for k, v in params.items()}
        return params
        
    def handleResult(self, result, params):
        """Display (or otherwise handle) the results of the task generated by this device.
        Does NOT handle file storage; this is handled by the device itself."""
        pass

    def taskSequenceStarted(self):
        """Automatically invoked before a task or sequence is started.
        Note: this signal is emitted AFTER generateTask() has been run for all devices,
        and before the task is started.
        """
        pass

    def taskStarted(self, params):
        """Automatically invoked before a single task is started, including each task within a sequence."""
        pass
        
    def taskFinished(self):
        """Automatically invoked after a task or sequence has finished"""
        pass

    def quit(self):
        self.disable()
