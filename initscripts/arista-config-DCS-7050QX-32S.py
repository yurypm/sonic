#!/usr/bin/env python
# Copyright (c) 2016 Arista Networks, Inc.  All rights reserved.
# Arista Networks, Inc. Confidential and Proprietary.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
from collections import namedtuple

# Scd PCI address
scd_address = "0000:02:00.0"

# Define static types instead of enums
qsfpType = 0
sfpType = 1
psuType = 2
muxType = 3

# Data structures for holding mappings of hardware addresses to
# software functionality
resets = {
   0x4000 : [
      (0, "switch_chip_reset"),
      ],
   }

smbus_masters = range(0x8000, 0x8500 + 1, 0x100)

leds = [
   (0x6050, "status"),
   (0x6060, "fan_status"),
   (0x6070, "psu1"),
   (0x6080, "psu2"),
   (0x6090, "beacon"),
   ]

addr = 0x6100
for i in range(5, 28 + 1):
   for j in range(1, 4 + 1):
      leds.append((addr, "qsfp%d_%d" % (i, j)))
      addr += 0x10

addr = 0x6720
for i in range(29, 36 + 1):
   leds.append((addr, "qsfp%d" % i))
   if i % 2:
      addr += 0x30
   else:
      addr += 0x50

addr = 0x6900
for i in range(1, 4 + 1):
   leds.append((addr, "sfp%d" % i))
   addr += 0x10

Gpio = namedtuple("Gpio", ["addr", "ro", "activeLow"])
NamedGpio = namedtuple("Gpio", Gpio._fields + ("name",) )

gpio_names = []
gpio_type = []
scd_gpios = {
   0x5000 : [
      Gpio(0, True, False),
      Gpio(1, True, False),
      ],
}
gpio_names.append("psu")
gpio_type.append(psuType)


addr = 0x5010
for i in range(5, 36 + 1):
   gpio_names.append("qsfp%d" % i)
   gpio_type.append(qsfpType)
   scd_gpios[addr] = [
      Gpio(0, True, True),
      Gpio(2, True, True),
      Gpio(3, True, False),
      Gpio(5, True, False),
      Gpio(6, False, False),
      Gpio(7, False, False),
      Gpio(8, False, True),
      ]
   addr += 0x10

addr = 0x5210
for i in range(1, 4 + 1):
   gpio_names.append("sfp%d" % i)
   gpio_type.append(sfpType)
   scd_gpios[addr] = [
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
   addr += 0x10

#add mux
scd_gpios[0x6940] = [
      Gpio(0, False, False),
      ]
gpio_names.append("mux")
gpio_type.append(muxType)

# Process hardware mappings into separate lists so we can manipulate
# them conveniently
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

(led_addrs, led_names) = zip(*leds)

gpio_addrs = sorted(scd_gpios)
gpio_masks = []
gpio_ro = []
gpio_active_low = []
for addr in gpio_addrs:
   mask = 0
   ro_mask = 0
   active_low_mask = 0
   for (bit, ro, active_low) in scd_gpios[addr]:
      mask |= (1 << bit)
      if ro:
         ro_mask |= (1 << bit)
      if active_low:
         active_low_mask |= (1 << bit)
   gpio_masks.append(mask)
   gpio_ro.append(ro_mask)
   gpio_active_low.append(active_low_mask)

# Generate comma-separated strings in the right format from the lists
# above to be written to sysfs
def formatHex( x ):
   return "0x%08x" % x

def formatDec( x ):
   return "%d" % x

reset_addrs = ",".join(map(formatHex, reset_addrs))
reset_names = ",".join(reset_names)
reset_masks = ",".join(map(formatHex, reset_masks))

master_addrs = ",".join(map(formatHex, smbus_masters))

led_addrs = ",".join(map(formatHex, led_addrs))
led_names = ",".join(led_names)

gpio_addrs = ",".join(map(formatHex, gpio_addrs))
gpio_masks = ",".join(map(formatHex, gpio_masks))
gpio_names = ",".join(gpio_names)
gpio_ro = ",".join(map(formatHex, gpio_ro))
gpio_type = ",".join(map(formatHex, gpio_type))
gpio_active_low = ",".join(map(formatHex, gpio_active_low))

init_trigger = 1

# Install and initialize scd driver
os.system("modprobe scd")
os.system("modprobe sonic-support-driver")
os.chdir("/sys/bus/pci/drivers/scd/%s/sonic_support_driver/sonic_support_driver"
         % scd_address)


for fname in [
   "reset_addrs", "reset_names", "reset_masks",
   "master_addrs",
   "led_addrs", "led_names",
   "gpio_addrs", "gpio_masks", "gpio_names", "gpio_ro", "gpio_type",
   "gpio_active_low",
   ]:
   with open(fname, "w") as f:
      f.write(str(eval(fname)))

os.chdir("/sys/bus/pci/drivers/scd/%s" % scd_address)
fname = "init_trigger"
with open(fname, "w") as f:
   f.write(str(eval(fname)))

os.system("modprobe crow-fan-driver")

# Temperature sensors
os.system("modprobe lm90")

# PMBus devices
for (bus, addr) in [
   (3, 0x4e),
   (5, 0x58),
   (6, 0x58),
   (7, 0x4e),
   ]:
   with open("/sys/bus/i2c/devices/i2c-%d/new_device" % bus, "w") as f:
      f.write("pmbus 0x%02x" % addr)

# EEPROM
os.system("modprobe eeprom")

# QSFP+
bus = 10
addr = 0x50
for i in range(32):
   with open("/sys/bus/i2c/devices/i2c-%d/new_device" % bus, "w") as f:
      f.write("sff8436 0x%02x" % addr)
   bus += 1

# SFP+
bus = 42
addr = 0x50
for i in range(4):
   with open("/sys/bus/i2c/devices/i2c-%d/new_device" % bus, "w") as f:
      f.write("sff8436 0x%02x" % addr)
   bus += 1

# Take QSFPs out of reset and assert modsel
for i in range(5, 36 + 1):
   with open("qsfp%d_reset/direction" % i, "w") as f:
      f.write("out")
   with open("qsfp%d_reset/value" % i, "w") as f:
      f.write("0")
   with open("qsfp%d_modsel/direction" % i, "w") as f:
      f.write("out")
   with open("qsfp%d_modsel/value" % i, "w") as f:
      f.write("1")

# Configure the switch asic pin
with open("switch_chip_reset/direction", "w") as f:
   f.write("out")

