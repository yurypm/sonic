from ..core.platform import registerPlatform, Inventory, Platform, Xcvrs
from ..core.driver import KernelDriver
from ..core.utils import incrange
from ..core.types import PciAddr, I2cAddr, Gpio, NamedGpio, ResetGpio

from ..components.common import I2cKernelComponent
from ..components.scd import Scd
from ..components.ds125br import Ds125Br
from ..components.ds460 import Ds460

@registerPlatform('DCS-7260CX3-64')
class Gardena(Platform):
   def __init__(self):
      super(Gardena, self).__init__()

      self._inventory.addXcvrs(Xcvrs(0, 65, 0, 63, 64, 65, 9,
                                     Inventory._portToEeprom(0, 65, 10)))

      self.sfpRange = incrange(65, 66)
      self.qsfpRange = incrange(1, 64)

      self.addDriver(KernelDriver, 'rook-fan-cpld')
      self.addDriver(KernelDriver, 'rook-led-driver')

      scd = Scd(PciAddr(bus=0x06), newDriver=True)
      self.addComponent(scd)

      scd.addComponents([
         I2cKernelComponent(I2cAddr(1, 0x4c), 'max6658'),
         I2cKernelComponent(I2cAddr(3, 0x58), 'pmbus'),
         I2cKernelComponent(I2cAddr(4, 0x58), 'pmbus'),
      ]) # Incomplete

      scd.addSmbusMasterRange(0x8000, 8, 0x80)

      scd.addResets([
         ResetGpio(0x4000, 0, False, 'switch_chip_reset'),
         ResetGpio(0x4000, 1, False, 'switch_chip_pcie_reset'),
         ResetGpio(0x4000, 2, False, 'security_asic_reset'),
      ])

      scd.addGpios([
         NamedGpio(0x5000, 0, True, False, "psu1_present"),
         NamedGpio(0x5000, 1, True, False, "psu2_present"),
      ])

      addr = 0x6100
      for xcvrId in self.qsfpRange:
         for laneId in incrange(1, 4):
            scd.addLed(addr, "qsfp%d_%d" % (xcvrId, laneId))
            addr += 0x10

      addr = 0x7100
      for xcvrId in self.sfpRange:
         scd.addLed(addr, "sfp%d" % xcvrId)
         addr += 0x10

      addr = 0xA010
      bus = 9
      for xcvrId in sorted(self.qsfpRange):
         scd.addQsfp(addr, xcvrId)
         scd.addComponent(I2cKernelComponent(I2cAddr(bus, 0x50), 'sff8436'))
         addr += 0x10
         bus += 1

      addr = 0xA400
      bus = 7
      for xcvrId in sorted(self.sfpRange):
         scd.addSfp(addr, xcvrId)
         scd.addComponent(I2cKernelComponent(I2cAddr(bus, 0x50), 'sff8436'))
         addr += 0x10
         bus += 1

      cpld = Scd(PciAddr(bus=0xff, device=0x0b, func=3), newDriver=True)
      self.addComponent(cpld)

      cpld.addSmbusMasterRange(0x8000, 4, 0x80, 4)
      cpld.addComponents([
         I2cKernelComponent(I2cAddr(73, 0x4c), 'max6658'),
         I2cKernelComponent(I2cAddr(74, 0x4e), 'pmbus'),
         I2cKernelComponent(I2cAddr(85, 0x60), 'rook_cpld'),
         I2cKernelComponent(I2cAddr(88, 0x20), 'rook_leds'),
         I2cKernelComponent(I2cAddr(88, 0x48), 'lm73'),
      ])
