#!/usr/bin/env python3
'''
lsusb for MacOS after https://github.com/jlhonora/lsusb

MacBook-Pro-apple-2:~ jno$ system_profiler SPUSBDataType
2018-12-19 15:14:49.583 system_profiler[96589:1580584] SPUSBDevice: IOCreatePlugInInterfaceForService failed 0xe00002be
USB:

    USB 3.0 Bus:

      Host Controller Driver: AppleUSBXHCISPTLP
      PCI Device ID: 0x9d2f
      PCI Revision ID: 0x0021
      PCI Vendor ID: 0x8086

        Apple USB Ethernet Adapter:

          Product ID: 0x1402
          Vendor ID: 0x05ac (Apple Inc.)
          Version: 0.01
          Serial Number: 267DCA
          Speed: Up to 480 Mb/sec
          Manufacturer: Apple Inc.
          Location ID: 0x14500000 / 4
          Current Available (mA): 500
          Current Required (mA): 250
          Extra Operating Current (mA): 0

        iBridge:

          Product ID: 0x8600
          Vendor ID: 0x05ac (Apple Inc.)
          Version: 1.01
          Manufacturer: Apple Inc.
          Location ID: 0x14100000

    USB 3.1 Bus:

      Host Controller Driver: AppleUSBXHCIAR
      PCI Device ID: 0x15d4
      PCI Revision ID: 0x0002
      PCI Vendor ID: 0x8086
      Bus Number: 0x01

    USB 3.1 Bus:

      Host Controller Driver: AppleUSBXHCIAR
      PCI Device ID: 0x15d4
      PCI Revision ID: 0x0002
      PCI Vendor ID: 0x8086
      Bus Number: 0x00


'''
from __future__ import print_function

import sys
import subprocess

EXECUTABLE='system_profiler' # /usr/sbin/system_profiler
DATA_TYPE = 'SPUSBDataType'
DEFAULT_VENDOR = 'Apple Inc.'

def run(*av, **kw):
    try:
        kw['stdout'] = subprocess.PIPE
        kw['stderr'] = subprocess.PIPE
        r = subprocess.run((EXECUTABLE,) + av, **kw)
    except Exception as e:
        print('Cannot run {!r}: {!r}'.format(EXECUTABLE, e), file=sys.stderr)
        sys.exit(1)
    if r.returncode:
        print('Error {!r} in {!r}: {}'.format(r.returncode, EXECUTABLE, r.stderr))
        sys.exit(r.returncode)
    return r.stdout.decode()

def supported():
    return len([1 for line in run('-listDataTypes').splitlines()
                if line.strip() == DATA_TYPE]) > 0

def fetch():
    if not supported():
        raise NotImplementedError('No way to iterate ' + DATA_TYPE + ' data')
    return [i for i in filter(None, run(DATA_TYPE).strip().splitlines())]

class NamedAttributedObjectWithList(object):

    def __init__(self, name):
        self.name = name
        self.attr = {}
        self.list = []

    def set(self, name, value):
        self.attr[name] = value
        return self

    def add(self, entry):
        self.list.append(entry)
        # print('{}.{} += {!r}'.format(self.__class__.__name__, self.name, entry))
        return self

    def __repr__(self):
        return '<{}:{}:{}{}{}{}>'.format(
            self.__class__.__name__, self.name or '<ROOT>',
            ' ' if self.attr else '',
            ' '.join(['{!r}={!r}'.format(k, self.attr[k])
                      for k in sorted(self.attr)])
            if self.attr else '',
            ' 'if self.list else '',
            ' '.join([str(e) for e in self.list])
            if self.list else '')

    def __len__(self):
        return len(self.list)

#end class NamedAttributedObjectWithList

class USBDevice(NamedAttributedObjectWithList):
    def __init__(self, bus, name):
        super(USBDevice, self).__init__(name)
        self.bus = bus

    def __str__(self):
        # Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
        serNr = self.attr.get('Serial Number', '')
        serNr = ', Serial: {}'.format(serNr) if serNr else ''
        if 'Product ID' in self.attr:
            busId = '{:03d}'.format(int(self.attr.get('Location ID',
                                                      self.bus.attr.get('Bus Number',
                                                                        '0') + '/x')
                                        .split('/', 1)[0],
                                        16) >> 24)
            devId = '{:03x}'.format(int(self.attr.get('Location ID')
                                        .split('/', 1)[-1]
                                        .strip())
                    ) if 'Location ID' in self.attr and \
                         '/' in self.attr['Location ID'] \
                      else '000'
            vndId = self.attr.get('Vendor ID', '0x1d6b (xx)').split(' ', 1)[0][2:]
            prdId = self.attr.get('Product ID', '0x????')[2:]
            mfrNm = self.attr.get('Manufacturer',
                               self.attr.get('Vendor ID',
                                             'xxx ({})'.format(DEFAULT_VENDOR))
                               .split(' ', 1)[-1].strip()
                    )
            locId = self.attr.get('Location ID', '0x00000000')
        else: # fake entry for "root hub"
            busId = '{:03d}'.format(int(self.bus.attr.get('Bus Number', '3e7'), 16))
            devId = '001'
            vndId = '05ac' # or 1d6b ???
            prdId = self.attr.get('Host Controller Driver',
                                  self.attr.get('Product ID', '0x????')
                                 ).strip()
            prdId = dict(OHCI='8005', EHCI='8006', XHCI='8007',
                         AppleUSBXHCISPTLP='8007',
                         AppleUSBXHCIAR='8007').get(prdId, prdId)
            mfrNm = '({})'.format(DEFAULT_VENDOR) # or 'Linux Foundation' ???
            locId = '0x{:02x}000000'.format(int(busId, 10))
            serNr = ', ' + self.attr.get('Host Controller Driver', '???')

        return 'Bus {bus} Device {dev}: ID {vnd}:{prd} {mfr} {dsc}{ser}'.format(
            bus=busId, dev=devId, vnd=vndId, prd=prdId,
            dsc=self.name,
            mfr=mfrNm.strip().strip('()').strip(),
            ser=serNr,
        )
#end class USBDevice

class USBBus(NamedAttributedObjectWithList):
    def __init__(self, system, name):
        super(USBBus, self).__init__(name)
        self.system = system

    def add(self, entry):
        if not self.list:
            self.list.append(USBDevice(self, self.name))
            self.list[0].attr.update(self.attr)
        if entry is not None:
            self.list.append(entry)

    def __str__(self):
        return '\n'.join([str(dev) for dev in self.list])
#end class USBBus

class USB(NamedAttributedObjectWithList):
    def __init__(self):
        super(USB, self).__init__(None)

    def __str__(self):
        return '\n'.join([str(bus) for bus in self.list])
#end class USB

def parse_dev(bus, name, text):
    dev = USBDevice(bus, name)
    while text:
        line = text.pop(0).strip()
        if line.endswith(':'):
            text.insert(0, line)
            bus.add(dev)
            break
        name, value = tuple(word.strip() for word in line.split(':', 1))
        dev.set(name, value)
    else:
        bus.add(dev)

def parse_bus(sys, name, text):
    bus = USBBus(sys, name)
    while text:
        line = text.pop(0).strip()
        if line.endswith('Bus:'):
            text.insert(0, line)
            bus.add(None)
            sys.add(bus)
            break
        if line.endswith(':'):
            parse_dev(bus, line[:-1], text)
            continue
        name, value = tuple(word.strip() for word in line.split(':', 1))
        bus.set(name, value)
    else:
        bus.add(None)
        sys.add(bus)

def parse(text=None):
    if text is None:
        return parse(fetch())
    assert text and text[0] == 'USB:', text
    text.pop(0)
    usb = USB()
    while text:
        line = text.pop(0).strip()
        if line.endswith('Bus:'):
            parse_bus(usb, line[:-1], text)
            continue
        name, value = tuple(word.strip() for word in line.split(':', 1))
        usb.set(name, value)
    return usb

if __name__ == '__main__':
    usb = parse()
    print(usb)
# EOF #