import logging
import copy

from ..core.utils import SMBus
from common import I2cComponent

class Ds125Br(I2cComponent):
   def __init__(self, addr):
      super(Ds125Br, self).__init__(addr, channels=8)

   def createRepeaterMatrix(self):
      squelch, inputTermination, rxEqualization, outputAmplitude, txDeEmphasis = \
               0, 1, 2, 3, 4
      regMat = [[None] * 5] * self.channels

      baseAddr = 0x0d
      for channel in range(0, self.channels):
         offset = channel * 7
         if (baseAddr + offset) > 0x27:
            offset += 1
         # Each value in the matrix is tuple (RegAddr,RegValue)
         regMat[channel][squelch]          = (baseAddr + squelch
                                                      + offset, 0x02)
         regMat[channel][inputTermination] = (baseAddr + inputTermination
                                                      + offset, 0x0c)
         regMat[channel][rxEqualization]   = (baseAddr + rxEqualization
                                                      + offset, 0x00)
         regMat[channel][outputAmplitude]  = (baseAddr + outputAmplitude
                                                      + offset, 0xaa)
         regMat[channel][txDeEmphasis]     = (baseAddr + txDeEmphasis
                                                      + offset, 0x00)

      repeaterMatrix = {}
      repeaterMatrix['qsfp35Ds125Br'] = copy.deepcopy(regMat)
      repeaterMatrix['qsfp36Ds125Br'] = copy.deepcopy(regMat)

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

      return repeaterMatrix

   def setup(self):
      logging.debug('setting up ds125br repeaters')

      # Control Registers
      disableCrc  = (0x06, 0x18)
      squelchMode = (0x28, 0x40)

      bus = SMBus(self.addr.bus)

      repeaterMatrix = self.createRepeaterMatrix()
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

   def finish(self):
      pass

   def clean(self):
      pass

