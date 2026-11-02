"""Readiness checks: pairing, iOS version, Developer Mode, mounted developer image."""
from __future__ import annotations

import asyncio
import logging

from packaging.version import Version

from .errors import (AnywhereGpsError, DeveloperImageMissing, DeviceNotFound, DeviceUnreachable)
from .models import Readiness

log = logging.getLogger("anywhere_gps.setup")
MIN_IOS = Version("17.4")  # userspace tunnel needs CoreDeviceProxy (iOS 17.4+)


def build_readiness(udid: str, *, paired: bool, ios_version: str | None, developer_mode: bool | None,
                    image_mounted: bool | None) -> Readiness:
    """Pure function turning raw facts into a Readiness with actionable problems (unit-testable)."""
    from .errors import DeveloperModeDisabled, NotPaired, UnsupportedIOSVersion
    problems: list[AnywhereGpsError] = []
    supported = False
    if not paired:
        problems.append(NotPaired("The iPhone is not paired/trusted with this Mac."))
    if ios_version:
        supported = Version(ios_version) >= MIN_IOS
        if not supported:
            problems.append(UnsupportedIOSVersion(f"iOS {ios_version} is not supported (need 17.4+)."))
    if paired and developer_mode is False:
        problems.append(DeveloperModeDisabled("Developer Mode is turned off on the iPhone."))
    if paired and supported and developer_mode and image_mounted is False:
        problems.append(DeveloperImageMissing("No developer disk image is mounted."))
    return Readiness(udid=udid, paired=paired, ios_supported=supported, developer_mode=developer_mode,
                     image_mounted=image_mounted, ios_version=ios_version,
                     problems=[p.to_dict() for p in problems])


class RealDeveloperSetup:
    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    async def _lockdown(self, udid: str):
        from pymobiledevice3.exceptions import (ConnectionFailedError, DeviceNotFoundError, NotPairedError,
                                                PairingError)
        from pymobiledevice3.lockdown import create_using_usbmux
        try:
            return await asyncio.wait_for(create_using_usbmux(serial=udid, autopair=False), self.timeout)
        except DeviceNotFoundError as e:
            raise DeviceNotFound(f"No device with UDID {udid} is connected.") from e
        except (NotPairedError, PairingError):
            return None
        except (ConnectionFailedError, asyncio.TimeoutError) as e:
            raise DeviceUnreachable(f"Could not talk to {udid}: {e!r}") from e

    async def check(self, udid: str) -> Readiness:
        from pymobiledevice3.services.mobile_image_mounter import (MobileImageMounterService,
                                                                   image_type_for_device)
        ld = await self._lockdown(udid)
        if ld is None:
            return build_readiness(udid, paired=False, ios_version=None, developer_mode=None, image_mounted=None)
        try:
            ver = ld.product_version
            dev_mode: bool | None = None
            mounted: bool | None = None
            try:
                async with MobileImageMounterService(ld) as mounter:
                    dev_mode = await asyncio.wait_for(mounter.query_developer_mode_status(), self.timeout)
                    if dev_mode:
                        mounted = await asyncio.wait_for(
                            mounter.is_image_mounted(image_type_for_device(ld)), self.timeout)
            except Exception as e:  # leave unknown rather than guess
                log.warning("readiness probe incomplete for %s: %r", udid, e)
            return build_readiness(udid, paired=True, ios_version=ver, developer_mode=dev_mode, image_mounted=mounted)
        finally:
            await ld.close()

    async def mount_image(self, udid: str) -> None:
        """Equivalent of `pymobiledevice3 mounter auto-mount`; downloads the personalized DDI (needs internet)."""
        from pymobiledevice3.services.mobile_image_mounter import auto_mount
        ld = await self._lockdown(udid)
        if ld is None:
            from .errors import NotPaired
            raise NotPaired("The iPhone is not paired/trusted with this Mac.")
        try:
            await asyncio.wait_for(auto_mount(ld), 600)
        finally:
            await ld.close()
