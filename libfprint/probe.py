#!/usr/bin/env python3
"""Read-only probe of the ELAN 04f3:0c00 match-on-chip reader over raw usbfs.

Sends only query commands (firmware version, enrolled count, finger info);
nothing is enrolled, deleted or wiped. No third-party modules needed.
"""
import ctypes
import fcntl
import glob
import os
import sys

USBDEVFS_BULK = 0xC0185502
USBDEVFS_CLAIMINTERFACE = 0x8004550F
USBDEVFS_RELEASEINTERFACE = 0x80045510

EP_OUT = 0x01
EP_IN = 0x83
MAX_PRINTS = 10


class BulkTransfer(ctypes.Structure):
    _fields_ = [("ep", ctypes.c_uint), ("len", ctypes.c_uint),
                ("timeout", ctypes.c_uint), ("data", ctypes.c_void_p)]


def find_device():
    for path in glob.glob("/sys/bus/usb/devices/*/idVendor"):
        base = os.path.dirname(path)
        with open(path) as f:
            vendor = f.read().strip()
        with open(os.path.join(base, "idProduct")) as f:
            product = f.read().strip()
        if (vendor, product) == ("04f3", "0c00"):
            with open(os.path.join(base, "busnum")) as f:
                bus = int(f.read())
            with open(os.path.join(base, "devnum")) as f:
                dev = int(f.read())
            return "/dev/bus/usb/%03d/%03d" % (bus, dev)
    sys.exit("no 04f3:0c00 device found")


def bulk(fd, ep, data_or_len, timeout_ms=2000):
    if ep & 0x80:
        buf = ctypes.create_string_buffer(data_or_len)
    else:
        buf = ctypes.create_string_buffer(bytes(data_or_len), len(data_or_len))
    xfer = BulkTransfer(ep, len(buf), timeout_ms, ctypes.addressof(buf))
    n = fcntl.ioctl(fd, USBDEVFS_BULK, xfer)
    return buf.raw[:n] if ep & 0x80 else n


def query(fd, name, cmd, in_len):
    try:
        bulk(fd, EP_OUT, cmd)
        resp = bulk(fd, EP_IN, in_len)
        print("%-16s > %s  < %s" % (name, bytes(cmd).hex(" "), resp.hex(" ")))
        return resp
    except OSError as e:
        print("%-16s > %s  ! %s" % (name, bytes(cmd).hex(" "), e))
        return None


def main():
    fd = os.open(find_device(), os.O_RDWR)
    iface = ctypes.c_uint(0)
    fcntl.ioctl(fd, USBDEVFS_CLAIMINTERFACE, iface)
    try:
        query(fd, "fw version", [0x40, 0x19], 2)
        query(fd, "enrolled count", [0x40, 0xFF, 0x04], 2)
        for i in range(MAX_PRINTS):
            query(fd, "finger info %d" % i, [0x40, 0xFF, 0x12, i], 64)
    finally:
        fcntl.ioctl(fd, USBDEVFS_RELEASEINTERFACE, iface)
        os.close(fd)


if __name__ == "__main__":
    main()
