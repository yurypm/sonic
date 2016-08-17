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

import smbus
import copy

# Control Registers
disableCrc  = (0x06, 0x18)
squelchMode = (0x28, 0x40)

squelch, inputTermination, rxEqualization, outputAmplitude, \
txDeEmphasis = 0, 1, 2, 3, 4

registerMatrix = [[None]*5 for x in range(0, 8)] # 8 channels 5 registers each

baseAddr = 0x0d
for channel in range(0, 8):
   offset = channel * 7
   if (baseAddr + offset) > 0x27:
      offset += 1
   # Each value in the matrix is tuple (RegAddr,RegValue)
   registerMatrix[channel][squelch]          = (baseAddr + squelch
                                                + offset, 0x02)
   registerMatrix[channel][inputTermination] = (baseAddr + inputTermination
                                                + offset, 0x0c)
   registerMatrix[channel][rxEqualization]   = (baseAddr + rxEqualization
                                                + offset, 0x00)
   registerMatrix[channel][outputAmplitude]  = (baseAddr + outputAmplitude
                                                + offset, 0xaa)
   registerMatrix[channel][txDeEmphasis]     = (baseAddr + txDeEmphasis
                                                + offset, 0x00)

repeaterMatrix = {}
repeaterMatrix['qsfp35Ds125Br'] = copy.deepcopy(registerMatrix)
repeaterMatrix['qsfp36Ds125Br'] = copy.deepcopy(registerMatrix)

# Modify device specific registers
repeaterMatrix['qsfp36Ds125Br'][4][outputAmplitude] = \
(repeaterMatrix['qsfp35Ds125Br'][4][outputAmplitude][0], 0xa9)
repeaterMatrix['qsfp36Ds125Br'][5][outputAmplitude] = \
(repeaterMatrix['qsfp35Ds125Br'][5][outputAmplitude][0], 0xa9)
repeaterMatrix['qsfp36Ds125Br'][6][outputAmplitude] = \
(repeaterMatrix['qsfp35Ds125Br'][6][outputAmplitude][0], 0xa9)
repeaterMatrix['qsfp36Ds125Br'][7][outputAmplitude] = \
(repeaterMatrix['qsfp35Ds125Br'][7][outputAmplitude][0], 0xaa)

repeaterMatrix['qsfp35Ds125Br'][4][outputAmplitude] = \
(repeaterMatrix['qsfp36Ds125Br'][4][outputAmplitude][0], 0xa8)
repeaterMatrix['qsfp35Ds125Br'][5][outputAmplitude] = \
(repeaterMatrix['qsfp36Ds125Br'][5][outputAmplitude][0], 0xa9)
repeaterMatrix['qsfp35Ds125Br'][6][outputAmplitude] = \
(repeaterMatrix['qsfp36Ds125Br'][6][outputAmplitude][0], 0xa8)
repeaterMatrix['qsfp35Ds125Br'][7][outputAmplitude] = \
(repeaterMatrix['qsfp36Ds125Br'][7][outputAmplitude][0], 0xa9)

bus = smbus.SMBus(8) # Instantiates i2c-8 aka Master 0 bus 6

for (device, addr) in [
      ("qsfp35Ds125Br", 0x59),
      ("qsfp36Ds125Br", 0x58)
      ]:
   tempMatrix = repeaterMatrix[device]
   for channel in tempMatrix:
      for (regName, regData) in channel:
         bus.write_byte_data(addr, regName, regData)

   bus.write_byte_data(addr, disableCrc[0],  disableCrc[1])
   bus.write_byte_data(addr, squelchMode[0], squelchMode[1])
