"""Discover iPhones via usbmuxd (equivalent of `pymobiledevice3 usbmux list`) plus lockdown metadata."""
from __future__ import annotations

import asyncio
import logging

from .errors import DeviceUnreachable
from .models import DeviceInfo

log = logging.getLogger("anywhere_gps.discovery")


class UsbmuxDiscovery:
    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    async def list_devices(self) -> list[DeviceInfo]:
        from pymobiledevice3 import usbmux
        from pymobiledevice3.exceptions import ConnectionFailedToUsbmuxdError
        from pymobiledevice3.lockdown import create_using_usbmux

        try:
            muxed = await asyncio.wait_for(usbmux.list_devices(), self.timeout)
        except ConnectionFailedToUsbmuxdError as e:
            raise DeviceUnreachable("usbmuxd is not reachable.", hint="On macOS usbmuxd is built in; replug the cable.") from e
        except asyncio.TimeoutError as e:
            raise DeviceUnreachable("Timed out listing USB devices.") from e

        devices: list[DeviceInfo] = []
        for m in muxed:
            info = DeviceInfo(udid=m.serial, connection=m.connection_type)
            try:
                # autopair=False: listing must never trigger a pairing dialog on the phone.
                ld = await asyncio.wait_for(
                    create_using_usbmux(serial=m.serial, autopair=False, connection_type=m.connection_type),
                    self.timeout)
                try:
                    info.name = ld.all_values.get("DeviceName")
                    info.ios_version = ld.product_version
                    info.product_type = ld.all_values.get("ProductType")
                    if ld.all_values.get("DeviceClass") not in (None, "iPhone"):
                        log.info("skipping non-iPhone %s (%s)", m.serial, ld.all_values.get("DeviceClass"))
                finally:
                    await ld.close()
            except Exception as e:  # unpaired / locked / transient: still list it, flagged
                log.info("device %s listed without metadata: %r", m.serial, e)
                info.paired = False
            devices.append(info)
        return devices
