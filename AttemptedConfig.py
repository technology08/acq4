#configFile = "C:\\Users\\LabPC-SICM\\Documents\\Connor\\acq4\\config\\example\\default.cfg"
#config = OrderedDict()
#cfg = configfile.readConfigFile(configFile)
#config.update(cfg)
#device_dict = OrderedDict()  # all devices loaded via Manager
#
#print(cfg)
#def _loadConfig(cfg):
#
#    for key, val in cfg.items():
#        try:
#            ## configure new devices
#            if key == 'devices':
#                for k in cfg['devices']:
#                    print(f"  === Configuring device '{k}' ===")
#                    try:
#                        conf = cfg['devices'][k]
#                        driverName = conf['driver']
#                        if 'config' in conf:  # for backward compatibility
#                            conf = conf['config']
#                        loadDevice(driverName, conf, k)
#                    except:
#                        raise(f"Error configuring device {k}:")
#                print("=== Device configuration complete ===")
#
#            ## set new storage directory
#            elif key == 'storageDir':
#                print(f"=== Setting base directory: {cfg['storageDir']} ===")
#                self.setBaseDir(cfg['storageDir'])
#
#            elif key == 'defaultCompression':
#                comp = cfg['defaultCompression']
#                try:
#                    if isinstance(comp, tuple):
#                        cstr = comp[0]
#                        assert isinstance(comp[1], int)
#                    else:
#                        cstr = comp
#                    assert cstr in [None, 'gzip', 'szip', 'lzf']
#                except Exception:
#                    raise Exception(
#                        f"'defaultCompression' option must be one of: None, 'gzip', 'szip', 'lzf', ('gzip', 0-9), or ('szip', opts). Got: '{comp}'")
#
#                print(f"=== Setting default HDF5 compression: {comp} ===")
#                from MetaArray import MetaArray
#                MetaArray.defaultCompression = comp
#
#        except:
#           raise("Error in ACQ4 configuration:")
#
#def loadDevice(devClassName, conf, name):
#        """Create a new instance of a device.
#        
#        Parameters
#        ----------
#        devClassName : str
#            The name of a device class that was registered using acq4.devices.registerDeviceClass().
#            See acq4.devices.DEVICE_CLASSES for access to all available device classes.
#        conf : dict
#            A structure passed to the device providing configuration options
#        name : str
#            The name of this device. The instantiated device object will be retrievable using
#            ``Manager.getDevice(name)``
#
#        Returns
#        -------
#        device : Device instance
#            The instantiated device object
#        """
#        devclass = devices.getDeviceClass(devClassName)
#        dev = devclass(conf, conf, name)
#        device_dict[name] = dev  # just to prevent device being collected
#        return dev
#
#_loadConfig(config)
#print(devices)