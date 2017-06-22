
import logging

from functools import wraps

def sysfsFmtHex(x):
   return "0x%08x" % x

def sysfsFmtDec(x):
   return "%d" % x

def sysfsFmtStr(x):
   return str(x)

def incrange(start, stop):
   return range(start, stop + 1)

class NoopObj(object):
   def __init__(self, *args, **kwargs):
      self.name = self.__class__.__name__
      self.classStr = '%s(%s)' % (self.name, self._fmtArgs(*args, **kwargs))
      logging.debug(self.classStr)

   def _fmtArgs(self, *args, **kwargs):
      kw = ['%s=%s' % (k,v) for k, v in kwargs.items()]
      return ', '.join(map(str, args) + kw)

   def noop(self, attr):
      def wrapped(*args, **kwargs):
         funcStr = '%s(%s)' % (attr, self._fmtArgs(*args, **kwargs))
         logging.debug('%s.%s' % (self.classStr, funcStr))
      return wrapped

   def __getattr__(self, attr):
      return self.noop(attr)

CMDLINE_PATH = '/proc/cmdline'

cmdlineDict = {}
def getCmdlineDict():
   global cmdlineDict

   if cmdlineDict:
      return cmdlineDict

   data = {}
   with open(CMDLINE_PATH) as f:
      for entry in f.read().split():
         idx = entry.find('=')
         if idx == -1:
            data[entry] = None
         else:
            data[entry[:idx]] = entry[idx+1:]

   cmdlineDict = data
   return data

# debug flag, if enabled should use the most tracing possible
debug = False

# force simulation to be True if not on a Arista box
simulation = True

# simulation related globals
SMBus = None

def inDebug():
   return debug

def inSimulation():
   return simulation

def simulateWith(simulatedFunc):
   def simulateThisFunc(func):
      @wraps(func)
      def funcWrapper(*args, **kwargs):
         if inSimulation():
            return simulatedFunc(*args, **kwargs)
         return func(*args, **kwargs)
      return funcWrapper
   return simulateThisFunc

def libraryInit():
   global simulation, debug, SMBus

   cmdline = getCmdlineDict()
   if "Aboot" in cmdline:
      simulation = False

   if "arista-debug" in cmdline:
      debug = True

   if simulation:
      SMBus = type('SMBus', (NoopObj,), {})
   else:
      from smbus import SMBus

libraryInit()

