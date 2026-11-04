import asyncio

import pytest
from fastapi.testclient import TestClient

from anywhere_gps.app import create_app
from anywhere_gps.errors import *  # noqa: F401,F403
from anywhere_gps.errors import (DeveloperImageMissing, DeveloperModeDisabled, DeviceNotFound, InvalidCoordinates,
                                 MultipleDevices, NotPaired, SessionBusy, UnsupportedIOSVersion)
from anywhere_gps.mock_backend import make_mock_services
from anywhere_gps.models import SessionState
from anywhere_gps.session_manager import SessionManager, retry_with_backoff


# 1 Device discovery
async def test_discovery_lists_connected_only(farm_services):
    services, farm = farm_services
    farm.add("UDID-B", ios_version="17.4")
    farm.unplug("UDID-B")
    devs = await services.discovery.list_devices()
    assert [d.udid for d in devs] == ["UDID-A"]
    assert devs[0].ios_version == "18.0" and devs[0].name == "Phone A"


# 2 Missing Developer Mode
async def test_missing_developer_mode(farm_services, mgr):
    _, farm = farm_services
    farm.devices["UDID-A"].developer_mode = False
    with pytest.raises(DeveloperModeDisabled) as e:
        await mgr.set_location("UDID-A", 10, 10)
    assert "Developer Mode" in e.value.hint
    assert farm.simulated == {}


# 3 Missing developer image
async def test_missing_developer_image(farm_services, mgr):
    _, farm = farm_services
    farm.devices["UDID-A"].image_mounted = False
    with pytest.raises(DeveloperImageMissing):
        await mgr.set_location("UDID-A", 10, 10)


async def test_not_paired(farm_services, mgr):
    farm_services[1].devices["UDID-A"].paired = False
    with pytest.raises(NotPaired):
        await mgr.set_location("UDID-A", 10, 10)


# 4 Invalid coordinates
@pytest.mark.parametrize("lat,lon", [(91, 0), (-90.0001, 0), (0, 180.5), (0, -181), (float("nan"), 0),
                                     (float("inf"), 0), (None, 0), ("1", 2), (True, 0)])
async def test_invalid_coordinates(mgr, farm_services, lat, lon):
    with pytest.raises(InvalidCoordinates):
        await mgr.set_location("UDID-A", lat, lon)
    assert farm_services[1].simulated == {}


@pytest.mark.parametrize("lat,lon", [(90, 180), (-90, -180), (0, 0)])
async def test_boundary_coordinates_ok(mgr, lat, lon):
    snap = await mgr.set_location("UDID-A", lat, lon)
    assert snap["simulation_active"]
    await mgr.shutdown()


# 5 Valid simulation
async def test_valid_set(mgr, farm_services):
    snap = await mgr.set_location(None, 40.690008, -74.045843)
    assert snap["state"] == "active" and snap["simulation_active"]
    assert farm_services[1].simulated["UDID-A"] == (40.690008, -74.045843)
    await mgr.shutdown()


# 6 Repeated requests reuse one channel
async def test_repeated_set_reuses_channel(mgr, farm_services):
    await mgr.set_location(None, 1, 1)
    await mgr.set_location(None, 2, 2)
    await mgr.set_location(None, 3, 3)
    assert farm_services[1].open_channels["UDID-A"] == 1
    assert farm_services[1].simulated["UDID-A"] == (3, 3)
    assert mgr.status("UDID-A")["target"] == {"latitude": 3, "longitude": 3}
    await mgr.shutdown()


# 7 Restore
async def test_restore(mgr, farm_services):
    await mgr.set_location(None, 1, 1)
    snap = await mgr.clear_location(None)
    assert snap["state"] == "idle" and not snap["simulation_active"] and snap["target"] is None
    assert "UDID-A" not in farm_services[1].simulated
    # honesty: the command was accepted but NOT independently verified
    assert snap["last_restore"]["clear_command_accepted"] is True
    assert snap["last_restore"]["verified"] is False
    assert farm_services[1].open_channels["UDID-A"] == 0


async def test_restore_without_session_opens_channel_and_clears(mgr, farm_services):
    farm_services[1].simulated["UDID-A"] = (5, 5)   # e.g. left over from before a backend restart
    await mgr.clear_location(None)
    assert "clear" in farm_services[1].calls


# 8 Cable disconnect is detected and never reported as active
async def test_cable_disconnect(mgr, farm_services):
    _, farm = farm_services
    await mgr.set_location(None, 1, 1)
    farm.unplug("UDID-A")
    for _ in range(50):
        await asyncio.sleep(0.01)
        if mgr.status("UDID-A")["state"] == "lost":
            break
    snap = mgr.status("UDID-A")
    assert snap["state"] == "lost" and snap["simulation_active"] is False
    assert snap["error"]["code"] == "device_unreachable"


# 9 Reconnection: no automatic re-apply; explicit set works again
async def test_reconnect_no_auto_reapply(mgr, farm_services):
    _, farm = farm_services
    await mgr.set_location(None, 1, 1)
    farm.unplug("UDID-A")
    for _ in range(50):
        await asyncio.sleep(0.01)
        if mgr.status("UDID-A")["state"] == "lost":
            break
    farm.plug("UDID-A")
    await asyncio.sleep(0.05)
    assert "UDID-A" not in farm.simulated and not mgr.status("UDID-A")["simulation_active"]
    snap = await mgr.set_location(None, 7, 8)
    assert snap["simulation_active"] and farm.simulated["UDID-A"] == (7, 8)
    await mgr.shutdown()


async def test_transient_tunnel_failure_retried(mgr, farm_services):
    farm_services[1].tunnel_failures = 2
    snap = await mgr.set_location(None, 1, 1)
    assert snap["simulation_active"]
    await mgr.shutdown()


async def test_retries_are_bounded(mgr, farm_services):
    farm_services[1].tunnel_failures = 99
    with pytest.raises(Exception) as e:
        await mgr.set_location(None, 1, 1)
    assert e.value.code == "tunnel_failed"
    assert mgr.status("UDID-A")["state"] == "error" and not mgr.status("UDID-A")["simulation_active"]
    assert 99 - farm_services[1].tunnel_failures == 3


async def test_retry_helper_does_not_retry_config_errors():
    calls = 0

    async def op():
        nonlocal calls
        calls += 1
        raise DeveloperModeDisabled("x")
    with pytest.raises(DeveloperModeDisabled):
        await retry_with_backoff(op, attempts=5, base=0)
    assert calls == 1


# 10 Backend termination restores
async def test_graceful_shutdown_clears(mgr, farm_services):
    await mgr.set_location(None, 1, 1)
    await mgr.shutdown()
    assert "clear" in farm_services[1].calls
    assert farm_services[1].simulated == {}
    assert farm_services[1].open_channels["UDID-A"] == 0
    assert mgr.status("UDID-A")["state"] == "idle"


def test_app_lifespan_shutdown_restores(settings):
    services, farm = make_mock_services()
    farm.add("U1")
    with TestClient(create_app(settings, services)) as c:
        assert c.post("/api/location", json={"latitude": 1, "longitude": 2}).status_code == 200
        assert farm.simulated["U1"] == (1, 2)
    assert farm.simulated == {} and farm.open_channels["U1"] == 0


# 11 Unsupported iOS
async def test_unsupported_ios(farm_services, mgr):
    farm_services[1].devices["UDID-A"].ios_version = "16.7"
    with pytest.raises(UnsupportedIOSVersion):
        await mgr.set_location(None, 1, 1)


# 12 Multiple iPhones
async def test_multiple_devices_require_explicit_choice(farm_services, mgr):
    _, farm = farm_services
    farm.add("UDID-B")
    with pytest.raises(MultipleDevices):
        await mgr.set_location(None, 1, 1)
    await mgr.set_location("UDID-B", 1, 1)
    assert "UDID-A" not in farm.simulated and "UDID-B" in farm.simulated
    with pytest.raises(DeviceNotFound):
        await mgr.set_location("NOPE", 1, 1)
    await mgr.shutdown()


async def test_concurrent_conflicting_requests_rejected(farm_services):
    services, farm = farm_services
    gate = asyncio.Event()
    orig = services.simulator.open

    async def slow_open(udid):
        await gate.wait()
        return await orig(udid)
    services.simulator.open = slow_open
    m = SessionManager(services, op_timeout=2, backoff_base=0, monitor_interval=5)
    t = asyncio.create_task(m.set_location(None, 1, 1))
    await asyncio.sleep(0.05)
    with pytest.raises(SessionBusy):
        await m.set_location(None, 2, 2)
    gate.set()
    await t
    await m.shutdown()


async def test_connect_timeout(farm_services):
    services, _ = farm_services

    async def hang(udid):
        await asyncio.sleep(10)
    services.simulator.open = hang
    m = SessionManager(services, op_timeout=0.05, connect_attempts=2, backoff_base=0, monitor_interval=5)
    with pytest.raises(Exception) as e:
        await m.set_location(None, 1, 1)
    assert e.value.code == "service_timeout"


# 13 User-visible error reporting through the HTTP API
def test_api_errors_are_actionable(settings):
    services, farm = make_mock_services()
    farm.add("U1", developer_mode=False)
    with TestClient(create_app(settings, services)) as c:
        r = c.post("/api/location", json={"latitude": 1, "longitude": 2})
        assert r.status_code == 412
        body = r.json()
        assert body["code"] == "developer_mode_disabled" and "Developer Mode" in body["hint"]
        r = c.post("/api/location", json={"latitude": 200, "longitude": 2})
        assert r.status_code == 422 and r.json()["code"] == "invalid_coordinates"
        assert c.get("/api/health").json()["mock"] is True


def test_api_no_device(settings):
    services, _ = make_mock_services()
    with TestClient(create_app(settings, services)) as c:
        r = c.post("/api/location/clear", json={})
        assert r.status_code == 404 and r.json()["code"] == "device_not_found"


def test_cross_origin_requests_blocked(settings):
    services, farm = make_mock_services()
    farm.add("U1")
    with TestClient(create_app(settings, services)) as c:
        r = c.post("/api/location", json={"latitude": 1, "longitude": 2}, headers={"Origin": "https://evil.example"})
        assert r.status_code == 403 and farm.simulated == {}
        r = c.get("/api/health", headers={"Host": "attacker.example"})
        assert r.status_code == 403
        assert c.get("/api/health", headers={"Origin": "http://127.0.0.1:8765"}).status_code == 200


def test_default_bind_is_localhost(settings):
    assert settings.host == "127.0.0.1"
