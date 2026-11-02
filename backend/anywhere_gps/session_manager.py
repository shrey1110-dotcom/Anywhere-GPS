"""Per-device simulation sessions: state machine, locking, monitoring, retry, graceful shutdown."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from .errors import (AnywhereGpsError, DeviceNotFound, DeviceUnreachable, MultipleDevices, ServiceTimeout,
                     SessionBusy, TunnelFailed)
from .models import LocationChannel, Services, SessionState, now, validate_coordinates

log = logging.getLogger("anywhere_gps.session")
TRANSIENT = (TunnelFailed, ServiceTimeout)


async def retry_with_backoff(op: Callable[[], Awaitable[Any]], *, attempts: int, base: float,
                             sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> Any:
    """Bounded retries; only transient errors are retried. Config errors (dev mode, pairing) fail at once."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            return await op()
        except TRANSIENT as e:
            last = e
            log.warning("transient failure (attempt %d/%d): %s", i + 1, attempts, e.message)
            if i + 1 < attempts:
                await sleep(base * (2 ** i))
    assert last is not None
    raise last


@dataclass
class DeviceSession:
    udid: str
    state: SessionState = SessionState.IDLE
    target: tuple[float, float] | None = None
    channel: LocationChannel | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    monitor: asyncio.Task | None = None
    error: dict[str, str] | None = None
    since: float = field(default_factory=now)
    last_restore: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "udid": self.udid, "state": self.state.value,
            # True only while a channel is open AND the monitor has not flagged loss.
            "simulation_active": self.state == SessionState.ACTIVE and self.channel is not None,
            "target": {"latitude": self.target[0], "longitude": self.target[1]} if self.target else None,
            "error": self.error, "since": self.since, "last_restore": self.last_restore,
        }


class SessionManager:
    def __init__(self, services: Services, *, op_timeout: float = 20.0, connect_attempts: int = 3,
                 backoff_base: float = 0.5, monitor_interval: float = 2.0,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> None:
        self.s = services
        self.op_timeout, self.attempts, self.base = op_timeout, connect_attempts, backoff_base
        self.interval, self._sleep = monitor_interval, sleep
        self.sessions: dict[str, DeviceSession] = {}
        self._closing = False

    # ---- device resolution -------------------------------------------------
    async def resolve_udid(self, udid: str | None) -> str:
        devices = await self.s.discovery.list_devices()
        if udid:
            if not any(d.udid == udid for d in devices):
                raise DeviceNotFound(f"No device with UDID {udid} is connected.")
            return udid
        if not devices:
            raise DeviceNotFound("No iPhone is connected.")
        if len(devices) > 1:
            raise MultipleDevices(f"{len(devices)} iPhones are connected: " + ", ".join(d.udid for d in devices))
        return devices[0].udid

    def _session(self, udid: str) -> DeviceSession:
        return self.sessions.setdefault(udid, DeviceSession(udid))

    def status(self, udid: str) -> dict[str, Any]:
        return self._session(udid).snapshot()

    def all_status(self) -> list[dict[str, Any]]:
        return [s.snapshot() for s in self.sessions.values()]

    # ---- set ---------------------------------------------------------------
    async def set_location(self, udid: str | None, latitude: float, longitude: float) -> dict[str, Any]:
        lat, lon = validate_coordinates(latitude, longitude)
        udid = await self.resolve_udid(udid)
        sess = self._session(udid)
        if sess.lock.locked():      # never queue conflicting operations on one device
            raise SessionBusy(f"Another operation is running on {udid}.")
        async with sess.lock:
            readiness = await self.s.setup.check(udid)
            if not readiness.ready:
                if readiness.problems:
                    p = readiness.problems[0]
                    self._raise_problem(p)
                raise DeviceUnreachable("Could not determine whether the device is ready.")
            try:
                if sess.state == SessionState.ACTIVE and sess.channel is not None:
                    try:
                        await sess.channel.ping()
                    except DeviceUnreachable:
                        await self._drop_channel(sess)
                if sess.channel is None:
                    sess.state, sess.error, sess.since = SessionState.CONNECTING, None, now()
                    sess.channel = await retry_with_backoff(
                        lambda: self._open(udid), attempts=self.attempts, base=self.base, sleep=self._sleep)
                await sess.channel.set(lat, lon)
            except AnywhereGpsError as e:
                await self._drop_channel(sess)
                sess.state, sess.error, sess.since = SessionState.ERROR, e.to_dict(), now()
                log.error("set_location failed", extra={"ctx": {"udid": udid, "code": e.code}})
                raise
            sess.target, sess.state, sess.error, sess.since = (lat, lon), SessionState.ACTIVE, None, now()
            if sess.monitor is None or sess.monitor.done():
                sess.monitor = asyncio.create_task(self._monitor(sess), name=f"monitor-{udid}")
            log.info("location set", extra={"ctx": {"udid": udid, "lat": lat, "lon": lon}})
            return sess.snapshot()

    @staticmethod
    def _raise_problem(p: dict[str, str]) -> None:
        from . import errors
        for cls in vars(errors).values():
            if isinstance(cls, type) and issubclass(cls, AnywhereGpsError) and getattr(cls, "code", None) == p["code"]:
                raise cls(p["message"], hint=p["hint"])
        raise AnywhereGpsError(p["message"], hint=p.get("hint"))

    async def _open(self, udid: str) -> LocationChannel:
        try:
            return await asyncio.wait_for(self.s.simulator.open(udid), self.op_timeout)
        except asyncio.TimeoutError as e:
            raise ServiceTimeout("Timed out connecting to the device's developer services.") from e

    async def _drop_channel(self, sess: DeviceSession) -> None:
        ch, sess.channel = sess.channel, None
        if ch is not None:
            try:
                await asyncio.wait_for(ch.close(), 8)
            except Exception as e:
                log.warning("close failed: %r", e)

    # ---- clear -------------------------------------------------------------
    async def clear_location(self, udid: str | None) -> dict[str, Any]:
        udid = await self.resolve_udid(udid)
        sess = self._session(udid)
        if sess.lock.locked():
            raise SessionBusy(f"Another operation is running on {udid}.")
        async with sess.lock:
            sess.state = SessionState.RESTORING
            had_target = sess.target
            try:
                ch = sess.channel
                if ch is None:   # e.g. after a backend restart: open a fresh channel just to send `clear`
                    ch = await retry_with_backoff(lambda: self._open(udid), attempts=self.attempts,
                                                  base=self.base, sleep=self._sleep)
                    sess.channel = ch
                await asyncio.wait_for(ch.clear(), self.op_timeout)
            except asyncio.TimeoutError:
                sess.state = SessionState.ERROR
                sess.error = ServiceTimeout("The device did not confirm the restore request.").to_dict()
                await self._drop_channel(sess)
                raise ServiceTimeout("The device did not confirm the restore request.")
            except AnywhereGpsError as e:
                await self._drop_channel(sess)
                sess.state, sess.error = SessionState.ERROR, e.to_dict()
                raise
            await self._drop_channel(sess)
            await self._stop_monitor(sess)
            sess.target, sess.error, sess.state, sess.since = None, None, SessionState.IDLE, now()
            # Honest wording: the device accepted the clear command. Nothing here can *observe* the phone's
            # real GPS, so independent verification must come from Location Probe (see location_restore.py).
            sess.last_restore = {"clear_command_accepted": True, "verified": False,
                                 "verification": "pending",
                                 "message": "Restore command accepted by the device. Confirm in Location Probe "
                                            "(isSimulatedBySoftware = false) before relying on it.",
                                 "previous_target": {"latitude": had_target[0], "longitude": had_target[1]}
                                 if had_target else None}
            return sess.snapshot()

    # ---- monitoring --------------------------------------------------------
    async def _monitor(self, sess: DeviceSession) -> None:
        while not self._closing:
            await self._sleep(self.interval)
            if sess.state != SessionState.ACTIVE or sess.channel is None:
                return
            try:
                present = any(d.udid == sess.udid for d in await self.s.discovery.list_devices())
                if not present:
                    raise DeviceUnreachable("The iPhone was disconnected.")
                await asyncio.wait_for(sess.channel.ping(), self.op_timeout)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                err = e if isinstance(e, AnywhereGpsError) else DeviceUnreachable(f"Connection check failed: {e!r}")
                if sess.lock.locked():
                    continue
                async with sess.lock:
                    if sess.state != SessionState.ACTIVE:
                        return
                    await self._drop_channel(sess)
                    sess.state, sess.error, sess.since = SessionState.LOST, err.to_dict(), now()
                    log.warning("session lost", extra={"ctx": {"udid": sess.udid, "why": err.message}})
                return   # no auto-reapply: the user must press Set Location again

    async def _stop_monitor(self, sess: DeviceSession) -> None:
        t, sess.monitor = sess.monitor, None
        if t and t is not asyncio.current_task():
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass

    # ---- shutdown ----------------------------------------------------------
    async def shutdown(self) -> None:
        """Graceful: stop monitors, send `clear` on active sessions (bounded), close all channels."""
        self._closing = True
        for sess in list(self.sessions.values()):
            await self._stop_monitor(sess)
            if sess.channel is not None:
                try:
                    if sess.state == SessionState.ACTIVE:
                        await asyncio.wait_for(sess.channel.clear(), 5)
                except Exception as e:
                    log.warning("clear during shutdown failed for %s: %r", sess.udid, e)
                await self._drop_channel(sess)
                sess.state, sess.target = SessionState.IDLE, None
