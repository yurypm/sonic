import logging

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

# set simulation to True if not on a Arista box
simulation = True
with open('/proc/cmdline') as f:
   simulation = "Aboot=" not in f.read()

if simulation:
   SMBus = type('SMBus', (NoopObj,), {})
else:
   from smbus import SMBus

