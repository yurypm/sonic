from __future__ import print_function

import os
import logging

from collections import OrderedDict

from ..core.types import Gpio, ResetGpio, NamedGpio
from ..core.utils import sysfsFmtHex, sysfsFmtDec, sysfsFmtStr, simulation

from common import PciComponent, KernelDriver, PciKernelDriver

class ScdKernelDriver(PciKernelDriver):
   def __init__(self, scd):
      super(ScdKernelDriver, self).__init__(scd, 'sonic-support-driver')

   def oldSetup(self):
      # converting internals to old format
      scd = self.component

      qsfpType = 0
      sfpType = 1
      psuType = 2
      muxType = 3

      resets = {}
      for reset in scd.resets:
         assert isinstance(reset, ResetGpio), "Invalid type for reset %s" % reset
         v = resets.setdefault(reset.addr, [])
         v.append((reset.bit, reset.name))

      gpios = {}
      gpio_names = []
      gpio_type = []
      for gpio in scd.gpios:
         assert isinstance(gpio, NamedGpio), "Invalid type for gpio %s" % gpio
         v = gpios.setdefault(gpio.addr, [])
         v.append(Gpio(gpio.bit, gpio.ro, gpio.activeLow))

      # FIXME: works since only psus are gpios and the driver behave strangely
      gpio_type.append(psuType)
      gpio_names.append("psu")
      if len(gpios) > 2:
         gpio_type.append(muxType)
         gpio_names.append("mux")

      for addr, data in scd.qsfps.items():
         gpio_names.append("qsfp%d" % data['id'])
         gpio_type.append(qsfpType)
         gpios[addr] = data['gpios']

      for addr, data in scd.sfps.items():
         gpio_names.append("sfp%d" % data['id'])
         gpio_type.append(sfpType)
         gpios[addr] = data['gpios']

      # generating values

      reset_addrs = sorted(resets)
      reset_names = []
      reset_masks = []

      for addr in reset_addrs:
         mask = 0
         (bits, names) = zip(*resets[addr])
         reset_names.extend(names)
         for bit in bits:
            mask |= (1 << bit)
         reset_masks.append(mask)

      gpio_addrs = sorted(gpios)
      gpio_masks = []
      gpio_ro = []
      gpio_active_low = []

      for addr in gpio_addrs:
         mask = 0
         ro_mask = 0
         active_low_mask = 0
         for (bit, ro, active_low) in gpios[addr]:
            mask |= (1 << bit)
            if ro:
               ro_mask |= (1 << bit)
            if active_low:
               active_low_mask |= (1 << bit)
         gpio_masks.append(mask)
         gpio_ro.append(ro_mask)
         gpio_active_low.append(active_low_mask)

      (led_addrs, led_names) = zip(*scd.leds)
      master_addrs = scd.masters

      files = [
         ('master_addrs', sysfsFmtHex),
         ('reset_addrs', sysfsFmtHex),
         ('reset_names', sysfsFmtStr),
         ('reset_masks', sysfsFmtHex),
         ('gpio_addrs', sysfsFmtHex),
         ('gpio_masks', sysfsFmtHex),
         ('gpio_names', sysfsFmtStr),
         ('gpio_ro', sysfsFmtDec),
         ('gpio_type', sysfsFmtHex),
         ('gpio_active_low', sysfsFmtDec),
         ('led_addrs', sysfsFmtHex),
         ('led_names', sysfsFmtStr)
      ]
      variables = locals()
      return {key: ",".join(map(fmt, variables[key])) for key, fmt in files}

   def writeConfig(self, path, data):
      if simulation:
         print(data)
      else:
         for filename, value in data.items():
            with open(os.path.join(path, filename), 'w') as f:
               f.write(value)

   def getConfigSysfsPath(self):
      return os.path.join(self.getSysfsPath(), 'sonic_support_driver',
                          'sonic_support_driver')
   def setup(self):
      super(ScdKernelDriver, self).setup()
      data = self.oldSetup()
      self.writeConfig(self.getConfigSysfsPath(), data)

   def finish(self):
      logging.debug('applying scd configuration')
      path = self.getSysfsPath()
      self.writeConfig(path, {'init_trigger': '1'})

      # FIXME: the direction should be set properly by the driver
      logging.debug('setting gpio directions')
      data = {
         os.path.join(key, 'direction'): 'out'
         for key in self.component.getSysfsResetNameList()
      }
      self.writeConfig(path, data)
      super(ScdKernelDriver, self).finish()

   def reset(self, value):
      path = self.getSysfsPath()
      if simulation:
         resets = self.component.getSysfsResetNameList()
         logging.debug('reseting devices %s' % resets)
         return
      for reset in self.component.getSysfsResetNameList():
         activeLow = False
         with open(os.path.join(path, reset, 'active_low')) as f:
            activeLow = bool(int(f.read(), 0))
         with open(os.path.join(path, reset, 'value'), 'w') as f:
            f.write('1' if value != activeLow else '0') # logical xor

   def resetIn(self):
      self.reset(True)

   def resetOut(self):
      self.reset(False)

class Scd(PciComponent):
   def __init__(self, addr):
      super(Scd, self).__init__(addr)
      self.addDriver(KernelDriver, 'scd')
      self.addDriver(ScdKernelDriver)
      self.masters = []
      self.resets = []
      self.gpios = []
      self.qsfps = OrderedDict()
      self.sfps = OrderedDict()
      self.leds = []

   def addSmbusMaster(self, addr):
      self.masters += [addr]

   def addSmbusMasterRange(self, addr, count, spacing=0x100):
      self.masters += range(addr, addr + (count + 1) * spacing, spacing)

   def addLed(self, addr, name):
      self.leds += [(addr, name)]

   def addLeds(self, leds):
      self.leds += leds

   def addReset(self, gpio):
      self.resets += [gpio]

   def addResets(self, gpios):
      self.resets += gpios

   def addGpio(self, gpio):
      self.gpios += [gpio]

   def addGpios(self, gpios):
      self.gpios += gpios

   def addQsfp(self, addr, xcvrId):
      self.qsfps[addr] = {
         'id': xcvrId,
         'gpios': [
            Gpio(0, True, True),
            Gpio(2, True, True),
            Gpio(3, True, False),
            Gpio(5, True, False),
            Gpio(6, False, False),
            Gpio(7, False, False),
            Gpio(8, False, True),
         ]
      }

   def addSfp(self, addr, xcvrId):
      self.sfps[addr] = {
         'id': xcvrId,
         'gpios': [
            Gpio(0, True, False),
            Gpio(1, True, False),
            Gpio(2, True, True),
            Gpio(3, True, False),
            Gpio(4, True, False),
            Gpio(5, True, False),
            Gpio(6, False, False),
            Gpio(7, False, False),
            Gpio(8, False, False),
         ]
      }

   def getSysfsResetNameList(self, xcvrs=True):
      entries = [reset.name for reset in self.resets]
      if xcvrs:
         entries += ['qsfp%d_reset' % data['id'] for data in self.qsfps.values()]
         entries += ['sfp%d_reset' % data['id'] for data in self.sfps.values()]
      return entries

