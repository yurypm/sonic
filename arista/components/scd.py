from __future__ import print_function, with_statement

import os
import logging

from collections import OrderedDict

from ..core.types import Gpio, ResetGpio, NamedGpio
from ..core.utils import sysfsFmtHex, sysfsFmtDec, sysfsFmtStr, simulateWith, \
                         inSimulation

from common import PciComponent, KernelDriver, PciKernelDriver

class ScdHwmonKernelDriver(PciKernelDriver):
   def __init__(self, scd):
      super(ScdHwmonKernelDriver, self).__init__(scd, 'scd-hwmon')

   def writeConfigSim(self, path, data):
      for filename, value in data.items():
         logging.info('writting data under %s : %r',
                      os.path.join(path, filename), value)

   @simulateWith(writeConfigSim)
   def writeConfig(self, path, data):
      for filename, value in data.items():
         try:
            with open(os.path.join(path, filename), 'w') as f:
               f.write(value)
         except IOError as e:
            logging.error('%s %s', e.filename, e.strerror)

   def writeObjects(self, components):
      PAGE_SIZE = 4096
      data = []
      data_size = 0

      for entry in components:
         entry_size = len(entry) + 1
         if entry_size + data_size > PAGE_SIZE:
            self.writeConfig(self.getSysfsPath(), {'new_object': '\n'.join(data)})
            data_size = 0
            data = []
         data.append(entry)
         data_size += entry_size

      if data:
         self.writeConfig(self.getSysfsPath(), {'new_object': '\n'.join(data)})

   def setup(self):
      super(ScdHwmonKernelDriver, self).setup()

      scd = self.component
      data = []

      for i, addr in enumerate(scd.masters, 0):
         data += ["master %#x %d" % (addr, i)]

      for addr, name in scd.leds:
         data += ["led %#x %s" % (addr, name)]

      for addr, info in scd.qsfps.items():
         data += ["qsfp %#x %u" % (addr, info['id'])]

      for addr, info in scd.sfps.items():
         data += ["sfp %#x %u" % (addr, info['id'])]

      for reset in scd.resets:
         data += ["reset %#x %s %u" % (reset.addr, reset.name, reset.bit)]

      for gpio in scd.gpios:
         data += ["gpio %#x %s %u %d %d" % (gpio.addr, gpio.name, gpio.bit,
                                            int(gpio.ro), int(gpio.activeLow))]

      self.writeObjects(data)

   def finish(self):
      logging.debug('applying scd configuration')
      path = self.getSysfsPath()
      self.writeConfig(path, {'init_trigger': '1'})
      super(ScdHwmonKernelDriver, self).finish()

   def resetSim(self, value):
      resets = self.component.getSysfsResetNameList()
      logging.debug('reseting devices %s', resets)

   @simulateWith(resetSim)
   def reset(self, value):
      path = self.getSysfsPath()
      for reset in self.component.getSysfsResetNameList():
         with open(os.path.join(path, reset), 'w') as f:
            f.write('1' if value else '0')

   def resetIn(self):
      self.reset(True)

   def resetOut(self):
      self.reset(False)

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

      gpios = OrderedDict()
      gpio_names = []
      gpio_type = []
      for gpio in scd.gpios:
         assert isinstance(gpio, NamedGpio), "Invalid type for gpio %s" % gpio
         v = gpios.setdefault(gpio.addr, [])
         v.append(Gpio(gpio.bit, gpio.ro, gpio.activeLow))

      # FIXME: works since only psus are gpios and the driver behave strangely
      gpio_type.append(psuType)
      gpio_names.append("psu")
      if len(scd.gpios) > 2:
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

      gpio_addrs = gpios.keys()
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
      if inSimulation():
         print(data)
      else:
         for filename, value in data.items():
            try:
               with open(os.path.join(path, filename), 'w') as f:
                  f.write(value)
            except IOError as e:
               logging.error('%s %s' % (e.filename, e.strerror))

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
         os.path.join(name, 'direction'): 'out'
         for name, ro in self.component.allGpios() if not ro
      }
      self.writeConfig(path, data)
      super(ScdKernelDriver, self).finish()

   def reset(self, value):
      path = self.getSysfsPath()
      if inSimulation():
         resets = self.component.getSysfsResetNameList()
         logging.debug('reseting devices %s', resets)
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
   def __init__(self, addr, newDriver=False):
      super(Scd, self).__init__(addr)
      self.addDriver(KernelDriver, 'scd')
      if newDriver:
         self.addDriver(ScdHwmonKernelDriver)
      else:
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

   def allGpios(self):
      def zipXcvr(xcvrType, gpio_names, entries):
         res = []
         for data in entries.values():
            for name, gpio in zip(gpio_names, data['gpios']):
               res += [ ("%s%d_%s" % (xcvrType, data['id'], name), gpio.ro) ]
         return res

      sfp_names = [
         "rxlos", "txfault", "present", "rxlos_changed", "txfault_changed",
         "present_changed", "txdisable", "rate_select0", "rate_select1",
      ]

      qsfp_names = [
         "interrupt", "present", "interrupt_changed", "present_changed",
         "lp_mode", "reset", "modsel",
      ]

      gpios = []
      gpios += zipXcvr("sfp", sfp_names, self.sfps)
      gpios += zipXcvr("qsfp", qsfp_names, self.qsfps)
      gpios += [ (gpio.name, gpio.ro) for gpio in self.gpios ]
      gpios += [ (reset.name, False) for reset in self.resets ]
      return gpios

   def getSysfsResetNameList(self, xcvrs=True):
      entries = [reset.name for reset in self.resets]
      if xcvrs:
         entries += ['qsfp%d_reset' % data['id'] for data in self.qsfps.values()]
      return entries

