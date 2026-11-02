"""iOS 17+ developer tunnel. Uses pymobiledevice3's no-root *userspace* RSD tunnel, held in-process."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .errors import DeviceNotFound, DeviceUnreachable, ServiceTimeout, TunnelFailed

log = logging.getLogger("anywhere_gps.tunnel")


class TunnelHandle:
    def __init__(self, tunnel: Any, rsd: Any) -> None:
        self._tunnel, self.rsd = tunnel, rsd

    async def close(self) -> None:
        try:
            await asyncio.wait_for(self._tunnel.aclose(), 5)
        except Exception as e:
            log.warning("tunnel close error: %r", e)


class UserspaceTunnelManager:
    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def open(self, udid: str) -> TunnelHandle:
        from pymobiledevice3.exceptions import DeviceNotFoundError, PyMobileDevice3Exception
        from pymobiledevice3.remote.userspace_tunnel import UserspaceRsdTunnel
        tunnel = UserspaceRsdTunnel(serial=udid, autopair=False, remotepairing_fallback=False)
        try:
            rsd = await asyncio.wait_for(tunnel.aopen(), self.timeout)
        except asyncio.TimeoutError as e:
            raise ServiceTimeout("Timed out opening the developer tunnel.") from e
        except DeviceNotFoundError as e:
            raise DeviceNotFound(f"No device with UDID {udid} is connected.") from e
        except PyMobileDevice3Exception as e:
            raise TunnelFailed(f"Tunnel failed: {e}") from e
        except OSError as e:
            raise DeviceUnreachable(f"Tunnel I/O error: {e}") from e
        return TunnelHandle(tunnel, rsd)
