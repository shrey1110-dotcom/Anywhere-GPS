"""Real LocationSimulation channel over DVT (com.apple.instruments.server.services.LocationSimulation).

The channel owns the tunnel + DTX connection. Per pymobiledevice3's CLI (`dvt simulate-location set`) the
process must stay alive after `set`; we therefore keep this object open for the whole session.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack

from .errors import DeviceUnreachable, ServiceTimeout
from .tunnel_manager import UserspaceTunnelManager

log = logging.getLogger("anywhere_gps.simulator")


class DvtLocationChannel:
    def __init__(self, stack: AsyncExitStack, dvt, sim, timeout: float) -> None:
        self._stack, self._dvt, self._sim, self._timeout = stack, dvt, sim, timeout
        self._closed = False

    async def _call(self, coro):
        from pymobiledevice3.exceptions import ConnectionTerminatedError
        try:
            return await asyncio.wait_for(coro, self._timeout)
        except asyncio.TimeoutError as e:
            raise ServiceTimeout("The device did not answer the location request in time.") from e
        except (ConnectionTerminatedError, ConnectionError, OSError, EOFError) as e:
            raise DeviceUnreachable(f"Lost connection to the device: {e!r}") from e

    async def set(self, latitude: float, longitude: float) -> None:
        await self._call(self._sim.set(latitude, longitude))

    async def clear(self) -> None:
        await self._call(self._sim.clear())

    async def ping(self) -> None:
        # Liveness from pymobiledevice3's DTX connection state. These are private attributes (no public
        # "is_connected" exists in 11.45.0); the pinned version is recorded in COMPATIBILITY.md.
        dtx = getattr(self._dvt, "_dtx", None)
        reader = getattr(dtx, "_reader_task", None)
        if dtx is None or getattr(dtx, "_closed", False) or (reader is not None and reader.done()):
            raise DeviceUnreachable("The developer-service connection to the device has closed.")

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await asyncio.wait_for(self._stack.aclose(), 8)
        except Exception as e:
            log.warning("channel close error: %r", e)


class DvtLocationSimulator:
    def __init__(self, tunnels: UserspaceTunnelManager | None = None, timeout: float = 20.0) -> None:
        self.tunnels = tunnels or UserspaceTunnelManager()
        self.timeout = timeout

    async def open(self, udid: str) -> DvtLocationChannel:
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
        tunnel = await self.tunnels.open(udid)
        stack = AsyncExitStack()
        try:
            stack.push_async_callback(tunnel.close)
            dvt = await stack.enter_async_context(DvtProvider(tunnel.rsd))
            sim = await stack.enter_async_context(LocationSimulation(dvt))
        except BaseException:
            await stack.aclose()
            raise
        return DvtLocationChannel(stack, dvt, sim, self.timeout)
