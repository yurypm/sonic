from __future__ import print_function

import logging
import subprocess
import os
import sys

from collections import OrderedDict

from component import Component
from utils import simulation
from driver import modprobe, rmmod, KernelDriver

platforms = {}
syseeprom = None

def readPrefdl():
   if simulation:
      logging.debug('bypass prefdl reading by returning default values')
      return {'SKU': 'simulation'}

   # FIXME: currently a hack that import an out of module script
   #        the prefdl should be added as part of the module
   prefdl = {}
   execfile('/usr/share/arista/prefdl', prefdl)

   modprobe('eeprom')
   for addr in ['1-0052']:
      eeprompath = os.path.join('/sys/bus/i2c/drivers/eeprom', addr, 'eeprom')
      if not os.path.exists(eeprompath):
         continue
      try:
         with open(eeprompath) as f:
            logging.debug('reading system eeprom from %s' % eeprompath)
            return prefdl['decode'](f).data()
      except Exception as e:
         logging.warn('could not obtain prefdl from %s' % eeprompath)
         logging.warn('error seen: %s' % e)

   raise RuntimeError("Could not find valid system eeprom")

def getSysEeprom():
   global syseeprom
   if not syseeprom:
      syseeprom = readPrefdl()
      assert 'SKU' in syseeprom
   return syseeprom

def detectPlatform():
   return getSysEeprom()['SKU']

def getPlatform(name=None):
   if name == None:
      name = detectPlatform()
   return platforms[name]()

def getPlatforms():
   return platforms

def registerPlatform(sku):
   global platforms
   def wrapper(cls):
      platforms[sku] = cls
      return cls
   return wrapper

class Platform(Component):
   def __init__(self):
      super(Platform, self).__init__()
      self.addDriver(KernelDriver, 'eeprom')
      self.addDriver(KernelDriver, 'i2c-dev')

   def setup(self):
      super(Platform, self).setup()
      super(Platform, self).finish()
