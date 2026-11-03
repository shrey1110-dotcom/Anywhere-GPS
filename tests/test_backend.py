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
