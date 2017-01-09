from ..core.platform import registerPlatform, Platform
from ..core.driver import KernelDriver
from ..core.utils import incrange
from ..core.types import PciAddr, I2cAddr, Gpio, NamedGpio, ResetGpio

from ..components.common import I2cKernelComponent
from ..components.scd import Scd
from ..components.ds125br import Ds125Br

@registerPlatform('DCS-7050QX-32S')
class Clearlake(Platform):
   def __init__(self):
      super(Clearlake, self).__init__()

      # FIXME: due to an issue with the kernel drivers, the sfp ports are disabled
      # self.sfpRange = incrange(1, 4)
      self.sfpRange = []
      self.qsfp40gAutoRange = incrange(5, 28)
      self.qsfp40gOnlyRange = incrange(29, 36)

      self.addDriver(KernelDriver, 'crow-fan-driver')

      scd = Scd(PciAddr(bus=0x02))
      self.addComponent(scd)

      scd.addComponents([
         I2cKernelComponent(I2cAddr(2, 0x4c), 'max6658'),
         I2cKernelComponent(I2cAddr(3, 0x60), 'crow_cpld'),
         I2cKernelComponent(I2cAddr(3, 0x4e), 'pmbus'), # ucd90120A
         I2cKernelComponent(I2cAddr(5, 0x58), 'pmbus'),
         I2cKernelComponent(I2cAddr(6, 0x58), 'pmbus'),
         I2cKernelComponent(I2cAddr(7, 0x4e), 'pmbus'), # ucd90120A
         Ds125Br(I2cAddr(8, 0xff)), # XXX only repeater for 35-36, mux needed?
      ])

      scd.addSmbusMasterRange(0x8000, 6)

      scd.addLeds([
         (0x6050, 'status'),
         (0x6060, 'fan_status'),
         (0x6070, 'psu1'),
         (0x6080, 'psu2'),
         (0x6090, 'beacon'),
      ])

      scd.addReset(ResetGpio(0x4000, 0, False, 'switch_chip_reset'))

      scd.addGpios([
         NamedGpio(0x5000, 0, True, False, "psu1"),
         NamedGpio(0x5000, 1, True, False, "psu2"),
         NamedGpio(0x6940, 0, False, False, "mux"), # FIXME: oldSetup order/name
      ])

      addr = 0x6100
      for xcvrId in self.qsfp40gAutoRange:
         for laneId in incrange(1, 4):
            scd.addLed(addr, "qsfp%d_%d" % (xcvrId, laneId))
            addr += 0x10

      addr = 0x6720
      for xcvrId in self.qsfp40gOnlyRange:
         scd.addLed(addr, "qsfp%d" % xcvrId)
         addr += 0x30 if xcvrId % 2 else 0x50

      addr = 0x6900
      for xcvrId in self.sfpRange:
         scd.addLed(addr, "sfp%d" % xcvrId)
         addr += 0x10

      addr = 0x5010
      bus = 10
      for xcvrId in sorted(self.qsfp40gAutoRange + self.qsfp40gOnlyRange):
         scd.addQsfp(addr, xcvrId)
         scd.addComponent(I2cKernelComponent(I2cAddr(bus, 0x50), 'sff8436'))
         addr += 0x10
         bus += 1

      addr = 0x5210
      bus = 42
      for xcvrId in sorted(self.sfpRange):
         scd.addSfp(addr, xcvrId)
         scd.addComponent(I2cKernelComponent(I2cAddr(bus, 0x50), 'sff8436'))
         addr += 0x10
         bus += 1

@registerPlatform('DCS-7050QX2-32S')
class ClearlakePlus(Clearlake):
   pass

