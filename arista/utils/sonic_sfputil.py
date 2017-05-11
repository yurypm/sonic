from ..core import platform as core_platform
from .. import platforms

try:
    from sonic_sfp.sfputilbase import sfputilbase
except ImportError, e:
    raise ImportError (str(e) + "- required module not found")


def getSfpUtil():
    platform = core_platform.getPlatform()
    inventory = platform.getInventory()
    xcvrs = inventory.getXcvrs()

    class sfputil(sfputilbase):
        port_start = xcvrs.port_start
        port_end = xcvrs.port_end
        eeprom_offset = xcvrs.eeprom_offset
        port_to_eeprom_mapping = xcvrs.port_eeprom_mapping
        _qsfp_ports = range(xcvrs.qsfp_start, xcvrs.qsfp_end + 1)
        _sfp_ports = range(xcvrs.sfp_start, xcvrs.sfp_end + 1)

        def __init__(self, port_num):
            sfputilbase.__init__(self, port_num)

    return sfputil
