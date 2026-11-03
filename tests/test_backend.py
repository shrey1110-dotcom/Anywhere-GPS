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


