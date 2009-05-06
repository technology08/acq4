# -*- coding: utf-8 -*-
import threading, os, time, re, types
##  import fcntl  ## linux only?
from lib.util.functions import strncmp
from lib.util.configfile import *
from lib.util.MetaArray import MetaArray
from lib.util.advancedTypes import Locker

class DataManager:
    """Class for creating and caching DirHandle objects to make sure there is only one manager object per directory. 
    This class is thread-safe.
    
    ONE OBJECT IS GENERATED BY THE LIBRARY, DO NOT CREATE YOUR OWN!"""
    
    CREATED = False
    
    def __init__(self):
        if DataManager.CREATED:
            raise Exception("Attempted to create more than one DataManager!")
        DataManager.CREATED = True
        self.cache = {}
        #self.m = manager
        self.lock = threading.RLock()
        #self.baseDir = baseDir
        #self.currentDir = ""
    #def time(self):
        #return self.m.time()
        
    def getDirHandle(self, dirName, create=False):
        l = Locker(self.lock)
        dirName = os.path.abspath(dirName)
        if dirName not in self.cache:
            self.cache['dirName'] = DirHandle(self, dirName, create=create)
        return self.cache['dirName']
        
    #def getBaseDir(self):
        #l = Locker(self.lock)
        #return self.getDirHandle("")
        
    #def setBaseDir(self, d):
        #l = Locker(self.lock)
        #self.baseDir = d
           

    #def getCurrentDir(self):
        #l = Locker(self.lock)
        #return self.getDirHandle(self.currentDir, create=True)
        
    #def setCurrentDir(self, d):
        #l = Locker(self.lock)
        #if type(d) is str:
            #self.currentDir = d
        #elif type(d) is DirHandle:
            #self.currentDir = d.baseDir
        #else:
            #raise Exception("Must specify either a directory name or a DirHandle object")

#GLOBAL_DMFACTORY = DataManager("do not copy this password")

#def createDirHandle(baseDir, create=False):
    #global GLOBAL_DMFACTORY
    #return GLOBAL_DMFACTORY.getDirHandle(baseDir, create=create)




class DirHandle:
    def __init__(self, manager, baseDir, create=False):
        self.manager = manager
        self.baseDir = baseDir
        self.indexFile = os.path.join(self.baseDir, '.index')
        self.logFile = os.path.join(self.baseDir, '.log')
        
        self.lock = threading.RLock()
        
        if not os.path.isdir(baseDir):
            if create:
                os.mkdir(baseDir)
            else:
                raise Exception("Directory %s does not exist." % baseDir)
        
        if os.path.isfile(self.indexFile):
            self._readIndex()
        else:
            self.index = {}
            self._writeIndex()
        
    def __del__(self):
        pass
    
    def __getitem__(self, item):
        if type(item) is types.StringType:
            return self.getDir(item)
        elif type(item) is types.TupleType:
            dm = self
            for d in item:
                dm = dm.getDir(d)
            return dm
    
    def _readIndex(self, lock=True):
        l = Locker(self.lock)
        #fd = open(self.indexFile)
        #if lock:
            #pass
            #fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            #self.index = eval(fd.read())
            self.index = readConfigFile(self.indexFile)
        except:
            print "***************Error while reading index file %s!*******************" % self.indexFile
            raise
        #fd.close()
        
    def _writeIndex(self, lock=True):
        l = Locker(self.lock)
        #fd = open(self.indexFile, 'w')
        #if lock:
            #pass
#            fcntl.flock(fd, fcntl.LOCK_EX)
        #fd.write(str(self.index))
        #fd.close()
        writeConfigFile(self.index, self.indexFile)
    
    def logMsg(self, msg, tags={}):
        """Write a message into the log for this directory."""
        l = Locker(self.lock)
        t = time.strftime('[20%y.%m.%d %H:%m:%S]')
        fd = open(self.logFile, 'a')
        #fcntl.flock(fd, fcntl.LOCK_EX)
        fd.write('%s %s\n' % (t, msg))
        fd.close()
    
    def mkdir(self, name, autoIncrement=False, info={}):
        """Create a new subdirectory, return a new DirHandle object. If autoIndex is true, add a number to the end of the dir name if it already exists."""
        l = Locker(self.lock)
        
        if autoIncrement:
            fullName = name+"_000"
        else:
            fullName = name
            
        if autoIncrement:
            files = os.listdir(self.baseDir)
            files = filter(lambda f: re.match(name + r'_\d+$', f), files)
            if len(files) > 0:
                files.sort()
                maxVal = int(files[-1][-3:])
                fullName = name + "_%03d" % (maxVal+1)
            
        newDir = os.path.join(self.baseDir, fullName)
        if os.path.isdir(newDir):
            raise Exception("Directory %s already exists." % newDir)
        
        ndm = self.manager.getDirHandle(newDir, create=True)
        self.addFile(fullName, info)
        return ndm
    
    def getDir(self, subdir, create=False, autoIncrement=False):
        """Return a DirHandle for the specified subdirectory. If the subdir does not exist, it will be created only if create==True"""
        l = Locker(self.lock)
        ndir = os.path.join(self.baseDir, subdir)
        if os.path.isdir(ndir):
            return self.manager.getDirHandle(ndir)
        else:
            if create:
                return self.mkdir(subdir, autoIncrement=autoIncrement)
            else:
                raise Exception('Directory %s does not exist.' % ndir)
        
    def dirExists(self, dirName):
        return os.path.isdir(os.path.join(self.baseDir, dirName))
            
    def getToday(self):
        #yr = self.getDir(time.strftime("20%y"), create=True)
        #mo = yr.getDir(time.strftime("%m"), create=True)
        #return mo.getDir(time.strftime("%d"), create=True)
        return self.getDir(time.strftime("%Y.%m.%d"), create=True)
    
    
    def ls(self):
        """Return a list of all managed files in the directory"""
        l = Locker(self.lock)
        self._readIndex()
        ls = self.index.keys()
        ls.sort(strncmp)
        return ls
    
    def fileInfo(self, file):
        """Return a dict of the meta info stored for file"""
        l = Locker(self.lock)
        self._readIndex()
        if self.index.has_key(file):
            return self.index[file]
        else:
            raise Exception("File %s is not indexed" % file)
    
    def writeFile(self, obj, fileName, info={}, autoIncrement=False):
        """Write a file to this directory using obj.write(fileName), store info in the index."""
        t = self.manager.time()
        l = Locker(self.lock)
        name = fileName
        fullFn = os.path.join(self.baseDir, name)
        appendInfo = False

        if autoIncrement:
            appendInfo = True
            d = 0
            base, ext = os.path.splitext(name)
            while True:
                name = "%s_%04d%s" % (base, d, ext)
                fullFn = os.path.join(self.baseDir, name)
                if not os.path.exists(fullFn):
                    break
                d += 1
        #fd = open(fn, 'w')
        #fcntl.flock(fd, fcntl.LOCK_EX)
        
        obj.write(fullFn)
        
        #fd.close()
        
        if not info.has_key('__object_type__'):
            info['__object_type__'] = obj.typeName()
        if not info.has_key('__timestamp__'):
            info['__timestamp__'] = t
        self.setFileInfo(name, info, append=appendInfo)
        return name
    
    def addFile(self, fileName, info={}, protect=False):
        """Add a pre-existing file into the index. Overwrites any pre-existing info for the file unless protect is True"""
        l = Locker(self.lock)
        fn = os.path.join(self.baseDir, fileName)
        if not (os.path.isfile(fn) or os.path.isdir(fn)):
            raise Exception("File %s does not exist." % fn)
        if protect and (fileName in self.index):
            raise Exception("File %s is already indexed." % fileName)
        self.setFileInfo(fileName, info, append=True)
    
    def setFileInfo(self, fileName, info, append=False):
        l = Locker(self.lock)
        #fd = open(self.indexFile, 'r')
        #fcntl.flock(fd, fcntl.LOCK_EX)
        if append:
            appendConfigFile({fileName: info}, self.indexFile)
        else:
            self._readIndex(lock=False)
            self.index[fileName] = info
            self._writeIndex(lock=False)
        #fd.close()
        
    def setFileAttr(fileName, attr, value):
        l = Locker(self.lock)
        if not self.index.has_key('file'):
            self.setFileInfo(fileName, {attr: value}, append=True)
        else:
            #fd = open(self.indexFile, 'r')
            #fcntl.flock(fd, fcntl.LOCK_EX)
            self._readIndex(lock=False)
            self.index[fileName][attr] = value
            self._writeIndex(lock=False)
            #fd.close()
        
    def parent(self):
        #pdir = re.sub(r'/[^/]+/$', '', self.baseDir)
        pdir = os.path.normpath(os.path.join(self.baseDir, '..'))
        return self.manager.getDirHandle(pdir)

    def getFile(self, fileName):
        ## Todo: Make this function check __object_type__ and dynamically determine what kind of object to create
        info = self.fileInfo(fileName)
        typ = info['__object_type__']
        cls = self.getFileClass(typ)
        return cls.fromFile(fileName=os.path.join(self.baseDir, fileName))
        #return MetaArray(file=os.path.join(self.baseDir, fileName))

    def getFileClass(self, className):
        mod = __import__('lib.filetypes.%s' % modName, fromlist=['*'])
        return getattr(mod, modName)
        
    def dirName(self):
        return os.path.abspath(self.baseDir)


#class FakeDirHandle:
    #def __init__(self, *args):
        #pass    
    #def __del__(self):
        #pass
    
    #def logMsg(self, *args):
        #pass
    
    #def mkdir(self, *args):
        #return self
    
    #def getDir(self, *args):
        #return self
        
    #def dirExists(self, *args):
        #return False
            
    #def getToday(self):
        #return self
    
    #def ls(self):
        #return []
    
    #def fileInfo(self, *args):
        #return {}
    
    #def writeFile(self, *args):
        #pass
    
    #def addFile(self, *args):
        #pass
    
    #def setFileInfo(self, *args):
        #pass
        
    #def setFileAttr(file, *args):
        #pass
        
    #def parent(self):
        #return self
