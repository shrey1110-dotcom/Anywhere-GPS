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


