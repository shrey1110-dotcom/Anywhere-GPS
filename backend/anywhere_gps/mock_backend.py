"""MOCK backend — for automated tests and UI development ONLY. It never touches a real device.

The API reports `backend: "mock"` and the UI shows a permanent banner when it is active.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .developer_setup import build_readiness
from .errors import DeviceNotFound, DeviceUnreachable, TunnelFailed
from .models import DeviceInfo, Readiness, Services


@dataclass
class FakeDevice:
    udid: str
    name: str = "Mock iPhone"
    ios_version: str = "18.0"
    paired: bool = True
    developer_mode: bool = True
    image_mounted: bool = True
    connected: bool = True


@dataclass
class MockFarm:
    devices: dict[str, FakeDevice] = field(default_factory=dict)
    simulated: dict[str, tuple[float, float]] = field(default_factory=dict)  # what the "device" believes
    open_channels: dict[str, int] = field(default_factory=dict)
    tunnel_failures: int = 0     # next N open() calls fail (transient)
    calls: list[str] = field(default_factory=list)

    def add(self, udid: str, **kw) -> FakeDevice:
        self.devices[udid] = FakeDevice(udid=udid, **kw)
        return self.devices[udid]

    def unplug(self, udid: str) -> None:
        self.devices[udid].connected = False
        self.simulated.pop(udid, None)   # connection gone => modelled as simulation gone (hardware TBD)

    def plug(self, udid: str) -> None:
        self.devices[udid].connected = True


class MockChannel:
    def __init__(self, farm: MockFarm, udid: str) -> None:
        self.farm, self.udid, self.closed = farm, udid, False

    def _live(self) -> FakeDevice:
        d = self.farm.devices.get(self.udid)
        if self.closed or d is None or not d.connected:
            raise DeviceUnreachable("Mock device is unreachable.")
        return d

    async def set(self, latitude: float, longitude: float) -> None:
        self._live()
        self.farm.calls.append(f"set {latitude} {longitude}")
        self.farm.simulated[self.udid] = (latitude, longitude)

    async def clear(self) -> None:
        self._live()
        self.farm.calls.append("clear")
        self.farm.simulated.pop(self.udid, None)

    async def ping(self) -> None:
        self._live()

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.farm.open_channels[self.udid] = self.farm.open_channels.get(self.udid, 1) - 1
            self.farm.simulated.pop(self.udid, None)  # closing the DVT connection ends simulation (modelled)


class MockDiscovery:
    def __init__(self, farm: MockFarm) -> None:
        self.farm = farm

    async def list_devices(self) -> list[DeviceInfo]:
        return [DeviceInfo(udid=d.udid, name=d.name, ios_version=d.ios_version if d.paired else None,
                           product_type="MockPhone1,1", paired=d.paired)
                for d in self.farm.devices.values() if d.connected]


class MockSetup:
    def __init__(self, farm: MockFarm) -> None:
        self.farm = farm

    async def check(self, udid: str) -> Readiness:
        d = self.farm.devices.get(udid)
        if d is None or not d.connected:
            raise DeviceNotFound(f"No device with UDID {udid} is connected.")
        return build_readiness(udid, paired=d.paired, ios_version=d.ios_version if d.paired else None,
                               developer_mode=d.developer_mode if d.paired else None,
                               image_mounted=d.image_mounted if d.developer_mode else None)

    async def mount_image(self, udid: str) -> None:
        self.farm.devices[udid].image_mounted = True


class MockSimulator:
    def __init__(self, farm: MockFarm) -> None:
        self.farm = farm

    async def open(self, udid: str) -> MockChannel:
        d = self.farm.devices.get(udid)
        if d is None or not d.connected:
            raise DeviceNotFound(f"No device with UDID {udid} is connected.")
        if self.farm.tunnel_failures > 0:
            self.farm.tunnel_failures -= 1
            raise TunnelFailed("Mock transient tunnel failure.")
        self.farm.open_channels[udid] = self.farm.open_channels.get(udid, 0) + 1
        return MockChannel(self.farm, udid)


def make_mock_services(farm: MockFarm | None = None) -> tuple[Services, MockFarm]:
    farm = farm or MockFarm()
    return Services(MockDiscovery(farm), MockSetup(farm), MockSimulator(farm), kind="mock"), farm
