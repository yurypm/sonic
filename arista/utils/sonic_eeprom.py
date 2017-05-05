"""
This file provides helper for sonic environment

Currently all arista switches have their eeprom at the same address and use
the same data format. Since it is not an open standard and all our platforms
need this having everything at the same place is easier.

The eeprom plugin end up being just the following

   import arista.utils.sonic
   board = arista.utils.sonic.getTlvInfoDecoder()

"""

import StringIO

from ..core import prefdl

try:
   from sonic_eeprom import eeprom_base
   from sonic_eeprom import eeprom_tlvinfo
except ImportError, e:
   raise ImportError (str(e) + "- required module not found")

class board(eeprom_tlvinfo.TlvInfoDecoder):
   _TLV_INFO_MAX_LEN = 256
   _TLV_HDR_ENABLED = 0

   def __init__(self, name, path, cpld_root, ro):
      self._prefdl_cache = {}
      self.eeprom_path = "/sys/bus/i2c/drivers/eeprom/1-0052/eeprom"
      super(board, self).__init__(self.eeprom_path, 0, '', True)

   def _decode_eeprom(self, e):
      pfdl = self._prefdl_cache.get(e, None)
      if pfdl is not None:
         return pfdl

      pfdl = prefdl.decode(StringIO.StringIO(e))

      self._prefdl_cache[e] = pfdl
      return pfdl

   def decode_eeprom(self, e):
       pfdl = self._decode_eeprom(e)
       return pfdl.show()

   def is_checksum_valid(self, e):
       pfdl = self._decode_eeprom(e)
       return (True, pfdl.getCrc())

   def serial_number_str(self, e):
       pfdl = self._decode_eeprom(e)
       return pfdl.getField('SerialNumber')

   def mgmtaddrstr(self,e):
       pfdl = self._decode_eeprom(e)
       return pfdl.getField('MAC')

def getTlvInfoDecoder():
   return board
