import httpx
import pytest
from fastapi.testclient import TestClient

from anywhere_gps import compatibility_report as cr
from anywhere_gps.app import create_app
from anywhere_gps.config import Settings
from anywhere_gps.errors import RateLimited
from anywhere_gps.geocode import Geocoder
from anywhere_gps.location_restore import ProbeReading, verify_restore
from anywhere_gps.mock_backend import make_mock_services


def test_verify_restore_cases():
    tgt = (40.69, -74.04)
    assert not verify_restore(ProbeReading(40.69, -74.04, True, 1), tgt)["verified"]
    assert verify_restore(ProbeReading(37.0, -122.0, False, 1), tgt)["verified"]
    assert verify_restore(ProbeReading(37.0, -122.0, False, 99), tgt)["reason"] == "stale_reading"
    assert verify_restore(ProbeReading(40.69, -74.04, None, 1), tgt)["reason"] == "inconclusive_near_target"
    assert not verify_restore(ProbeReading(37.0, -122.0, None, 1), tgt)["verified"]  # unknown source != proof


