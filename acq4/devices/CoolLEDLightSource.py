import glob
import sys
from threading import Thread
from time import sleep

import serial
from pyqtgraph.util.mutex import Mutex

from acq4.devices.LightSource import LightSource
from acq4.util.HelpfulException import HelpfulException


class CoolLEDLightSource(LightSource):
    def __init__(self, dm, config, name):
        super(CoolLEDLightSource, self).__init__(dm, config, name)
        if "port" in config:
            self._port = config["port"]
        else:
            self._port = self._detectCoolLEDPort()
        self._devConn = serial.Serial(self._port, 57600, timeout=0)
        self.addSource("A", {"adjustableBrightness": True})
        self.addSource("B", {"adjustableBrightness": True})
        self.addSource("C", {"adjustableBrightness": True})
        self._writeBuffer = ""
        self._writeLock = Mutex()

        self._ioThread = Thread(target=self._ioAsNeeded)
        self._ioThread.start()

    @staticmethod
    def _detectCoolLEDPort():
        if sys.platform.startswith("win"):
            ports = ["COM%s" % (i + 1) for i in range(10)]
        elif sys.platform.startswith("linux") or sys.platform.startswith("cygwin"):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob("/dev/tty[A-Za-z]*")
        elif sys.platform.startswith("darwin"):
            ports = glob.glob("/dev/tty.*")
        else:
            raise EnvironmentError("Unsupported platform")

        for port in ports:
            try:
                conn = serial.Serial(port, timeout=0.1)
                if conn.readline()[0:7] == b"CoolLED" or conn.readline() == 4:
                    conn.close()
                    return port
                elif conn.readline() == b"":
                    conn.write("XVER\n".encode("utf-8"))
                    out = conn.read(7)
                    if out == b"XFW_VER":
                        conn.close()
                        return port
                else:
                    conn.close()
            except (OSError, serial.SerialException):
                pass

        raise HelpfulException("Could not detect a usb CoolLED light source. Are the drivers installed?")

    def _ioAsNeeded(self):
        while True:
            if len(self._writeBuffer) > 0:
                with self._writeLock:
                    dataToWrite = self._writeBuffer
                    self._writeBuffer = ""
                self._devConn.write(dataToWrite.encode("utf-8"))
            while self._devConn.out_waiting > 0:
                self._handleData(self._devConn.readline().decode("utf-8"))
            sleep(0.2)

    def _requestStatus(self):
        self._sendCommand("CSS?")

    def _sendCommand(self, cmd):
        with self._writeLock:
            self._writeBuffer += f"{cmd}\n"

    def _handleData(self, resp):
        print(f"CoolLED resp: {resp}")
        try:
            self.sourceConfigs["A"]["active"] = (resp[5] == "N")
            self.sourceConfigs["A"]["brightness"] = int(resp[6:9])
            self.sourceConfigs["B"]["active"] = (resp[11] == "N")
            self.sourceConfigs["B"]["brightness"] = int(resp[12:15])
            self.sourceConfigs["C"]["active"] = (resp[17] == "N")
            self.sourceConfigs["C"]["brightness"] = int(resp[18:21])
            # Current uses of this signal ignore the source name
            self.sigLightChanged.emit(self, "A")
        except (IndexError, ValueError):
            pass

    @staticmethod
    def _makeSetterCommand(channel, onOrOff, brightness):
        onOrOff = "N" if onOrOff else "F"
        return f"CSS{channel}S{onOrOff}{brightness:03d}"

    def quit(self):
        self._devConn.close()

    def sourceActive(self, name):
        return self.sourceConfigs[name]["active"]

    def setSourceActive(self, name, active):
        cmd = self._makeSetterCommand(name, active, int(self.getSourceBrightness(name) * 100))
        self._sendCommand(cmd)

    def getSourceBrightness(self, name):
        return self.sourceConfigs[name]["brightness"] / 100.

    def setSourceBrightness(self, name, percent):
        cmd = self._makeSetterCommand(name, percent > 0, int(percent * 100))
        self._sendCommand(cmd)
