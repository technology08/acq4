# -*- coding: utf-8 -*-
"""
WidgetGroup.py -  WidgetGroup class for easily managing lots of Qt widgets
Copyright 2010  Luke Campagnola
Distributed under MIT/X11 license. See license.txt for more infomation.

This class addresses the problem of having to save and restore the state
of a large group of widgets. 
"""

from PyQt4 import QtCore, QtGui
import weakref

def splitterState(w):
    s = str(w.saveState().toPercentEncoding())
    return s
    
def restoreSplitter(w, s):
    if type(s) is list:
        w.setSizes(s)
    elif type(s) is str:
        w.restoreState(QtCore.QByteArray.fromPercentEncoding(s))
    else:
        print "Can't configure QSplitter using object of type", type(s)
    if w.count() > 0:   ## make sure at least one item is not collapsed
        for i in w.sizes():
            if i > 0:
                return
        w.setSizes([50] * w.count())
        
def comboState(w):
    ind = w.currentIndex()
    data = w.itemData(ind)
    if not data.isValid():
        return w.itemText(ind)
    else:
        return data.toInt()[0]    
    
def setComboState(w, v):
    if type(v) is int:
        ind = w.findData(QtCore.QVariant(v))
        if ind > -1:
            w.setCurrentIndex(ind)
            return
    w.setCurrentIndex(w.findText(str(v)))
        

class WidgetGroup(QtCore.QObject):
    """This class takes a list of widgets and keeps an internal record of their state which is always up to date. Allows reading and writing from groups of widgets simultaneously."""
    
    ## List of widget types which can be handled by WidgetGroup.
    ## The value for each type is a tuple (change signal, get function, set function, [auto-add children])
    ## The change signal should be a signal that is emitted any time the state of the widget changes, not just 
    ##   when it is changed by user interaction. (for example, 'clicked' is not a valid signal here)
    ## If the change signal is None, the value of the widget is not cached.
    ## Custom widgets not in this list can be made to work with WidgetGroup by giving them a 'widgetGroupInterface' method
    ##   which returns the tuple.
    classes = {
        QtGui.QSpinBox: 
            ('valueChanged(int)', 
            QtGui.QSpinBox.value, 
            QtGui.QSpinBox.setValue),
        QtGui.QDoubleSpinBox: 
            ('valueChanged(double)', 
            QtGui.QDoubleSpinBox.value, 
            QtGui.QDoubleSpinBox.setValue),
        QtGui.QSplitter: 
            (None, 
            splitterState,
            restoreSplitter,
            True),
        QtGui.QCheckBox: 
            ('stateChanged(int)',
            QtGui.QCheckBox.isChecked,
            QtGui.QCheckBox.setChecked),
        QtGui.QComboBox:
            ('currentIndexChanged(int)',
            comboState,
            setComboState),
        QtGui.QGroupBox:
            ('toggled(bool)',
            QtGui.QGroupBox.isChecked,
            QtGui.QGroupBox.setChecked,
            True),
        #StimGenerator:
            #('changed',
            #StimGenerator.saveState,
            #StimGenerator.loadState),
        #PlotWidget:
            #(None,
            #PlotWidget.saveState,
            #PlotWidget.restoreState),
        QtGui.QLineEdit:
            ('editingFinished()',
            lambda w: str(w.text()),
            QtGui.QLineEdit.setText),
        QtGui.QRadioButton:
            ('toggled(bool)',
            QtGui.QRadioButton.isChecked,
            QtGui.QRadioButton.setChecked),
        QtGui.QSlider:
            ('valueChanged(int)',
            QtGui.QSlider.value,
            QtGui.QSlider.setValue),
    }
    
    
    def __init__(self, widgetList):
        """Initialize WidgetGroup, adding specified widgets into this group.
        widgetList can be either a list of widget specifications (widget, [name], [scale])
        or it can be any QObject, and all compatible child widgets will be added recursively.
        
        The 'scale' parameter for each widget allows QSpinBox to display a different value than the value recorded
        in the group state (for example, the program may set a spin box value to 100e-6 and have it displayed as 100 to the user)
        """
        QtCore.QObject.__init__(self)
        self.widgetList = weakref.WeakKeyDictionary() # Make sure widgets don't stick around just because they are listed here
        self.scales = weakref.WeakKeyDictionary()
        self.cache = {}  ## name:value pairs
        self.uncachedWidgets = weakref.WeakKeyDictionary()
        if isinstance(widgetList, QtCore.QObject):
            self.autoAdd(widgetList)
        elif isinstance(widgetList, list):
            for w in widgetList:
                self.addWidget(*w)
        else:
            raise Exception("Wrong argument type %s" % type(widgetList))
        
    def addWidget(self, w, name=None, scale=None):
        if not self.acceptsType(w):
            raise Exception("Widget type %s not supported by WidgetGroup" % type(w))
        if name is None:
            name = str(w.objectName())
        self.widgetList[w] = name
        self.scales[w] = scale
        self.readWidget(w)
            
        if type(w) in WidgetGroup.classes:
            signal = WidgetGroup.classes[type(w)][0]
        else:
            signal = w.widgetGroupInterface()[0]
            
        if signal is not None:
            QtCore.QObject.connect(w, QtCore.SIGNAL(signal), self.mkChangeCallback(w))
        else:
            self.uncachedWidgets[w] = None
       
    def findWidget(self, name):
        for w in self.widgetList:
            if self.widgetList[w] == name:
                return w
        return None
       
    def interface(self, obj):
        t = type(obj)
        if t in WidgetGroup.classes:
            return WidgetGroup.classes[t]
        else:
            return obj.widgetGroupInterface()

    def checkForChildren(self, obj):
        """Return true if we should automatically search the children of this object for more."""
        iface = self.interface(obj)
        return (len(iface) > 3 and iface[3])
       
    def autoAdd(self, obj):
        ## Find all children of this object and add them if possible.
        accepted = self.acceptsType(obj)
        if accepted:
            #print "%s  auto add %s" % (self.objectName(), obj.objectName())
            self.addWidget(obj)
            
        if not accepted or self.checkForChildren(obj):
            for c in obj.children():
                self.autoAdd(c)

    def acceptsType(self, obj):
        for c in WidgetGroup.classes:
            if isinstance(obj, c):
                return True
        if hasattr(obj, 'widgetGroupInterface'):
            return True
        return False
        #return (type(obj) in WidgetGroup.classes)

    def setScale(self, widget, scale):
        val = self.readWidget(widget)
        self.scales[widget] = scale
        self.setWidget(widget, val)
        #print "scaling %f to %f" % (val, self.readWidget(widget))
        

    def mkChangeCallback(self, w):
        return lambda *args: self.widgetChanged(w, *args)
        
    def widgetChanged(self, w, *args):
        #print "widget changed"
        n = self.widgetList[w]
        v1 = self.cache[n]
        v2 = self.readWidget(w)
        if v1 != v2:
            #print "widget", n, " = ", v2
            self.emit(QtCore.SIGNAL('changed'), self.widgetList[w], v2)
        
    def state(self):
        for w in self.uncachedWidgets:
            self.readWidget(w)
        
        #cc = self.cache.copy()
        #if 'averageGroup' in cc:
            #val = cc['averageGroup']
            #w = self.findWidget('averageGroup')
            #self.readWidget(w)
            #if val != self.cache['averageGroup']:
                #print "  AverageGroup did not match cached value!"
            #else:
                #print "  AverageGroup OK"
        return self.cache.copy()

    def setState(self, s):
        #print "SET STATE", self, s
        for w in self.widgetList:
            n = self.widgetList[w]
            #print "  restore %s?" % n
            if n not in s:
                continue
            #print "    restore state", w, n, s[n]
            self.setWidget(w, s[n])

    def readWidget(self, w):
        if type(w) in WidgetGroup.classes:
            getFunc = WidgetGroup.classes[type(w)][1]
        else:
            getFunc = w.widgetGroupInterface()[1]
        
        if getFunc is None:
            return None
            
        val = getFunc(w)
        if self.scales[w] is not None:
            val /= self.scales[w]
        if isinstance(val, QtCore.QString):
            val = str(val)
        n = self.widgetList[w]
        self.cache[n] = val
        return val

    def setWidget(self, w, v):
        v1 = v
        if self.scales[w] is not None:
            v *= self.scales[w]
        
        if type(w) in WidgetGroup.classes:
            setFunc = WidgetGroup.classes[type(w)][2]
        else:
            setFunc = w.widgetGroupInterface()[2]
        setFunc(w, v)
        #name = self.widgetList[w]
        #if name in self.cache and (self.cache[name] != v1):
            #print "%s: Cached value %s != set value %s" % (name, str(self.cache[name]), str(v1))

        
        