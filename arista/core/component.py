from __future__ import print_function

from driver import Driver

class Component(object):
   def __init__(self, **kwargs):
      self.components = []
      self.drivers = []
      for key, value in kwargs.items():
         setattr(self, key, value)
      self.params = kwargs.keys()

   def __str__(self):
      kwargs = ['%s=%s' % (k, getattr(self, k)) for k in self.params]
      return '%s(%s)' % (self.__class__.__name__, ', '.join(kwargs))

   def addComponents(self, components):
      assert all(isinstance(c, Component) for c in components)
      self.components += components
      return self

   def addComponent(self, component):
      assert isinstance(component, Component)
      self.components += [component]
      return self

   def addDriver(self, driverCls, *args, **kwargs):
      assert issubclass(driverCls, Driver)
      self.drivers += [driverCls(self, *args, **kwargs)]
      return self

   def setup(self):
      for driver in self.drivers:
         driver.setup()
      for driver in self.drivers:
         driver.finish()

   def finish(self):
      # underlying component are initialized recursively but require the parent to
      # be fully initialized
      for component in self.components:
         component.setup()
      for component in self.components:
         component.finish()

   def clean(self):
      for component in reversed(self.components):
         component.clean()
      for driver in reversed(self.drivers):
         driver.clean()

   def resetIn(self):
      for component in reversed(self.components):
         component.resetIn()
      for driver in reversed(self.drivers):
         driver.resetIn()

   def resetOut(self):
      for driver in self.drivers:
         driver.resetOut()
      for component in self.components:
         component.resetOut()

   def _dumpDrivers(self, depth, prefix):
      if len(self.drivers) == 1:
         self.drivers[0].dump(prefix=' => ')
      elif self.drivers:
         spacer = ' ' * (depth * 3)
         print('%s%sdrivers:' % (spacer, prefix))
         for driver in self.drivers:
            driver.dump(depth + 1)

   def _dumpNode(self, depth, prefix):
      depth += 1
      spacer = ' ' * (depth * 3)
      if self.drivers:
         self._dumpDrivers(depth, prefix)
      print('%s%scomponents:' % (spacer, prefix))
      for component in self.components:
         component.dump(depth + 1)

   def dump(self, depth=0, prefix=' - '):
      spacer = ' ' * (depth * 3)
      end = '' if len(self.drivers) == 1 else '\n'
      print('%s%s%s' % (spacer, prefix,self), end=end)
      if self.components:
         self._dumpNode(depth, prefix)
      else:
         self._dumpDrivers(depth, prefix)

