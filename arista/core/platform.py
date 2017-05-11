from __future__ import print_function

import logging
import subprocess
import os
import sys

from collections import OrderedDict, namedtuple

from component import Component
from utils import simulation, incrange
from driver import modprobe, rmmod, KernelDriver

import prefdl

platforms = {}
syseeprom = None

def readPrefdl():
   modprobe('eeprom')
   for addr in ['1-0052']:
      eeprompath = os.path.join('/sys/bus/i2c/drivers/eeprom', addr, 'eeprom')
      if not os.path.exists(eeprompath):
         continue
      try:
         with open(eeprompath) as f:
            logging.debug('reading system eeprom from %s' % eeprompath)
            return prefdl.decode(f)
      except Exception as e:
         logging.warn('could not obtain prefdl from %s' % eeprompath)
         logging.warn('error seen: %s' % e)
   raise RuntimeError("Could not find valid system eeprom")

def getPrefdlData():
   if simulation:
      logging.debug('bypass prefdl reading by returning default values')
      return {'SKU': 'simulation'}

   return readPrefdl().data()

def getSysEeprom():
   global syseeprom
   if not syseeprom:
      syseeprom = getPrefdlData()
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

class Inventory(object):
   def getXcvrs(self):
      return self._xcvrs

   def addXcvrs(self, xcvrs):
      self._xcvrs = xcvrs

   @staticmethod
   def _portToEeprom(port_start, port_end, eeprom_offset):
      eeprom_path = '/sys/class/i2c-adapter/i2c-{0}/{0}-0050/eeprom'
      port_to_eeprom_mapping = {}
      for x in range(port_start, port_end + 1):
         port_to_eeprom_mapping[x] = eeprom_path.format(x + eeprom_offset)
      return port_to_eeprom_mapping

class Platform(Component):
   def __init__(self):
      super(Platform, self).__init__()
      self.addDriver(KernelDriver, 'eeprom')
      self.addDriver(KernelDriver, 'i2c-dev')
      self._inventory = Inventory()

   def setup(self):
      super(Platform, self).setup()
      super(Platform, self).finish()

   def getInventory(self):
      return self._inventory


Xcvrs = namedtuple("Xcvrs", "port_start port_end qsfp_start qsfp_end sfp_start "
                            "sfp_end eeprom_offset port_eeprom_mapping")
